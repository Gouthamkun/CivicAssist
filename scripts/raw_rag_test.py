import os
import json
import subprocess

def get_ollama_response(prompt):
    try:
        # Using subprocess to call ollama directly to avoid any python lib issues
        result = subprocess.run(
            ['ollama', 'run', 'llama3', prompt],
            capture_output=True,
            text=True,
            encoding='utf-8'
        )
        return result.stdout.strip()
    except Exception as e:
        return f"Error: {e}"

def raw_rag(question):
    print(f"Question: {question}")
    
    # 1. Read Knowledge Base
    kb_content = ""
    kb_dir = "knowledge_base"
    for root, dirs, files in os.walk(kb_dir):
        for file in files:
            if file.endswith(".txt"):
                file_path = os.path.join(root, file)
                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        kb_content += f"\n--- FILE: {file} ---\n"
                        kb_content += f.read()
                except:
                    pass
    
    # 2. Build Prompt
    prompt = f"""
You are CivicAssist. Use the context below to answer the question.
Context:
{kb_content[:15000]}  # Primitive truncation to avoid context limits

Question: {question}

Return ONLY a JSON:
{{
  "answer": "Detailed answer with \\n formatting",
  "action_label": "Optional form label or 'Form is not required'",
  "action_url": ""
}}
"""
    
    # 3. Get Response
    print("Fetching response from Ollama...")
    response_text = get_ollama_response(prompt)
    print("\n--- RAW RESPONSE ---")
    print(response_text)

if __name__ == "__main__":
    raw_rag("What are the reasons for tax refund delays?")
