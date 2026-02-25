from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException
from app.core.exceptions import VectraException, EntityNotFound, FunctionalError, TechnicalError


async def mock_global_exception_handler(request: Request, exc: Exception):
    status_code = getattr(exc, "status_code", 500)
    error_code = getattr(exc, "error_code", "INTERNAL_SERVER_ERROR")
    # Handle VectraException message attribute or str(exc)
    message = getattr(exc, "message", str(exc))

    if isinstance(exc, (StarletteHTTPException, RequestValidationError)):
        status_code = getattr(exc, "status_code", 422)
        # HTTP exceptions use 'detail'
        detail = getattr(exc, "detail", None)
        if detail:
            message = str(detail)
        else:
            message = str(exc)
        error_code = f"HTTP_{status_code}"

    # Default to 500 for generic exceptions if status is 500
    if status_code == 500 and not isinstance(exc, VectraException):
        error_code = "TECHNICAL_ERROR"

    return JSONResponse(
        status_code=status_code,
        content={"message": message, "code": error_code},
    )


def get_test_app() -> FastAPI:
    app = FastAPI()
    app.add_exception_handler(VectraException, mock_global_exception_handler)
    app.add_exception_handler(EntityNotFound, mock_global_exception_handler)
    app.add_exception_handler(FunctionalError, mock_global_exception_handler)
    app.add_exception_handler(TechnicalError, mock_global_exception_handler)
    app.add_exception_handler(Exception, mock_global_exception_handler)
    app.add_exception_handler(StarletteHTTPException, mock_global_exception_handler)
    app.add_exception_handler(RequestValidationError, mock_global_exception_handler)
    return app
