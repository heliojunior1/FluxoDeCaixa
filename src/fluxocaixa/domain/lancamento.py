from datetime import date
from decimal import Decimal
from pydantic import BaseModel

class LancamentoCreate(BaseModel):
    dat_lancamento: date
    seq_qualificador: int
    val_lancamento: Decimal
    cod_tipo_lancamento: int
    cod_origem_lancamento: int
    dsc_lancamento: str | None = None

class LancamentoOut(LancamentoCreate):
    seq_lancamento: int
