import argparse
import json

import faiss
import numpy as np
from flask import Flask, jsonify, request

app = Flask(__name__)

@app.route("/search", methods=["POST"])
def search():
    body = request.get_json(force=True)
    query = body.get("query", "").strip()
    print(query)
    return query

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