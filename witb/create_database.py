# Requires transformers>=4.51.0
# Requires sentence-transformers>=2.7.0

from sentence_transformers import SentenceTransformer

# Load the model
model = SentenceTransformer("Qwen/Qwen3-Embedding-4B")

# We recommend enabling flash_attention_2 for better acceleration and memory saving,
# together with setting `padding_side` to "left":
# model = SentenceTransformer(
#     "Qwen/Qwen3-Embedding-8B",
#     model_kwargs={"attn_implementation": "flash_attention_2", "device_map": "auto"},
#     tokenizer_kwargs={"padding_side": "left"},
# )

# The queries and documents to embed
queries = [
    "What is the capital of China?",
    "Explain gravity",
]
documents = [
    "The capital of China is Beijing.",
    "Gravity is a force that attracts two bodies towards each other. It gives weight to physical objects and is responsible for the movement of planets around the sun.",
]

# Encode the queries and documents. Note that queries benefit from using a prompt
# Here we use the prompt called "query" stored under `model.prompts`, but you can
# also pass your own prompt via the `prompt` argument
import csv
import faiss
from sentence_transformers import SentenceTransformer

# 1. Initialize Model and Paths
model = SentenceTransformer('all-MiniLM-L6-v2') # Light and fast
output_path = "output.csv"
index_path = "bible.index"

# Containers for data
embeddings = []
metadata = []

# 2. Read and Encode
with open(output_path, "r", encoding="utf-8") as f:
    reader = list(csv.DictReader(f)) # Convert to list to get total for tqdm
    
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