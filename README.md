<div align="center">

# 🏛️ CivicAssist

### AI-Powered Government Services Assistant using RAG & Local LLMs

![Python](https://img.shields.io/badge/Python-3.11-blue?logo=python)
![FastAPI](https://img.shields.io/badge/FastAPI-Backend-009688?logo=fastapi)
![Ollama](https://img.shields.io/badge/Ollama-Local%20LLM-black)
![RAG](https://img.shields.io/badge/RAG-Retrieval%20Augmented%20Generation-success)
![MIT License](https://img.shields.io/badge/License-MIT-green)

**Making Government Services Simple, Accessible, and AI-Driven**

</div>

---

# 📖 Overview

**CivicAssist** is an AI-powered government assistance platform that helps citizens easily understand and access government services using **Retrieval-Augmented Generation (RAG)** and **Local Large Language Models (LLMs)**.

Instead of navigating multiple government websites and complex documentation, users can simply ask questions in natural language and receive accurate, context-aware responses sourced from official knowledge bases.

The platform is designed to improve citizen engagement, reduce misinformation, and simplify access to government schemes and public services.

---

# 🎯 Problem Statement

Citizens often face challenges such as:

- Difficulty understanding government procedures
- Confusing eligibility criteria
- Scattered information across multiple portals
- Complex legal terminology
- Long search times for simple questions

CivicAssist addresses these problems by providing an AI-powered conversational interface that retrieves verified information from official documentation.

---

# ✨ Features

- 🤖 AI-powered Government Assistant
- 📚 Retrieval-Augmented Generation (RAG)
- 🧠 Local LLM Integration using Ollama
- 🔍 Semantic Search over Government Documents
- 📄 PDF & Document Knowledge Base
- 💬 Natural Language Question Answering
- 🏛️ Support for Multiple Government Departments
- ⚡ FastAPI Backend
- 🔒 Privacy-Friendly Local AI Processing
- 📈 Easily Extensible Knowledge Base

---

# 🏛️ Supported Services

Current knowledge base includes topics such as:

- 💰 Income Tax
- 👨‍💼 EPFO
- 🛂 Passport Services
- 🪪 PAN Card
- 🏦 Government Schemes
- 📑 Official Notifications
- 📋 FAQs

The architecture allows additional departments to be integrated easily.

---

# 🏗️ System Architecture

```text
                    User
                      │
                      ▼
             Web Application / Chat UI
                      │
                      ▼
               FastAPI Backend
                      │
         ┌────────────┼────────────┐
         ▼            ▼            ▼
  Query Processing  Embedding Model  Document Loader
         │            │
         └────────────┼────────────┘
                      ▼
             Vector Database (RAG)
                      │
                      ▼
              Ollama Local LLM
                      │
                      ▼
        Context-Aware Government Response
```

---

# ⚙️ Technology Stack

## Frontend

- React
- HTML
- CSS
- JavaScript

## Backend

- FastAPI
- Python

## AI & Machine Learning

- Ollama
- Retrieval-Augmented Generation (RAG)
- Sentence Transformers
- Embedding Models
- Semantic Search

## Database

- Vector Database
- CSV Knowledge Base
- Structured Government Documents

## Development

- Git
- GitHub

---

# 📂 Project Structure

```text
CivicAssist/
│
├── backend/
├── frontend/
├── data/
├── embeddings/
├── knowledge_base/
├── models/
├── routes/
├── static/
├── docs/
├── app.py
└── README.md
```

---

# 🚀 Core Modules

### 🤖 AI Assistant

Provides conversational answers for government-related queries using natural language.

---

### 📚 Knowledge Base

Stores official government documents, FAQs, and policy information for retrieval.

---

### 🔍 Semantic Search Engine

Finds the most relevant information using vector embeddings rather than keyword matching.

---

### 🧠 RAG Pipeline

Retrieves relevant context from the knowledge base before generating responses, reducing hallucinations and improving accuracy.

---

### 🏛️ Government Information Hub

Supports multiple public services including taxation, employment, identity services, and welfare schemes.

---

# 🌟 Key Highlights

- AI-powered citizen assistance
- Retrieval-Augmented Generation (RAG)
- Local LLM support (No external API dependency)
- Semantic document retrieval
- Modular architecture
- Scalable knowledge base
- Privacy-focused design

---

# 🚀 Installation

Clone the repository

```bash
git clone https://github.com/Gouthamkun/CivicAssist.git
```

Navigate into the project

```bash
cd CivicAssist
```

Install dependencies

```bash
pip install -r requirements.txt
```

Start the backend

```bash
uvicorn app:app --reload
```

Run the frontend

```bash
npm install
npm run dev
```

---

# 📸 Screenshots

Add screenshots here.

```text
assets/screenshots/

home.png
chatbot.png
search.png
knowledge-base.png
```

---

# 🔮 Future Enhancements

- Voice-based interaction
- Multi-language support (Hindi, Telugu, Tamil, etc.)
- OCR for Government Documents
- WhatsApp Integration
- Citizen Profile Memory
- AI Agents for Department-Specific Services
- Government API Integration
- Mobile Application
- Document Upload & Analysis

---

# 📈 Project Highlights

- GenAI Application
- Retrieval-Augmented Generation (RAG)
- Local AI Deployment
- FastAPI Backend
- Vector Search
- Semantic Retrieval
- Government Service Automation
- Citizen-Centric Design

---

# 🤝 Contributing

Contributions are welcome!

1. Fork the repository
2. Create a new branch
3. Commit your changes
4. Push to your branch
5. Submit a Pull Request

---

# 📄 License

Licensed under the MIT License.

---

# 👨‍💻 Author

**Goutham Kundeti**

GitHub: https://github.com/Gouthamkun

---

<div align="center">

### ⭐ If you found this project useful, consider giving it a star!

**Empowering Citizens Through AI-Driven Government Services**

</div>
