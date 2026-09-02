from pydantic import BaseModel, Field


class QuerySchema(BaseModel):
    query: str = Field(min_length=1, max_length=1000)
    max_rows: int = Field(default=500, ge=1, le=1000)
