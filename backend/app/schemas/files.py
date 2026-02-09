from typing import Optional

from pydantic import BaseModel, Field


class FileStreamingInfo(BaseModel):
    """
    Schema for file streaming metadata.
    """

    file_path: str = Field(..., description="Absolute path to the file on disk")
    media_type: str = Field(..., description="MIME type of the file")
    file_name: str = Field(..., description="Original filename for headers")
