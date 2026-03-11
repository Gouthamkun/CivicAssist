import os
import sys

def trace_import(module_name):
    print(f"Importing {module_name}...")
    try:
        __import__(module_name)
        print(f"Successfully imported {module_name}")
    except Exception as e:
        print(f"Failed to import {module_name}: {e}")

trace_import("langchain_core")
trace_import("langchain_text_splitters")
trace_import("langchain_chroma")
trace_import("langchain_huggingface")

print("All imports finished (or hung)")
