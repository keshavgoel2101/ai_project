# RAG Cold Case Detective

A Retrieval-Augmented Generation (RAG) system designed to assist detectives in solving cold cases. This system uses vector similarity search to retrieve relevant evidence from documents and an LLM to provide cited, hallucination-controlled answers.

## Features

- **Document Ingestion**: Loads `.txt` evidence files with automatic text chunking for better retrieval accuracy.
- **Vector Store**: Uses FAISS and SentenceTransformers (`all-MiniLM-L6-v2`) for efficient similarity search.
- **RAG Pipeline**: Integrates Gemini LLM with a strict detective persona prompt to ensure answers are based solely on provided evidence.
- **Source Citation**: Every answer includes explicit citations of the source files (e.g., `witness_sarah.txt`).
- **Hallucination Control**: The system is instructed to state whenever it lacks sufficient evidence to answer a question.

## Project Structure

```text
rag-cold-case-detective/
├── evidence/           ← Case evidence (.txt files)
├── ingest.py           ← Loads and chunks evidence
├── vector_store.py     ← Embeddings + FAISS similarity search
├── rag_chat.py         ← LLM pipeline with citation logic
└── vector_store.pkl    ← Persistent vector store
```

## Quick Start (Reliable Method) 🚀

We have included a startup script to make running the project easy and robust.

1.  **Run the App:**
    ```bash
    ./run_app.sh
    ```
    *This script will automatically clear old processes, start the Python backend, and launch the React frontend.*

2.  **Access:**
    - Frontend: [http://rag-cold-case-detective.vercel.app/](https://rag-cold-case-detective.vercel.app/)
    - Backend: [http://rag-cold-case-detective.onrender.com](https://rag-cold-case-detective.onrender.com)

## Manual Setup (If needed)

1. **Install Dependencies**:
   ```bash
   pip install faiss-cpu sentence-transformers numpy google-generativeai
   ```

2. **Set API Key**:
   Export your Google API Key:
   ```bash
   export GOOGLE_API_KEY="your_api_key_here"
   ```

3. **Run the System**:
   - To ingest and test search: `python vector_store.py`
   - To start the RAG chat: `python rag_chat.py`

## Adding New Evidence

The system is designed to handle multiple documents and incidents easily:

1. **Place Evidence**: Add any case-related `.txt` files into the `evidence/` directory.
2. **Re-Ingest**: 
   - **Via UI**: Click the **Refresh** button in the chat sidebar.
   - **Via Command Line**: Run `python vector_store.py`.
3. **Ask**: The detective will now include the new files in its search and citations.

## Example Query

**Question**: "What evidence confirms the car color?"
**Answer**: "According to `witness_sarah.txt` and `police_log.txt`, the vehicle involved was a silver sedan."
# Trigger deployment
