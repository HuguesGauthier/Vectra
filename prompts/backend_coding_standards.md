# Python Backend Coding Standards

This document outlines the best practices and standards for the Vectra backend codebase. It assumes an expert level of Python proficiency and focuses on maintaining a robust, scalable, and readable asynchronous application.

## 1. Type Hinting & Pydantic models

Strict type enforcement is critical for maintainability.

## 2. Configuration & Environment

- **Dynamic Configuration**: Settings are primarily stored in the database to allow runtime updates.
- **Access Pattern**:
  1. **Primary**: Fetch from Database via `SettingsService` (or cached instance).
  2. **Fallback**: Use `app.core.config.settings` for default values or environment-specific overrides (like DB URL).
- **Environment Variables**: Use `.env` for infrastructure settings (DB host, Redis) and as fallback for secrets.

  ```python
  from app.services.settings_service import SettingsService
  from app.core.config import settings

  # GOOD: Prioritize DB, fallback to config
  openai_key = SettingsService.get_settings().openai_api_key or settings.OPENAI_API_KEY
  ```

- **Always** use type hints for function arguments and return values.
- Use `typing.Optional`, `typing.List`, `typing.Union`, etc. (or newer `|` syntax if Python 3.10+ is strictly enforced, but `typing` is safer for compatibility).
- Use **SQLModel** for database models and Pydantic schemas (unified definition).
- Use **Pydantic** models (V2) for API-specific contracts if they differ significantly from DB models.
- Avoid `Any` unless absolutely necessary. If used, provide a comment explaining why.

```python
# BAD
def process_data(data):
    return data["id"]

# GOOD
from typing import Dict, Any
from uuid import UUID

def process_data(data: Dict[str, Any]) -> UUID:
    return UUID(data["id"])
```

## 3. Async/Await Patterns

We use **AsyncIO** (FastAPI) and **SQLAlchemy Async**.

- **Never blocking operations** in an `async` function.
  - BAD: `time.sleep(1)`, `requests.get()`
  - GOOD: `await asyncio.sleep(1)`, `await httpx.get()`
- **CPU-bound tasks**: If you have heavy sync computation (e.g., pandas over large CSV), offload it using `asyncio.to_thread`.
  ```python
  await asyncio.to_thread(pd.read_csv, file_path)
  ```
- **Session Management**: Always use `async with` context managers for database sessions.
  ```python
  async with SessionLocal() as db:
      result = await db.execute(...)
  ```

## 4. Error Handling

Fail fast and explicitly.

- **VectraException Hierarchy**: ALL custom exceptions must inherit from `VectraException`.
  - Use `FunctionalError` (4xx) for business logic failures (e.g. `DOC_TOO_LARGE`).
  - Use `TechnicalError` (5xx) for system/infrastructure failures (e.g. `FILESYSTEM_ERROR`).
- **Error Codes**: Always provide a specific `error_code` (snake_case uppercase) when raising exceptions. This code is used for frontend translation.
- **Global Handler**: Do NOT catch generic `Exception` in services unless you are wrapping it in a `TechnicalError`. Let 500s bubble up to the global handler in `main.py`.
- **Logging**:
  - `FunctionalError` -> Logged as WARNING (no traceback).
  - `TechnicalError` / Unhandled -> Logged as ERROR (with traceback) to `error_logs` table.

## 5. Project Structure (Service Pattern)

We follow a 3-layer architecture:

1.  **Routes (`api/routes.py`)**:
    - Handle HTTP request/response.
    - Validate inputs (Pydantic).
    - **Call Services**. Do NOT put business logic here.
2.  **Services (`services/`)**:

    - Contain the actual business logic.
    - Reusable, independent of HTTP context.
    - Example: `IngestionService`, `VectorService`.

3.  **Data Access / Models (`models/`)**:
    - **SQLModel** classes (combining SQLAlchemy + Pydantic).
    - Raw DB interaction should happen within Services.

## 6. Distributed Tracing & Logging Strategy

We implement a rigorous **Distributed Tracing** strategy using specialized `ContextVars` and structured logging to trace requests from entry to exit.

### 6.1 Correlation ID (ContextVars)

- **Requirement**: A `ContextVar` named `correlation_id` must be defined in `app/core/logging.py`.
- **Propagation**:
  - Middleware must generate or extract the `X-Correlation-ID` header and set the context.
  - If a function receives a `correlation_id` (e.g., background worker tasks), it MUST update the context context variable.
- **Format**: Every log message MUST start with the prefix: `[%(correlation_id)s]`.

### 6.2 Audit & Refacoring Rules (Reuse vs Flush)

- **Flush:** Remove redundant logs (e.g., `print()`, generic "doing x" logs that add no value over the standardized entry/exit logs).
- **Reuse & Upgrade:** If a legacy log contains unique business info, integrate it into the new structured format or add it as a `DEBUG` log in the Logic phase.
- **Strict Ban**: `print()` is strictly forbidden. Use `logger`.

### 6.3 Instrumentation Pattern

Apply this standard block to **ALL** significant functions (Services, Routes, Workers):

1.  **ENTRY**: `logger.info(f"START | {func_name} | Params: {args_filtered}")`
2.  **LOGIC**: Use `logger.debug()` for intermediate steps (e.g., "Querying Qdrant", "Parsing PDF").
3.  **EXIT**: `logger.info(f"FINISH | {func_name} | Status: Success | Duration: {elapsed}ms")`
4.  **ERROR**: In `except` blocks: `logger.error(f"❌ FAIL | {func_name} | Error: {str(e)}", exc_info=True)`

### 6.4 Security & Privacy

