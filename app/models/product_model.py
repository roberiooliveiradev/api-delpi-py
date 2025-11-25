from __future__ import annotations
from pydantic import BaseModel, Field, ConfigDict
from typing import List, Optional

class Product(BaseModel):
    code: str = Field(..., alias="B1_COD")
    description: str = Field(..., alias="B1_DESC")
    group: Optional[str] = Field(None, alias="B1_GRUPO")
    components: Optional[List["Product"]] = []

    model_config = ConfigDict(extra="allow")  # ✅ permite colunas adicionais sem erro

class ProductSearchRequest(BaseModel):
    page: int = 1
    page_size: int = 50
    code: Optional[str] = None
    description: Optional[str] = None
    group: Optional[str] = None
