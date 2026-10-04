"""
HTTP Client test for FastAPI /api/v1/chat endpoint
"""
import urllib.request
import json

payload = {
    "user_id": 1,
    "query": "Python Data Structures",
    "difficulty": "easy",
    "questions_count": 2,
    "answers": [
        "A list is an ordered mutable collection",
        "A dictionary stores key-value pairs"
    ]
}

req = urllib.request.Request(
    "http://127.0.0.1:8001/api/v1/chat",
    data=json.dumps(payload).encode("utf-8"),
    headers={"Content-Type": "application/json"}
)

print("Sending request to http://127.0.0.1:8001/api/v1/chat...")
with urllib.request.urlopen(req) as resp:
    data = json.loads(resp.read().decode("utf-8"))
    print("\nAPI Response Status:", resp.status)
    print("\nAPI Response Body:")
    print(json.dumps(data, indent=2))
