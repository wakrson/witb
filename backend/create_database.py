# Requires transformers>=4.51.0
# Requires sentence-transformers>=2.7.0

import argparse
from pathlib import Path
from sentence_transformers import SentenceTransformer
import csv
import faiss
import numpy as np
import json
import torch
import tqdm

BATCH_SIZE = 8
WINDOW_SIZES = [1, 3, 5, 10]

def make_ref(book: str, start_ch: str, start_vs: str, end_ch: str, end_vs: str) -> str:
    if start_ch == end_ch and start_vs == end_vs:
        return f"{book} {start_ch}:{start_vs}"
    elif start_ch == end_ch:
        return f"{book} {start_ch}:{start_vs}-{end_vs}"
    else:
        return f"{book} {start_ch}:{start_vs}-{end_ch}:{end_vs}"


def main() -> None:
    parser = argparse.ArgumentParser("")
    parser.add_argument("--window-sizes", type=int, nargs="+", default=WINDOW_SIZES)
    parser.add_argument("--input", default=f"{Path(__file__).parent.parent / 'data' / 'bible.csv'}")
    parser.add_argument("--output", default=f"{Path(__file__).parent.parent / 'data' / 'bible.index'}")
    parser.add_argument("--batch-size", type=int, default=BATCH_SIZE)
    args = parser.parse_args()

    model = SentenceTransformer(
        "Qwen/Qwen3-Embedding-4B",
        device="cuda",
        model_kwargs={
            "attn_implementation": "sdpa",
            "device_map": None,
            "dtype": torch.float16,
        },
        tokenizer_kwargs={"padding_side": "left"},
    )

    with open(args.input, "r", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))

    if not rows:
        print("No rows found in input CSV.")
        return

    # Precompute per-verse text and book for fast lookups
    verse_texts = [r["text"] for r in rows]
    verse_books = [r["book"] for r in rows]

    # Build prefix sums so any window's text is a single slice + join
    # For window=1 we already have verse_texts; for larger windows we
    # incrementally build text by appending one verse to the previous window.
    texts = []
    metadata = []

    for window in sorted(args.window_sizes):
        if window == 1:
            prev_texts = {}
            for i in range(len(rows)):
                t = verse_texts[i]
                prev_texts[i] = t
                ref = make_ref(verse_books[i], rows[i]['chapter'], rows[i]['verse'],
                               rows[i]['chapter'], rows[i]['verse'])
                texts.append(t)
                metadata.append({
                    "ref": ref,
                    "text": t,
                    "start_row": i,
                    "end_row": i,
                })
        else:
            new_prev = {}
            for i in range(0, len(rows) - window + 1):
                if verse_books[i] != verse_books[i + window - 1]:
                    continue
                # Try to build from cached (window-1) text
                prev = prev_texts.get(i)
                if prev is not None and verse_books[i] == verse_books[i + window - 2]:
                    t = prev + " " + verse_texts[i + window - 1]
                else:
                    t = " ".join(verse_texts[i : i + window])
                new_prev[i] = t
                ref = make_ref(verse_books[i],
                               rows[i]['chapter'], rows[i]['verse'],
                               rows[i + window - 1]['chapter'], rows[i + window - 1]['verse'])
                texts.append(t)
                metadata.append({
                    "ref": ref,
                    "text": t,
                    "start_row": i,
                    "end_row": i + window - 1,
                })
            prev_texts = new_prev

    print(f"Encoding {len(texts)} entries (windows {args.window_sizes})...")
    index = None
    for batch_start in tqdm.tqdm(range(0, len(texts), args.batch_size), desc="Encoding"):
        batch = texts[batch_start : batch_start + args.batch_size]
        embeddings = model.encode(
            batch,
            convert_to_numpy=True,
            normalize_embeddings=True,
            show_progress_bar=False,
        ).astype("float32")
        if embeddings.ndim == 1:
            embeddings = embeddings.reshape(1, -1)

        if index is None:
            index = faiss.IndexFlatIP(embeddings.shape[1])
        index.add(embeddings)

    output_path = Path(args.output)
    faiss.write_index(index, str(output_path))

    meta_path = output_path.with_suffix('.json')
    with open(meta_path, "w", encoding="utf-8") as f:
        json.dump(metadata, f)

    print(f"Index built with {index.ntotal} vectors and saved to {output_path}")

if __name__ == '__main__':
    main()
