def semantic_search(query, top_k=3):
    # Load index and metadata
    index = faiss.read_index("bible.index")
    with open("metadata.json", "r") as f:
        metadata = json.load(f)
    
    # Encode the search query
    query_vec = model.encode([query]).astype('float32')
    
    # Search the index
    distances, indices = index.search(query_vec, top_k)
    
    print(f"Results for: '{query}'\n")
    for i in range(top_k):
        idx = indices[0][i]
        result = metadata[idx]
        print(f"[{result['ref']}] (Score: {distances[0][i]:.2f})")
        print(f"{result['text']}\n")

# Example usage:
semantic_search("God's promises about peace")