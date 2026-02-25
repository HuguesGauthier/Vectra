# Vectra Architecture

Vectra is an **Agentic RAG Assistant** designed to unify structured (SQL) and unstructured (Documents) data into a single, intuitive chat interface.

## Hybrid Architecture

Vectra relies on a powerful dual-engine architecture:

1.  **AI Analyst (Vanna.ai)**: An intelligent agent that generates SQL on-the-fly to answer ad-hoc questions and explore structured databases in real-time.
2.  **Vector Search (LlamaIndex & Qdrant)**: Neural retrieval from internal wikis and documents (PDF, Word, Excel, PowerPoint) acting as a collective memory.

```mermaid
graph TD
    User([User]) <--> Frontend[Frontend Vue.js/Quasar]
    Frontend <--> API[FastAPI Backend]

    subgraph "Hybrid Core"
        API <--> AI_Analyst[AI Analyst / Vanna.ai]
        API <--> RAG[Vector Search / LlamaIndex]
    end

    AI_Analyst <--> SQL_DB[(Structured DB / Postgres, SQL Server...)]
    RAG <--> Qdrant[(Vector DB / Qdrant)]

    API <--> Redis[(Redis Cache)]
    API -- Ingestion triggers --> Worker[Background Worker]
    Worker -- Processing --> Qdrant
```

## Main Components

### 1. Backend API (FastAPI)

The central orchestrator of the system:

- **Smart Routing**: Automatically detects user intent to route queries to either the AI Analyst or the Vector Search engine.
- **Deep Chat UI Orchestration**: Manages streaming responses and interactive chart rendering.
- **Security**: JWT-based enterprise-grade authentication.

### 2. AI Analyst (Vanna.ai)

Specialized in translating natural language into precise SQL queries. It allows for real-time exploration of structured data without pre-defined reports.

### 3. Vector Search (LlamaIndex & Qdrant)

The backbone for unstructured data retrieval. It indexes and searches through your company's documents, acting as a "collective memory".

### 4. Background Worker (APScheduler)

Handles multimodal data ingestion, scheduled sync jobs, and heavy vectorization workloads, ensuring the knowledge base is always up-to-date.

## Tech Stack

### Frontend

- **Vue 3.5 + Quasar 2.16**: Premium UI framework and components.
- **TypeScript 5.9**: Type-safe development.
- **Three.js 0.182**: 3D graphics for advanced visualization.
- **ApexCharts 3.54**: Interactive data visualization.
- **Pinia**: Modern state management.

### Backend

- **FastAPI 0.122**: High-performance asynchronous API framework.
- **SQLModel 0.0.27**: Modern ORM (SQLAlchemy + Pydantic).
- **Alembic**: Database migration management.
- **JWT & Bcrypt**: Industrial-strength security.

### AI Orchestration

- **LlamaIndex 0.14**: Premier RAG and LLM orchestration framework.
- **Vanna.ai 0.7**: Specialized SQL generation agent.
- **Ollama**: Local model inference engine.
- **Faster-Whisper**: Optimized neural audio transcription.
- **Qdrant 1.16**: High-scale neural search engine.

### Infrastructure

- **PostgreSQL 15**: Metadata and persistent storage.
- **Redis 7.1**: Caching and task message broker.
- **Docker & Compose**: Full containerization.
- **NVIDIA CUDA**: Hardware acceleration for AI workloads.

## Security & Privacy

- **Self-Hosted**: Full control over your data; sensitive information never leaves your infrastructure.
- **Model Agnostic**: Compatible with **Gemini**, **OpenAI**, **Mistral**, and **Ollama** (local inference).

---

## Data Flow

1. **User Request**: The user sends a natural language query.
2. **Intent Analysis**: The API determines if the answer lies in structured databases or unstructured documents.
3. **Execution**:
   - **SQL Path**: Vanna.ai generates and executes SQL.
   - **Vector Path**: LlamaIndex performs semantic search in Qdrant.
4. **Response Synthesis**: The LLM compiles the findings into a sourced and clear response.
5. **Streaming**: Results are streamed back to the UI in real-time.
