import traceback
from backend.services.assistant import civic_assist

try:
    print("Testing civic_assist...")
    response = civic_assist("What is the process for PF withdrawal?")
    print("Response:", response)
except Exception as e:
    print("Error occurred!")
    traceback.print_exc()
