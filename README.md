# Vectra: The Agentic RAG Assistant

<div align="center">
  
  <br/>
  
  <a href="https://github.com/HuguesGauthier/Vectra/blob/main/LICENSE">
    <img src="https://img.shields.io/badge/License-AGPL%20v3-red.svg" alt="License">
  </a>
  <img src="https://img.shields.io/badge/Python-3.10+-yellow.svg" alt="Python">
  <img src="https://img.shields.io/badge/Vue-3.0-green.svg" alt="VueJS">
  <img src="https://img.shields.io/badge/Docker-Ready-blue" alt="Docker">
</div>

## What is Vectra?

Vectra is an **Agentic RAG Assistant** designed to democratize access to corporate data. It unifies structured (SQL) and unstructured (Documents) data into a single, intuitive chat interface.

Vectra relies on a powerful **Hybrid Architecture**:

1.  **AI Analyst (Vanna.ai):** An intelligent agent that generates SQL on-the-fly to answer ad-hoc questions and explore databases in real-time.
2.  **Vector Search (RAG):** Retrieves precise answers from internal wikis and documents, supporting both **PDFs and the entire Microsoft Office suite** (Word, Excel, PowerPoint) via Qdrant.
3.  **Knowledge Decentralization:** Vectra acts as the company’s collective memory. It is specifically designed to offload **"human knowledge hubs"** (the "Joe Expert" syndrome) by making specialized expertise accessible to everyone, 24/7.

---

### Why Vectra?

- **Free up your experts:** Drastically reduces the constant interruptions faced by key employees who historically hold all the technical or procedural knowledge.
- **Document Omniscience:** No longer limited to just PDFs; it indexes your actual working files (Office suite) and internal wikis to provide context-aware answers.
- **Operational Agility:** Converts complex business questions into instant SQL queries without needing to wait for a ticket from the IT or BI departments.

## Key Features

- **Smart Routing:** Automatically detects user intent to determine whether to query structured data (SQL) or internal documentation (Vector).
- **Deep Chat UI:** Features streaming responses, interactive chart rendering, and precise source citations for every answer.
- **Model Agnostic:** Fully compatible with a wide range of LLMs, including **Mistral**, **Gemini**, and **OpenAI**, allowing you to choose the best engine for your privacy and performance needs.
- **Self-Hosted & Secure:** A Docker-first architecture ensuring full control over your data. Your sensitive corporate information never leaves your infrastructure.
- **Multimodal Data Ingestion:** Seamlessly processes PDFs, the complete Microsoft Office suite (Word, Excel, PowerPoint), and internal wikis.
- **Scalable Vector Search:** Powered by Qdrant for high-performance retrieval, even with large volumes of corporate documentation.

## Tech Stack

Vectra is built on a high-performance, **Docker-first** architecture with native **NVIDIA GPU support**, ensuring seamless deployment and enterprise-grade scaling.

### Frontend (Vue.js Ecosystem)

- **Framework:** Vue 3 + [Quasar Framework](https://quasar.dev) (Material Design).
- **State Management:** Pinia.
- **Chat Interface:** [Deep Chat](https://deepchat.dev) (Advanced AI-driven streaming UI).
- **Visualization & Graphics:** ApexCharts for data rendering and **Three.js** for advanced 3D components.
- **Internationalization:** Vue I18n.
- **HTTP Client:** Axios.

### Backend (Python Ecosystem)

- **API Framework:** **FastAPI** (Asynchronous, high-performance).
- **Web Server:** Uvicorn.
- **ORM:** [SQLModel](https://sqlmodel.tiangolo.com/) (Combining the power of SQLAlchemy & Pydantic).
- **Migrations:** Alembic.
- **Security:** JWT (python-jose) & Bcrypt (passlib) for enterprise-grade authentication.
- **Task Scheduling:** APScheduler for background maintenance and sync tasks.

### AI & RAG Orchestration

- **Orchestrator:** **LlamaIndex** (The backbone for LLM data connection and retrieval).
- **SQL Agent:** **Vanna.ai** (Specialized in translating natural language to precise SQL).
- **Local Inference:** **Ollama** for self-hosted model execution.
- **LLM Providers:** Native support for **Mistral**, **Gemini**, **OpenAI**, and **Cohere**.
- **Vector Store:** **Qdrant** (High-performance vector search engine).

### Data & Storage

- **Primary Database:** PostgreSQL 15.
- **External SQL Support:** Native connectivity for SQL Server and MySQL (via ODBC/pyodbc and pytds).
- **Caching & Queue:** **Redis 7**.
- **Document Processing:** \* **PDF:** PyPDF.
  - **Word:** python-docx.
  - **Excel/CSV:** Openpyxl & Pandas.

### Infrastructure & DevTools

- **Containerization:** Full Docker & Docker Compose orchestration.
- **Hardware Acceleration:** NVIDIA GPU support for local LLM and embedding workloads.

## Quick Start (Docker)

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

### Data Persistence (Docker)

To allows Vectra to access your local files and folders in Docker:

1. Define the base path of your documents in your `.env`:
   ```env
   VECTRA_DATA_PATH=D:/MyDocuments
   ```
2. Any connector created with a path starting with `D:/MyDocuments` will be automatically mapped to the internal Docker `/data` volume.

## Environments Setup

Vectra supports multiple environments using Docker Compose profiles.

### 🛠️ Hybrid Development (Recommended)

This mode runs the **Infrastructure** (Postgres, Qdrant, Redis, Ollama) in Docker and your **Application code** locally for better performance and debugging.

1.  **Launch Infrastructure:**
    ```bash
    # Launches only the databases and infra services
    docker compose up -d
    ```
2.  **Launch Backend:**
    ```bash
    cd backend
    pip install -r requirements.txt
    python main.py
    ```
3.  **Launch Frontend:**
    ```bash
    cd frontend
    npm install
    npm run dev
    ```

### 🚀 Production (Full Docker)

This mode builds and runs everything inside optimized Docker containers. It doesn't rely on local code once built.

```bash
# Use --profile app to include the application services
docker compose --profile app -f docker-compose.yml -f docker-compose.prod.yml up -d --build
```

- **Frontend:** http://localhost (Port 80)
- **Backend API:** http://localhost:8000

## 📜 License

Vectra is open-source software licensed under the **GNU AGPL v3**.

> [!IMPORTANT]
> The **AGPL v3** is a "strong copyleft" license. If you modify Vectra or use it to provide a service over a network, you must make your modified source code available to the users of that service.

---

## 💼 Commercial Use

If you wish to:

- **Integrate Vectra** into a proprietary software product.
- **Build a commercial SaaS** without releasing your own source code.
- **Benefit from Enterprise Support** and priority features.

You must purchase a **Commercial License**. Please [contact me](mailto:hugues.gauthier@gmail.com) for enterprise pricing and licensing options.
