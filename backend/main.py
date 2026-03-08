from fastapi import FastAPI
from pydantic import BaseModel
from backend.services.assistant import civic_assist

app = FastAPI()


class QueryRequest(BaseModel):
    question: str


@app.get("/")
def home():
    return {"message": "CivicAssist AI running"}


@app.post("/ask")
def ask(request: QueryRequest):
    response = civic_assist(request.question)
    return {"response": response}