- **Masking**: You MUST strictly filter out sensitive parameters (`api_key`, `password`, `secret`, `token`, `authorization`) from the "Params" log. Replace values with `[MASKED]`.
- **Levels**:
  - `DEBUG`: Internal details, payloads (masked), logic flow.
  - `INFO`: Start/Finish events, high-level attributes.
  - `WARNING`: Handled failures, retries, functional errors.
  - `ERROR`: Unhandled exceptions, system failures (with stack trace).

## 7. AI & RAG Patterns

- **Fallbacks**: Always implement fallbacks for Model/API failures.
- **Separation**: Keep prompt logic, embedding generation, and retrieval separate from API routes.
- **Observability**: Log token usage, latency (if critical), and model decisions at DEBUG level.

## 8. Dependency Injection

- Use FastAPI's `Depends` for request-scoped dependencies (e.g., DB Session, Current User).
- For Services, prefer stateless static methods or Singleton classes (like `VectorService`) initialized cleanly.

## 9. Code Style

- **PEP 8** compliance is mandatory.
- Max line length: 120 chars (pragmatic).
- **Docstrings**: Mandatory for all public modules, classes, and complex functions. Use Google or NumPy style.

```python
def calculate_hash(file_path: str) -> str:
    """
    Calculates the MD5 hash of a file.

    Args:
        file_path (str): The absolute path to the file.

    Returns:
        str: The hexdigest of the hash.
    """
    ...
```

## 10. Git & Versioning

- **Atomic Commits**: One feature/fix per commit.
- **Conventional Commits**: `feat: ...`, `fix: ...`, `refactor: ...`.

## 11. Fullstack Model Consistency

- **Single Source of Truth**: The Backend Pydantic Schemas (`app/schemas/`) define the contract.
- **Immediate Sync**: Any modification to a Pydantic model (adding a field, renaming, changing type) REQUIRES a corresponding update to the TypeScript model in `frontend/src/models/`.
- **Strict Enums**: Do not use raw strings for status or types. Use Python `Enums`. These Enums must be replicated exactly in the Frontend.
- **Review Process**: A PR changing a backend model is invalid if it doesn't include the frontend update.

## 12. Documentation

- **Code Documentation**: Code must be well documented. This is not optional.
  - **Docstrings**: All functions, classes, and methods must have descriptive docstrings explaining their purpose, arguments, and return values.
  - **Inline Comments**: Use comments to explain **why** complex logic exists, not just **what** it does.
  - **Self-documenting code**: prioritize clear variable and function names over excessive comments.

## 13. Dead Code & Cleanup

- **Remove Unused Code**: Do not leave commented-out code or unused functions/variables in the codebase. If it's not used, delete it. Git history preserves it if needed later.
- **Remove Unused Files**: Regularly audit and delete files that are no longer referenced or used by the application.
- **No Debug Scripts**: Do not commit temporary debug scripts (e.g., `debug_test.py`, `scratch.py`). These should be deleted immediately after use or added to `.gitignore`.
- **Cleanliness**: Keep the codebase clean and focused on the current implementation.

## 14. Testing Protocol (Zero-Trust Coding)

- **Mandatory Tests**: Every new feature or service method MUST include a corresponding `pytest` file.
- **Bug Fixes**: Before fixing a bug, create a test case that reproduces the bug (fails), then fix the code until the test passes (TDD).
- **No Mocks for Logic**: Do not mock the logic you are testing. Only mock external dependencies (DB, API, Disk).

## 15. Error Handling & Logging Strategy

- **Standardized Error Codes**:

  - **Rule**: Every exception must raise or return an object containing an `error_code` in `SCREAMING_SNAKE_CASE` (e.g., `FILE_TOO_LARGE`, `DATABASE_CONNECTION_FAILED`).
  - **Action**: Replace all raw text error messages in `app/services/` and `app/api/` with these standardized codes.

- **Exception Hierarchy (`app/core/exceptions.py`)**:

  - **Base Exception**: `VectraException`
  - **Functional (4xx)**:
    - Must have a specific business `error_code` (e.g., `USER_ALREADY_EXISTS`).
    - Examples: `EntityNotFound`, `DuplicateError`, `InvalidStateError`.
  - **Technical (5xx)**:
    - Must have a generic or system-specific code (e.g., `EXTERNAL_API_TIMEOUT`).
    - **MUST** generate and log a unique `error_id` (UUID).
    - Examples: `ExternalDependencyError`, `FileSystemError`.

- **Global Middleware (`app/main.py`)**:
  - **Response Format**:
    ```json
    {
      "id": "550e8400...", // UUID (Required for Technical errors)
      "code": "ENTITY_NOT_FOUND", // SCREAMING_SNAKE_CASE (Required for ALL)
      "message": "Human readable message (fallback)",
      "type": "FUNCTIONAL|TECHNICAL"
    }
    ```
- **Refactoring Rules**:
  - **Input Guard Clauses**: Fail fast if parameters are logically incorrect.
  - **Specific Exception Wrapping**: Wrap external calls (DB, Vector Store, LLM) in dedicated try/except blocks.
  - **Context Preservation**: Re-raise low-level errors (e.g., `asyncpg.UniqueViolationError`) as high-level Functional errors (`DuplicateError`).
- **Edge Cases Checklist**:
  - **Database**: Timeouts, deadlocks, constraint violations.
  - **Filesystem**: Disk full, permissions, corruption.
  - **Memory**: specialized handling for large file processing.
  - **Concurrency**: Handle race conditions (e.g. double deletion).
- **Environment Awareness**:
  - **PROD**: Hide stack trace in response.
  - **DEV**: details allowed in response.
