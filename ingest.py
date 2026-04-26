import os
import json

def chunk_text(text, chunk_size=500, overlap=50):
    """
    Splits text into smaller chunks with overlap to maintain context.
    """
    chunks = []
    start = 0
    while start < len(text):
        end = start + chunk_size
        chunks.append(text[start:end])
        start += (chunk_size - overlap)
    return chunks

def ingest_evidence(directory):
    """
    Reads text files from a directory and returns a data structure 
    that separates content from source metadata.
    """
    evidence_data = []
    
    if not os.path.exists(directory):
        print(f"Error: Directory {directory} not found.")
        return evidence_data

    for filename in os.listdir(directory):
        if filename.endswith(".txt"):
            file_path = os.path.join(directory, filename)
            try:
                with open(file_path, 'r', encoding='utf-8', errors='replace') as f:
                    full_content = f.read()
                    
                    # Split into chunks (Optional but recommended)
                    chunks = chunk_text(full_content)
                    
                    for chunk in chunks:
                        evidence_data.append({
                            'content': chunk,
                            'source': filename
                        })
            except Exception as e:
                print(f"Skipping {filename} due to ingest error: {e}")
    
    return evidence_data

if __name__ == "__main__":
    evidence_path = "evidence"
    loaded_data = ingest_evidence(evidence_path)
    
    print(f"--- Loaded {len(loaded_data)} evidence chunks ---")
    if loaded_data:
        # Milestone Check: Print one object exactly as requested
        print("\n[Milestone Check] Sample Data Object:")
        print(loaded_data[0])
