# Configuration

Vectra uses environment variables for configuration. Copy the `.env.example` file to `.env` and fill it in.

```env
GEMINI_API_KEY=your_key_here
DATABASE_URL=postgresql+asyncpg://user:password@localhost:5432/vectra
QDRANT_HOST=localhost
REDIS_HOST=localhost
```

For a full list of available settings, please refer to the `app/core/settings.py` file.
