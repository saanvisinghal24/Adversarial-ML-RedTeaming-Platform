from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

ModelType = Literal["sklearn", "xgboost", "pytorch", "onnx"]


class ModelResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True, protected_namespaces=())

    id: UUID
    name: str
    model_type: ModelType
    version: str
    size_bytes: int | None = None
    checksum_sha256: str | None = Field(None, description="sha256 of the uploaded artefact")
    created_at: datetime
