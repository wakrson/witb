import argparse
import json

import faiss
import torch
from flask import Flask, jsonify, request
from sentence_transformers import SentenceTransformer

app = Flask(__name__)

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
            "attn_implementation": "eager",
            "device_map": None,
            #"dtype": torch.float16,
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

    if not query:
        return jsonify({"error": "query is required"}), 400

    embedding = model.encode(query, convert_to_numpy=True).astype("float32").reshape(1, -1)
    distances, indices = index.search(embedding, top_k)

    results = [
        {
            "ref": metadata[i]["ref"],
            "text": metadata[i]["text"],
            "score": float(distances[0][rank]),
        }
        for rank, i in enumerate(indices[0])
        #if i < len(metadata)
    ]

    return jsonify({"query": query, "results": results})


@app.route("/health", methods=["GET"])
def health():
    return jsonify({"status": "ok"})


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--model", default="Qwen/Qwen3-Embedding-4B")
    parser.add_argument("--index", default="/home/wakrson/witb/data/bible.index")
    parser.add_argument("--metadata", default="/home/wakrson/witb/data/bible.json")
    parser.add_argument("--host", default="0.0.0.0")
    parser.add_argument("--port", type=int, default=5000)
    args = parser.parse_args()

    load(args.model, args.index, args.metadata)
    app.run(host=args.host, port=args.port, debug=True, use_reloader=False)