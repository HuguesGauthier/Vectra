# 🧠 Vectra: The Agentic RAG Assistant

<div align="center">
  
  <br/>
  
  <a href="https://github.com/HuguesGauthier/Vectra/blob/main/LICENSE">
    <img src="https://img.shields.io/badge/License-AGPL%20v3-red.svg" alt="License">
  </a>
  <img src="https://img.shields.io/badge/Python-3.10+-yellow.svg" alt="Python">
  <img src="https://img.shields.io/badge/Vue-3.0-green.svg" alt="VueJS">
  <img src="https://img.shields.io/badge/Docker-Ready-blue" alt="Docker">
</div>

## 🚀 What is Vectra?

Vectra is an **Agentic RAG Assistant** designed to democratize access to corporate data. It unifies structured (SQL) and unstructured (Docs) data into a single chat interface.

It relies on a powerful **Tri-Hybrid Architecture**:

1.  **Certified SQL:** Runs predefined, secure SQL views for 100% accurate KPIs.
2.  **AI Analyst (Vanna.ai):** Generates SQL on-the-fly for ad-hoc exploration.
3.  **Vector Search (RAG):** Retrieves answers from PDF procedures and internal wikis (via Qdrant).

## ✨ Key Features

* **Smart Routing:** Automatically detects if the user needs a number (SQL) or a procedure (Vector).
* **Deep Chat UI:** Streaming responses, chart rendering, and source citations.
* **Agnostic:** Compatible with OpenAI, Gemini, and Azure OpenAI.
* **Self-Hosted:** Full control over your data. Docker-first architecture.

## 🛠️ Tech Stack

* **Backend:** FastAPI (Python)
* **Frontend:** Vue 3 + Quasar + Deep Chat
* **Vector Store:** Qdrant
* **SQL Engine:** SQL Server / MySQL (via ODBC)

## ⚡ Quick Start (Docker)

Get Vectra running in 2 minutes:

```bash
# 1. Clone the repo
git clone [https://github.com/HuguesGauthier/Vectra.git](https://github.com/HuguesGauthier/Vectra.git)
cd Vectra

# 2. Configure environment
cp .env.example .env
# Edit .env with your API Keys

# 3. Launch
docker-compose up -d
```
Access the UI at: http://localhost:9000

📜 License
Vectra is open-source software licensed under the GNU AGPL v3.

💼 Commercial Use
If you want to integrate Vectra into a proprietary software or a commercial SaaS product without open-sourcing your own code, you must purchase a Commercial License.

Please contact me for enterprise pricing and licensing options.
