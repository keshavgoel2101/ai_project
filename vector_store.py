

import os
import pickle
import time
from google.genai import Client
from dotenv import load_dotenv

load_dotenv()

# Global variable for the client, initially None
_client = None

def get_client():
    """
    Lazy loads the Gemini Client.
    """
    global _client
    if _client is None:
        from google.genai import Client
        api_key = os.getenv("GOOGLE_API_KEY")
        if not api_key:
            print("Warning: GOOGLE_API_KEY not found in environment variables.")
            return None
        try:
            _client = Client(api_key=api_key)
        except Exception as e:
            print(f"Error initializing Gemini Client: {e}")
            return None
    return _client

def build_vector_store(evidence_data, store_path="vector_store.pkl"):
    """
    Embeds evidence text using Gemini and stores it in a FAISS index with metadata.
    """
    if not evidence_data:
        return None

    documents = [item['content'] for item in evidence_data]
    metadatas = [{"source": item['source']} for item in evidence_data]
    
    # Create embeddings using Gemini
    client = get_client()
    if not client:
        print("Error: Gemini client not initialized. Skipping vector store build.")
        return None
    import numpy as np

    
    # Gemini text-embedding-004 (or gemini-embedding-001)
    # We batch documents to avoid too many API calls
    all_embeddings = []
    batch_size = 50
    for i in range(0, len(documents), batch_size):
        batch = documents[i:i + batch_size]
        
        # Retry logic for rate limits
        retries = 3
        delay = 10
        for attempt in range(retries):
            try:
                response = client.models.embed_content(
                    model='gemini-embedding-001',
                    contents=batch
                )
                batch_embeddings = [e.values for e in response.embeddings]
                all_embeddings.extend(batch_embeddings)
                break
            except Exception as e:
                if "429" in str(e) and attempt < retries - 1:
                    print(f"Embedding rate limit hit. Waiting {delay}s (Attempt {attempt+1})...")
                    time.sleep(delay)
                    delay *= 2
                    continue
                raise e
        
    embeddings = np.array(all_embeddings).astype('float32')
    
    # Initialize FAISS index
    import faiss
    dimension = embeddings.shape[1]
    index = faiss.IndexFlatL2(dimension)
    index.add(embeddings)
    
    # Save index and metadata
    with open(store_path, "wb") as f:
        pickle.dump({"index": index, "metadatas": metadatas, "documents": documents}, f)
    
    return index

def blind_search(query, n_results=1, store_path="vector_store.pkl"):
    """
    Performs a similarity search using Gemini embeddings and FAISS.
    """
    if not os.path.exists(store_path):
        print("Error: Vector store not found. Please build it first.")
        return {"documents": [[]], "metadatas": [[]]}
        
    with open(store_path, "rb") as f:
        data = pickle.load(f)
        index = data["index"]
        metadatas = data["metadatas"]
        documents = data["documents"]
    
    # Embed query using Gemini
    client = get_client()
    if not client:
        print("Error: Gemini client not initialized. Skipping search.")
        return {"documents": [[]], "metadatas": [[]]}
    import numpy as np

    
    response = client.models.embed_content(
        model='gemini-embedding-001',
        contents=query
    )
    query_embedding = np.array([response.embeddings[0].values]).astype('float32')
    
    # Search
    distances, indices = index.search(query_embedding, n_results)
    
    # Format results to mimic ChromaDB structure for compatibility
    res_docs = []
    res_metas = []
    for idx in indices[0]:
        if idx != -1 and idx < len(documents):
            res_docs.append(documents[idx])
            res_metas.append(metadatas[idx])
            
    return {"documents": [res_docs], "metadatas": [res_metas]}

if __name__ == "__main__":
    from ingest import ingest_evidence
    # 1. Load data from Phase 1
    evidence_path = "evidence"
    data = ingest_evidence(evidence_path)
    
    # 2. Build the store
    if data:
        print("Building vector store (FAISS + Gemini)...")
        build_vector_store(data)
        
        # 3. [Milestone Check] The "Blind" Search
        query = "What color was the car?"
        print(f"\n[Milestone Check] Performing Blind Search for: '{query}'")
        
        # Perform vector search
        results = blind_search(query)
        
        # Print result in requested format
        print("\n--- Similarity Search Result ---")
        for doc, meta in zip(results['documents'][0], results['metadatas'][0]):
            print(f"Source: {meta['source']}")
            print(f"Content: {doc.strip()}")
    else:
        print("No evidence found to index.")
