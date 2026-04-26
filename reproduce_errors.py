import requests
import os

BASE_URL = "http://localhost:8000"

def test_cases_endpoint():
    print("Testing GET /cases...")
    try:
        response = requests.get(f"{BASE_URL}/cases")
        print(f"Status: {response.status_code}")
        if response.status_code != 200:
            print(f"Response: {response.text}")
    except Exception as e:
        print(f"Error connecting to {BASE_URL}/cases: {e}")

def test_upload_endpoint():
    print("\nTesting POST /upload...")
    # Create a dummy test file
    with open("test_evidence.txt", "w") as f:
        f.write("Case ID: Test Case\nThis is a test evidence file.")
    
    try:
        with open("test_evidence.txt", "rb") as f:
            files = {"file": ("test_evidence.txt", f, "text/plain")}
            response = requests.post(f"{BASE_URL}/upload", files=files)
            print(f"Status: {response.status_code}")
            if response.status_code != 200:
                print(f"Response Detail: {response.text}")
    except Exception as e:
        print(f"Error connecting to {BASE_URL}/upload: {e}")
    finally:
        if os.path.exists("test_evidence.txt"):
            os.remove("test_evidence.txt")

if __name__ == "__main__":
    test_cases_endpoint()
    test_upload_endpoint()
