from datetime import date
from decimal import Decimal
from pydantic import BaseModel

class PagamentoCreate(BaseModel):
    dat_pagamento: date
    cod_orgao: int
    val_pagamento: Decimal
    dsc_pagamento: str | None = None

class PagamentoOut(PagamentoCreate):
    seq_pagamento: int

