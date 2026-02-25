# Vectra: The Agentic RAG Assistant

<div align="center">
  
  <br/>
  
  [![License](https://img.shields.io/badge/License-AGPL%20v3-red.svg)](https://github.com/HuguesGauthier/Vectra/blob/main/LICENSE)
  ![Python](https://img.shields.io/badge/Python-3.12+-3776AB?style=flat&logo=python&logoColor=white)
  ![FastAPI](https://img.shields.io/badge/FastAPI-0.122+-009688?style=flat&logo=fastapi&logoColor=white)
  ![VueJS](https://img.shields.io/badge/Vue.js-3.5-4FC08D?style=flat&logo=vuedotjs&logoColor=white)
  ![Quasar](https://img.shields.io/badge/Quasar-2.16-1976D2?style=flat&logo=quasar&logoColor=white)
  ![TypeScript](https://img.shields.io/badge/TypeScript-5.9-3178C6?style=flat&logo=typescript&logoColor=white)
  ![PostgreSQL](https://img.shields.io/badge/PostgreSQL-15-4169E1?style=flat&logo=postgresql&logoColor=white)
  ![Redis](https://img.shields.io/badge/Redis-7.1-DC382D?style=flat&logo=redis&logoColor=white)
  ![Docker](https://img.shields.io/badge/Docker-Ready-2496ED?style=flat&logo=docker&logoColor=white)
  ![NVIDIA](https://img.shields.io/badge/NVIDIA-CUDA%20Ready-76B900?style=flat&logo=nvidia&logoColor=white)
  ![LlamaIndex](https://img.shields.io/badge/Orchestrator-LlamaIndex%200.14-black?style=flat)
  ![Qdrant](https://img.shields.io/badge/Vector%20DB-Qdrant%201.16-red?style=flat)

</div>

## What is Vectra?

Vectra is a state-of-the-art **Agentic RAG Assistant** designed to unify corporate knowledge. It bridges the gap between structured databases and unstructured documentation through a high-end, intuitive interface.

Vectra relies on a powerful **Hybrid Architecture**:

1.  **AI Analyst (Vanna.ai):** An intelligent agent that generates SQL on-the-fly to answer ad-hoc questions and explore databases in real-time.
2.  **Vector Search (RAG):** Neural retrieval from internal wikis and documents, supporting **PDFs and the entire Microsoft Office suite** (Word, Excel, PowerPoint) via Qdrant.
3.  **Knowledge Centralization:** Specifically built to solve the "Knowledge Silo" problem by making specialized expertise accessible to everyone, 24/7.

---

### Why Vectra?

- **Free up your experts:** Reduces interruptions by making technical and procedural knowledge self-service.
- **Document Omniscience:** Indexes PDFs, Word, Excel, PowerPoint, and internal wikis for context-aware answers.
- **Operational Agility:** Instant SQL generation for complex business questions without IT tickets.
- **Privacy First:** Fully self-hosted architecture; your data never leaves your infrastructure.

## Key Features

- **Smart Intent Routing:** Automatically detects whether to query SQL databases or document vector stores.
- **Interactive Analytics:** Real-time chart rendering (ApexCharts) for SQL query results.
- **Live Voice Input:** Integrated **Web Speech API** for real-time hands-free chat interaction.
- **Audio Transcription:** High-performance neural processing for audio files and recordings via **Whisper**.
- **Admin Dashboard:** Complete user management, connector monitoring, and system health tracking.
- **Enterprise Connectors:** Native support for SQL Server, MySQL, PostgreSQL, and local/network filesystems.
- **Professional Chat UI:** Streaming responses, precise source citations, and glassmorphism design.
- **Hardware Acceleration:** Native **NVIDIA GPU (CUDA)** support for local LLMs and STT.
- **Internationalization:** Full support for multiple languages via Vue I18n.
- **3D Visualization:** Advanced UI components powered by Three.js.

## Tech Stack

### Frontend

- **Vue 3 + Quasar:** Premium Material Design UI component library.
- **Pinia:** Modern state management.
- **Three.js:** 3D graphics for advanced visualization.
- **ApexCharts:** Interactive data visualization.
- **Axios:** Robust HTTP client with interceptors.

### Backend

- **FastAPI:** High-performance, asynchronous Python API framework.
- **SQLModel:** Modern ORM bridging SQLAlchemy and Pydantic.
- **Alembic:** Structured database migrations.
- **APScheduler:** Background task orchestration and sync jobs.
- **JWT & Bcrypt:** Industrial-strength security and authentication.

### AI Orchestration

- **LlamaIndex:** The premier framework for RAG and LLM data connection.
- **Vanna.ai:** Specialized SQL generation agent.
- **Ollama:** Local inference engine for models like Mistral and Llama 3.
- **Faster-Whisper:** Neural engine for high-accuracy audio transcription and content analysis.
- **Web Speech API:** Native browser integration for real-time voice-to-text input.
- **Multi-Provider Support:** Native integration for **Gemini, Claude, OpenAI, Mistral, and Cohere**.
- **Qdrant:** High-scale vector database for neural search.

### Infrastructure & Storage

- **PostgreSQL 15:** Primary metadata and assistant storage.
- **Redis 7:** High-speed caching and task message broker.
- **Docker & Compose:** Full containerization with environment isolation.
- **CUDA Support:** Direct GPU passthrough for AI workloads.

## The Vectra Stack (Docker Services)

| Service                  | Container                      | Role                                     |
| :----------------------- | :----------------------------- | :--------------------------------------- |
| **Backend API**          | `vectra-api`                   | FastAPI server & business logic          |
| **Frontend**             | `vectra-frontend`              | Vue 3 Dashboard interface                |
| **Worker**               | `vectra-worker`                | Async processing (Ingestion, Sync)       |
| **Database**             | `vectra-postgres`              | Metadata & Persistent storage            |
| **Vector Store**         | `vectra-qdrant`                | Neural search & Embeddings               |
| **Cache/Queue**          | `vectra-redis`                 | Redis broker & Performance caching       |
| **LLM Engine**           | `vectra-ollama`                | Local model inference (Mistral, etc.)    |
| **Transcription Engine** | `vectra-whisper`               | Faster-Whisper for audio file processing |
| **Admin Tools**          | `vectra-pgadmin` / `commander` | Visual management interfaces             |

---

## System Requirements

Vectra is designed to be flexible. It can run on a modern laptop for evaluation, but for a production-grade experience with local AI, performance scales directly with your hardware.

| Component   | Cloud API (Gemini/Claude/etc.) | Minimum (Local AI Laptop) | Recommended (Local GPU Workstation)          |
| :---------- | :----------------------------- | :------------------------ | :------------------------------------------- |
| **CPU**     | Any modern Dual-Core           | Intel i5 / AMD Ryzen 5    | Intel i7+ / AMD Ryzen 7+ / Apple M2+         |
| **RAM**     | 4-8 GB                         | 16 GB                     | 32 GB+                                       |
| **GPU**     | Not Required                   | Integrated (Slow)         | **NVIDIA RTX 30/40 (8GB+ VRAM)** / Apple NPU |
| **Storage** | ~4 GB (Platform core)          | ~25 GB (Local AI Engines) | 60 GB+ (High-res models & context)           |

> [!IMPORTANT]
> **Cloud vs. Local AI:** The hardware requirements above primarily apply if you intend to run **local models** (via Ollama or Whisper). If you plan to use **Cloud APIs** (such as Gemini, Claude, Mistral, or OpenAI), the resource usage on your machine is minimal, and Vectra will run smoothly on any standard modern computer.

---

## Quick Start (Docker)

> [!TIP]
> **For a complete, step-by-step installation guide (including prerequisites, NVIDIA drivers, and troubleshooting), please read the [Detailed Installation Guide](docs/docs/install.md).**

### 1. Simple Launch

**Linux / macOS / PowerShell:**

```bash
git clone https://github.com/HuguesGauthier/Vectra.git
cd Vectra
cp .env.example .env
docker compose --profile dev up -d
```

**Windows (Command Prompt):**

```cmd
git clone https://github.com/HuguesGauthier/Vectra.git
cd Vectra
copy .env.example .env
docker compose --profile dev up -d
```

Access the UI at: **http://localhost:9000**

### Data Persistence

Map your local files by setting `VECTRA_DATA_PATH` in your `.env`:

```env
VECTRA_DATA_PATH=D:/MyDocuments
```

## Development Environments

### Hybrid Development

Run infrastructure in Docker and code locally for fast debugging:

1. **Infra:** `docker compose --profile dev up -d`
2. **Backend:** `cd backend && pip install -r requirements.txt && python main.py`
3. **Frontend:** `cd frontend && npm install && npm run dev`

### Production

```bash
docker compose --profile prod up -d --build
```

---

## License & Commercial

Vectra is licensed under the **GNU AGPL v3**.

> [!IMPORTANT]
> Modifications or network usage require sharing the source code under AGPL.

For **Proprietary Integration**, **Commercial SaaS**, or **Enterprise Support**, please [contact me](mailto:hugues.gauthier@gmail.com) for a **Commercial License**.
