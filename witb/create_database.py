# Requires transformers>=4.51.0
# Requires sentence-transformers>=2.7.0

import argparse
from pathlib import Path
from sentence_transformers import SentenceTransformer
import csv
import faiss
import tqdm
from sentence_transformers import SentenceTransformer
import json

# Load the model
# model = SentenceTransformer("Qwen/Qwen3-Embedding-4B")

def main() -> None:
    parser = argparse.ArgumentParser("")
    parser.add_argument("--window", type=int, default=1, help="Number of consecutive verses per entry")
    parser.add_argument("--input", default=f"{Path(__file__).parent.parent / 'data' / 'bible.csv'}")
    parser.add_argument("--output", default=f"{Path(__file__).parent.parent / 'data' / 'bible.index'}")
    args = parser.parse_args()

    # We recommend enabling flash_attention_2 for better acceleration and memory saving,
    # together with setting `padding_side` to "left":
    model = SentenceTransformer(
        "Qwen/Qwen3-Embedding-4B",
        model_kwargs={"attn_implementation": "eager", "device_map": "auto"},
        tokenizer_kwargs={"padding_side": "left"}, 
    )

    # Containers for data
    metadata = []

    # 2. Read and Encode
    index = None
    with open(args.input, "r", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    
    print(f"Encoding {len(rows) // args.window} entries (window={args.window})...")
    for i in tqdm.tqdm(range(0, len(rows), args.window)):
        chunk = rows[i : i + args.window]
        text = " ".join(r["text"] for r in chunk)
        ref = f"{chunk[0]['book']} {chunk[0]['chapter']}:{chunk[0]['verse']}-{chunk[-1]['verse']}"

        embedding = model.encode(text, convert_to_numpy=True).astype("float32").reshape(1, -1)

        if index is None:
            index = faiss.IndexFlatL2(embedding.shape[1])

        index.add(embedding)
        metadata.append({"ref": ref, "text": text})

    # Save to Disk
    faiss.write_index(index, args.output)

    # Save metadata separately (needed to reconstruct text from index hits)
    with open(f"{args.output.replace('index', 'json')}", "w", encoding="utf-8") as f:
        json.dump(metadata, f)

    print(f"Index built with {index.ntotal} vectors and saved to {args.output}")

if __name__ == '__main__':
    main()