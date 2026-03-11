# Requires transformers>=4.51.0
# Requires sentence-transformers>=2.7.0

import argparse
from pathlib import Path
from sentence_transformers import SentenceTransformer
import csv
import faiss
from sentence_transformers import SentenceTransformer

# Load the model
# model = SentenceTransformer("Qwen/Qwen3-Embedding-4B")

def main() -> None:
    parser = argparse.ArgumentParser("")
    parser.add_argument("--input", default=f"{Path(__file__).parent.parent / 'data' / 'bible.csv'}")
    parser.add_argument("--output", default=f"{Path(__file__).parent.parent / 'data' / 'bible.index'}")
    args = parser.parse_args()

    # We recommend enabling flash_attention_2 for better acceleration and memory saving,
    # together with setting `padding_side` to "left":
    model = SentenceTransformer(
        "Qwen/Qwen3-Embedding-8B",
        model_kwargs={"attn_implementation": "flash_attention_2", "device_map": "auto"},
        tokenizer_kwargs={"padding_side": "left"},
    )

    # 1. Initialize Model and Paths
    #model = SentenceTransformer('all-MiniLM-L6-v2') # Light and fast

    # Containers for data
    embeddings = []
    metadata = []

    # 2. Read and Encode
    with open(args.input, "r", encoding="utf-8") as f:
        import pdb; pdb.set_trace()
        reader = csv.DictReader(f) # Convert to list to get total for tqdm
        
        print("Encoding verses...")
        for row in tqdm.tqdm(reader):
            text = row["text"]
            # Create metadata reference
            ref = f"{row['book']} {row['chapter']}:{row['verse']}"
            
            # Generate embedding
            embedding = model.encode(text)
            
            embeddings.append(embedding)
            metadata.append({"ref": ref, "text": text})

    # 3. Build the FAISS Index
    # Convert list to float32 numpy array (FAISS requirement)
    embeddings_array = np.array(embeddings).astype('float32')
    dimension = embeddings_array.shape[1]

    # Create a Flat L2 index (exact search)
    index = faiss.IndexFlatL2(dimension)
    index.add(embeddings_array)

    # 4. Save to Disk
    faiss.write_index(index, index_path)

    # Save metadata separately (needed to reconstruct text from index hits)
    import json
    with open("metadata.json", "w", encoding="utf-8") as f:
        json.dump(metadata, f)

    print(f"Index built with {index.ntotal} vectors and saved to {index_path}")

if __name__ == '__main__':
    main()