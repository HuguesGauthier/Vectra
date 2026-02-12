from app.core.settings import Settings
from pydantic import ValidationError

try:
    Settings(ENV="production", SECRET_KEY=None)
except ValidationError as e:
    print(f"ERROR_STR: {str(e)}")
    print(f"ERROR_REPR: {repr(e)}")
    print(f"ERROR_DICT: {e.errors()}")
except Exception as e:
    print(f"OTHER_ERROR: {type(e)} - {e}")
