from backend.services.assistant import civic_assist
import json

print("Sending test query to CivicAssist RAG Engine...")
response = civic_assist("What are the reasons for tax refund delays?")
print("\n--- RESPONSE ---")
print(json.dumps(response, indent=2))
