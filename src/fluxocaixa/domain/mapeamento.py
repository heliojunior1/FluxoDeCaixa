from datetime import date
from pydantic import BaseModel

class MapeamentoCreate(BaseModel):
    seq_qualificador: int
    dsc_mapeamento: str
    txt_condicao: str | None = None
    ind_status: str = 'A'

class MapeamentoOut(MapeamentoCreate):
    seq_mapeamento: int
    dat_inclusao: date | None = None
