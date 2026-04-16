import argparse
import json

import faiss
import torch
from flask import Flask, jsonify, request
from flask_cors import CORS
from sentence_transformers import SentenceTransformer

app = Flask(__name__)
CORS(app)

model = None
index = None
metadata = None


def load(model_name: str, index_path: str, metadata_path: str):
    global model, index, metadata

    print(f"Loading model: {model_name}")
    model = SentenceTransformer(
        model_name,
        device="cuda",
        model_kwargs={
            "attn_implementation": "sdpa",
            "device_map": None,
            "dtype": torch.float16,
        },
        tokenizer_kwargs={"padding_side": "left"},
    )

    print(f"Loading index: {index_path}")
    index = faiss.read_index(index_path)

    print(f"Loading metadata: {metadata_path}")
    with open(metadata_path, "r", encoding="utf-8") as f:
        metadata = json.load(f)

    print("Ready.")


@app.route("/search", methods=["POST"])
def search():
    body = request.get_json(force=True)
    query = body.get("query", "").strip()
    top_k = int(body.get("top_k", 5))
    min_window = int(body.get("min_window", 1))

    if not query:
        return jsonify({"error": "query is required"}), 400

    # fetch extra candidates so we can filter overlaps and still return top_k
    fetch_k = top_k * 20
    embedding = model.encode(query, prompt_name="query", convert_to_numpy=True, normalize_embeddings=True).astype("float32").reshape(1, -1)
    distances, indices = index.search(embedding, min(fetch_k, index.ntotal))

    results = []
    claimed = set()  # set of row indices already covered
    for rank, idx in enumerate(indices[0]):
        if idx == -1:
            continue
        entry = metadata[idx]
        window_size = entry["end_row"] - entry["start_row"] + 1
        if window_size < min_window:
            continue
        entry_rows = set(range(entry["start_row"], entry["end_row"] + 1))
        if entry_rows & claimed:
            continue
        claimed |= entry_rows
        results.append({
            "ref": entry["ref"],
            "text": entry["text"],
            "score": float(distances[0][rank]),
        })
        if len(results) >= top_k:
            break

    return jsonify({"query": query, "results": results})


@app.route("/health", methods=["GET"])
def health():
    return jsonify({"status": "ok"})

load(
    "Qwen/Qwen3-Embedding-4B",
    "/home/wakrson/witb/data/bible.index",
    "/home/wakrson/witb/data/bible.json",
)