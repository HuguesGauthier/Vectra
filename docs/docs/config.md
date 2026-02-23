# Configuration

Vectra uses environment variables for its configuration. Most of these can be set in a `.env` file at the root of the project.

## Core Settings

| Variable       | Description                                | Default       |
| -------------- | ------------------------------------------ | ------------- |
| `ENV`          | Environment (development, production)      | `development` |
| `SECRET_KEY`   | Secret key for JWT authentication          | (Required)    |
| `DATABASE_URL` | SQLAlchemy URL for the PostgreSQL database | (Required)    |
| `QDRANT_HOST`  | Hostname for the Qdrant vector database    | `localhost`   |
| `REDIS_HOST`   | Hostname for the Redis cache/queue         | `localhost`   |

## AI Providers

Vectra supports multiple LLM and Embedding providers:

- **Gemini**: `GEMINI_API_KEY`
- **OpenAI**: `OPENAI_API_KEY`
- **Mistral**: `MISTRAL_API_KEY`
- **Ollama**: `OLLAMA_BASE_URL` (usually `http://localhost:11434`)

## Data Persistence (Docker)

To allow Vectra to access your local folders when running in Docker, you must define the mapping:

```env
# The physical path on your host machine
VECTRA_DATA_PATH=D:/MyDocuments
```

Any Connector path starting with this value will be correctly mapped to the internal Docker `/data` volume.

## Initial Setup

On first startup, Vectra can automatically create a superuser:

```env
FIRST_SUPERUSER=admin@vectra.ai
FIRST_SUPERUSER_PASSWORD=secure_password_here
```

---

> [!TIP]
> For a complete list of available settings and their meanings, please refer to the [app/core/settings.py](file:///c:/Dev/Vectra/backend/app/core/settings.py) file.
