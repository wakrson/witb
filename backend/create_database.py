# Requires transformers>=4.51.0
# Requires sentence-transformers>=2.7.0

import argparse
from pathlib import Path
from sentence_transformers import SentenceTransformer
import csv
import faiss
import numpy as np
import tqdm
import json

BATCH_SIZE = 32


def make_ref(chunk: list[dict]) -> str:
    start_book, start_ch, start_vs = chunk[0]['book'], chunk[0]['chapter'], chunk[0]['verse']
    end_ch, end_vs = chunk[-1]['chapter'], chunk[-1]['verse']
    if start_ch == end_ch and start_vs == end_vs:
        return f"{start_book} {start_ch}:{start_vs}"
    elif start_ch == end_ch:
        return f"{start_book} {start_ch}:{start_vs}-{end_vs}"
    else:
        return f"{start_book} {start_ch}:{start_vs}-{end_ch}:{end_vs}"


def main() -> None:
    parser = argparse.ArgumentParser("")
    parser.add_argument("--min-window", type=int, default=1)
    parser.add_argument("--max-window", type=int, default=10)
    parser.add_argument("--input", default=f"{Path(__file__).parent.parent / 'data' / 'bible.csv'}")
    parser.add_argument("--output", default=f"{Path(__file__).parent.parent / 'data' / 'bible.index'}")
    parser.add_argument("--batch-size", type=int, default=BATCH_SIZE)
    args = parser.parse_args()

    model = SentenceTransformer(
        "Qwen/Qwen3-Embedding-4B",
        device="cuda",
        model_kwargs={
            "attn_implementation": "eager",
            "device_map": None,
        },
        tokenizer_kwargs={"padding_side": "left"},
    )

    with open(args.input, "r", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))

    if not rows:
        print("No rows found in input CSV.")
        return

    texts = []
    metadata = []
    for window in range(args.min_window, args.max_window + 1):
        for i in range(0, len(rows) - window + 1):
            chunk = rows[i : i + window]
            # skip chunks that cross book boundaries
            if chunk[0]['book'] != chunk[-1]['book']:
                continue
            text = " ".join(r["text"] for r in chunk)
            ref = make_ref(chunk)
            texts.append(text)
            metadata.append({
                "ref": ref,
                "text": text,
                "start_row": i,
                "end_row": i + window - 1,
            })

    print(f"Encoding {len(texts)} entries (windows {args.min_window}-{args.max_window})...")
    index = None
    for batch_start in tqdm.tqdm(range(0, len(texts), args.batch_size)):
        batch = texts[batch_start : batch_start + args.batch_size]
        embeddings = model.encode(batch, convert_to_numpy=True).astype("float32")
        if embeddings.ndim == 1:
            embeddings = embeddings.reshape(1, -1)

        if index is None:
            index = faiss.IndexFlatL2(embeddings.shape[1])
        index.add(embeddings)

    output_path = Path(args.output)
    faiss.write_index(index, str(output_path))

    meta_path = output_path.with_suffix('.json')
    with open(meta_path, "w", encoding="utf-8") as f:
        json.dump(metadata, f)

    print(f"Index built with {index.ntotal} vectors and saved to {output_path}")

if __name__ == '__main__':
    main()