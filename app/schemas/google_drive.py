from typing import Literal
from pydantic import BaseModel, Field


class GoogleDocAnonymizeRequest(BaseModel):
    file_id: str = Field(..., description="ID do arquivo no Google Drive")
    engine: str = Field(default="hybrid", description="Motor de anonimização a ser utilizado")
    return_format: Literal["json", "file"] = Field(
        default="json",
        description="Formato de retorno desejado: 'json' com entidades ou 'file' com documento tarjado",
    )
