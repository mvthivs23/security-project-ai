import re
from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field, field_validator

_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9-]{0,39}$")
Short = Annotated[str, Field(max_length=40)]


class Answers(BaseModel):
    model_config = ConfigDict(extra="forbid")

    types: list[Short] = Field(default_factory=list, max_length=12)
    inst: Short | None = None
    nai: Short | None = None
    run: Short | None = None
    host: Short | None = None
    lang: list[Short] = Field(default_factory=list, max_length=12)
    fw: list[Short] = Field(default_factory=list, max_length=20)
    cai: Short | None = None
    repo: Short | None = None
    pipe: Short | None = None
    prod: Short | None = None
    pii: Short | None = None
    users: Short | None = None
    ext: Short | None = None
    act: Short | None = None
    api: Short | None = None
    mcp: Short | None = None
    code: Short | None = None
    aidev: Short | None = None


class StructuredContext(BaseModel):
    model_config = ConfigDict(extra="forbid")

    entrada: str = Field(default="", max_length=280)
    ia: str = Field(default="", max_length=280)
    acciones: str = Field(default="", max_length=280)
    datos: str = Field(default="", max_length=280)
    integraciones: str = Field(default="", max_length=280)
    usuarios: str = Field(default="", max_length=280)


class UnderstandRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    answers: Answers
    context: str = Field(max_length=10000)


class AnalyzeRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    answers: Answers
    context: str = Field(max_length=10000)
    structured_context: StructuredContext | None = None
    level: int = Field(ge=1, le=3)
    base_control_ids: list[str] = Field(max_length=200)

    @field_validator("base_control_ids")
    @classmethod
    def control_ids(cls, value: list[str]) -> list[str]:
        for item in value:
            if not _ID.fullmatch(item):
                raise ValueError("invalid control id")
        return value
