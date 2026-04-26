from fastapi import FastAPI, HTTPException, UploadFile, File, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel
import rag_chat
from ingest import ingest_evidence
from vector_store import build_vector_store, blind_search
import os
import shutil


app = FastAPI()

# Ensure evidence directory exists
if not os.path.exists("evidence"):
    os.makedirs("evidence")

print("--- DETECTIVE SERVER STARTING UP ---")
print(f"Evidence directory: {os.path.abspath('evidence')}")




app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class ChatRequest(BaseModel):
    message: str

class ChatResponse(BaseModel):
    response: str
    sources: list

@app.get("/")
def read_root():
    return {"status": "Detective API is running"}

@app.get("/health")
def health_check():
    return {"status": "healthy", "api_key_set": bool(os.getenv("GOOGLE_API_KEY"))}

@app.post("/ingest")
async def ingest_endpoint(background_tasks: BackgroundTasks):
    try:
        print("Manual ingest requested.")
        background_tasks.add_task(reindex_task)
        return {"status": "success", "message": "Manual re-indexing started in the background."}
    except Exception as e:
        print(f"Ingest endpoint error: {e}")
        raise HTTPException(status_code=500, detail=str(e))



@app.post("/upload")
async def upload_file(background_tasks: BackgroundTasks, file: UploadFile = File(...)):
    if not file.filename.endswith(".txt"):
         raise HTTPException(status_code=400, detail="Only .txt files are allowed")
    
    file_location = os.path.join("evidence", file.filename)
    try:
        with open(file_location, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        
        # Move indexing to background to avoid timeout
        background_tasks.add_task(reindex_task)
        
        return {"status": "success", "message": f"File '{file.filename}' uploaded. Indexing in progress..."}
    except Exception as e:
        import traceback
        error_details = traceback.format_exc()
        print(f"Upload error: {error_details}")
        raise HTTPException(status_code=500, detail=str(e))

def reindex_task():
    try:
        print("Starting background re-indexing...")
        data = ingest_evidence("evidence")
        if not data:
            print("No evidence found to index. Skipping vector store build.")
            return
        build_vector_store(data)
        print(f"Background re-indexing complete. Processed {len(data)} chunks.")
    except Exception as e:
        import traceback
        print(f"CRITICAL: Background re-indexing failed: {e}")
        print(traceback.format_exc())



@app.get("/cases")
async def get_cases():
    evidence_dir = "evidence"
    if not os.path.exists(evidence_dir):
        return {"cases": []}
    
    cases = set()
    for filename in os.listdir(evidence_dir):
        if filename.endswith(".txt"):
            file_path = os.path.join(evidence_dir, filename)
            try:
                # Use errors='replace' to avoid crashing on encoding issues
                with open(file_path, 'r', encoding='utf-8', errors='replace') as f:
                    first_line = f.readline().strip()
                    if ":" in first_line and (first_line.startswith("Case ID:") or first_line.startswith("Case:")):
                        cases.add(first_line.split(":")[1].strip())
                    else:
                        cases.add("Uncategorized")
            except Exception as e:
                print(f"Error reading case file {filename}: {e}")
                cases.add("Uncategorized")
    
    return {"cases": sorted(list(cases))}

@app.get("/timeline")
async def get_timeline(case_id: str = None):
    try:
        # If case_id is provided, filter or pass it to extraction logic
        # For now, we return the full timeline or a filtered one
        timeline = rag_chat.extract_timeline()
        if case_id and case_id != "All":
             # Optional: filter timeline by case_id if possible
             pass
        return {"timeline": timeline}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/trace")
async def get_trace(case_id: str = "All"):
    """
    Generates a network graph (nodes/links) for the selected case.
    """
    evidence_dir = "evidence"
    if not os.path.exists(evidence_dir):
        return {"nodes": [], "links": []}

    nodes = []
    links = []
    
    # 1. Central Node (The Case)
    root_id = "CASE_ROOT"
    nodes.append({"id": root_id, "label": case_id if case_id != "All" else "Master Archive", "type": "root"})

    files_processed = 0

    for filename in os.listdir(evidence_dir):
        if not filename.endswith(".txt"):
            continue
            
        file_path = os.path.join(evidence_dir, filename)
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
                
                # Check if file belongs to case
                is_relevant = False
                if case_id == "All":
                    is_relevant = True
                elif f"Case: {case_id}" in content or f"Case ID: {case_id}" in content:
                    is_relevant = True
                # Fallback: if filename contains case name (simplified)
                elif case_id.lower().split()[0] in filename.lower(): 
                   is_relevant = True
                
                if is_relevant:
                    file_node_id = f"FILE_{filename}"
                    nodes.append({"id": file_node_id, "label": filename, "type": "file"})
                    links.append({"source": root_id, "target": file_node_id})
                    
                    # Extract simple entities (Capitalized words - naive NER)
                    # This adds "flavor" to the graph without complex NLP
                    words = set()
                    for word in content.split():
                        if word and word[0].isupper() and len(word) > 4:

                            clean_word = word.strip(".,:;\"'")
                            if clean_word not in ["Case", "Date", "Time", "Report", "Evidence"]:
                                words.add(clean_word)
                    
                    # Limit to 3 key entities per file to avoid clutter
                    for i, entity in enumerate(list(words)[:3]):
                        entity_id = f"ENT_{entity}_{filename}"
                        nodes.append({"id": entity_id, "label": entity, "type": "entity"})
                        links.append({"source": file_node_id, "target": entity_id})
                        
        except Exception as e:
            print(f"Error reading {filename}: {e}")
            continue

    return {"nodes": nodes, "links": links}

@app.post("/chat", response_model=ChatResponse)
async def chat_endpoint(request: ChatRequest):
    try:
        # Get response using the logic in rag_chat.py
        response_text = rag_chat.generate_response(request.message)
        
        # Determine if it's an error message or a real response
        # If it's an error, we still want to show it in the chat
        
        # Get raw sources for the Case Board
        results = blind_search(request.message, n_results=3)
        sources = []
        for doc, meta in zip(results['documents'][0], results['metadatas'][0]):
            sources.append({
                "source": meta['source'],
                "content": doc
            })
            
        return ChatResponse(response=response_text, sources=sources)
    except Exception as e:
        # Instead of 500, return a clear message in the chat
        return ChatResponse(
            response=f"SYSTEM ERROR: {str(e)}",
            sources=[]
        )

# Serve Static Files (Frontend)
frontend_path = os.path.join(os.path.dirname(__file__), "frontend", "dist")
if os.path.exists(frontend_path):
    app.mount("/assets", StaticFiles(directory=os.path.join(frontend_path, "assets")), name="assets")

    @app.get("/{rest_of_path:path}")
    async def serve_frontend(rest_of_path: str):
        # Fallback to index.html for React SPA
        return FileResponse(os.path.join(frontend_path, "index.html"))
else:
    print(f"Warning: Frontend dist folder not found at {frontend_path}")

if __name__ == "__main__":

    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
