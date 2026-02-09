# Backend

This is the Python backend for the project, built with FastAPI.

## Setup

1.  Create a virtual environment (optional but recommended):

    ```bash
    python -m venv venv
    .\venv\Scripts\activate
    ```

2.  Install dependencies:
    ```bash
    pip install -r requirements.txt
    ```

## Running the Server

Run the server with hot-reloading enabled:

```bash
uvicorn main:app --reload
```

The API will be available at `http://127.0.0.1:8000`.
Documentation is available at `http://127.0.0.1:8000/docs`.
