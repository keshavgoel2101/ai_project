import os
import time
from google.genai import Client
from dotenv import load_dotenv
from vector_store import blind_search

# Load environment variables from .env file
load_dotenv()

# Configure the Gemini API
api_key = os.getenv("GOOGLE_API_KEY")
client = None
if not api_key:
    print("Warning: GOOGLE_API_KEY not found in environment variables.")
else:
    try:
        client = Client(api_key=api_key)
    except Exception as e:
        print(f"Error initializing Gemini Client: {e}")

def get_gemini_client():
    if client is None:
        raise ValueError("Gemini Client not initialized. Check your GOOGLE_API_KEY.")
    return client

def generate_response(query, retries=3):
    """
    Retrieves evidence and generates a response using Gemini with strict citations.
    Includes exponential backoff retry logic for rate limits.
    """
    # 1. Retrieve top 2-3 relevant documents
    results = blind_search(query, n_results=3)
    
    # 2. Format context for the prompt
    context_entries = []
    for doc, meta in zip(results['documents'][0], results['metadatas'][0]):
        context_entries.append(f"SOURCE: {meta['source']}\nCONTENT: {doc.strip()}")
    
    retrieved_documents = "\n\n".join(context_entries)
    
    # 3. Create Strong Prompt
    prompt = f"""
You are a smart detective assistant.
Answer ONLY using the context below.
Do not invent information.
Cite sources explicitly using their filenames (e.g., [source.txt]).

Formatting Rules:
- If the user asks for "key points", "summary", or a "list", YOU MUST use a succinct bulleted list.
- If the user asks a specific question, answer directly.
- Always include the source filename for every fact.

Context:
{retrieved_documents}

Question:
{query}
    """
    
    delay = 5
    for attempt in range(retries):
        try:
            gemini_client = get_gemini_client()
            response = gemini_client.models.generate_content(
                model='gemini-2.0-flash', contents=prompt
            )
            return response.text.strip()

        except Exception as e:
            error_str = str(e)
            print(f"Gemini Error in generate_response: {error_str}")
            if "429" in error_str or "RESOURCE_EXHAUSTED" in error_str:
                if attempt < retries - 1:
                    print(f"Rate limit hit. Waiting {delay} seconds (Attempt {attempt + 1})...")
                    time.sleep(delay)
                    delay *= 2
                    continue
                else:
                    return "DETECTIVE LOG: I've hit the Gemini rate limit multiple times. Please wait a minute before asking another question."
            return f"Error connecting to AI Detective: {error_str}"


def extract_timeline(retries=3):
    """
    Reads all text files in the evidence folder and uses Gemini to 
    extract a chronological timeline of events.
    Includes exponential backoff retry logic for rate limits.
    """
    evidence_dir = "evidence"
    all_content = []
    
    if not os.path.exists(evidence_dir):
        return []

    for filename in os.listdir(evidence_dir):
        if filename.endswith(".txt"):
            try:
                with open(os.path.join(evidence_dir, filename), 'r', encoding='utf-8', errors='replace') as f:
                    all_content.append(f"Source: {filename}\nContent: {f.read()}")
            except Exception as e:
                print(f"Error reading {filename} for timeline: {e}")

    context_text = "\n\n---\n\n".join(all_content)
    
    prompt = f"""
    Review the following cold case evidence and extract a chronological timeline of events.
    For each event, provide:
    1. A precise timestamp/date (as mentioned in the text).
    2. A brief description of the event.
    3. The source file name.
    
    EVIDENCE:
    {context_text}
    
    Format your response as a valid JSON list of objects like this:
    [
      {{"time": "2023-10-14 21:00", "event": "Man in dark hoodie seen running", "source": "witness_sarah.txt"}},
      ...
    ]
    Sort the events from oldest to newest. Return ONLY the JSON.
    """
    
    delay = 5
    for attempt in range(retries):
        try:
            gemini_client = get_gemini_client()
            response = gemini_client.models.generate_content(
                model='gemini-2.0-flash', contents=prompt
            )

            # Clean potential markdown wrapping
            json_text = response.text.strip().replace('```json', '').replace('```', '')
            import json
            return json.loads(json_text)
        except Exception as e:
            error_str = str(e)
            print(f"Gemini Error in extract_timeline: {error_str}")
            if ("429" in error_str or "RESOURCE_EXHAUSTED" in error_str) and attempt < retries - 1:
                print(f"Timeline extraction hit rate limit. Retrying in {delay}s...")
                time.sleep(delay)
                delay *= 2
                continue
            return []


def main():
    print("--- Cold Case Detective RAG Pipeline ---")
    print("Ask a question about the case (type 'exit' to quit).\n")
    
    while True:
        user_input = input("Question: ")
        if user_input.lower() == 'exit':
            break
            
        print("\nDetective is reviewing evidence...")
        answer = generate_response(user_input)
        print(f"\nFinal Answer: {answer}\n")

if __name__ == "__main__":
    # The interactive loop is disabled by default for the API server
    # main()
    pass
