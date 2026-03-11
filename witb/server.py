import argparse
import json

import faiss
import numpy as np
from flask import Flask, jsonify, request

model = SentenceTransformer(
    "Qwen/Qwen3-Embedding-4B",
    model_kwargs={"attn_implementation": "eager", "device_map": "auto"},
    tokenizer_kwargs={"padding_side": "left"}, 
)

index = None

app = Flask(__name__)

@app.route("/search", methods=["POST"])
def search():
    body = request.get_json(force=True)
    query = body.get("query", "").strip()
    top_k = int(body.get("top_k", 5))

    if not query:
        return jsonify({"error": "query is required"})

    embedding = model.encode(text, convert_to_numpy=True).astype("float32").reshape(1, -1)
    distances, indices = index.search(embedding, top_k)
    
    results = []

    for rank, i in enumerate(indices[0]):
        result = {
            "ref": metadata[i]["ref"],
            "text": metadata[i]["text"]
            "score": float(distances[0][rank])
        }
        results.append(result)

    return jsonify({"query": query, "results": results})

@app.route("/health", methods=["GET"])
def health():
    return jsonify({"status": "ok"})

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--model", default="Qwen/Qwen3-Embedding-0.6B")
    parser.add_argument("--index", required=False, help="Path to FAISS index file")
    parser.add_argument("--metadata", required=False, help="Path to metadata JSON file")
    parser.add_argument("--host", default="0.0.0.0")
    parser.add_argument("--port", type=int, default=5000)
    args = parser.parse_args()

    app.run(host=args.host, port=args.port)