from datetime import date, datetime
from pydantic import BaseModel


class AlertaGeradoCreate(BaseModel):
    """DTO para criação de alerta gerado."""
    seq_alerta: int | None = None
    dat_processamento: date | None = None  # None = alerta de demonstração
    dat_referencia: date
    valor_obtido: float | None = None
    valor_esperado: float | None = None
    mensagem: str
    categoria: str
    severidade: str = 'INFO'


class AlertaGeradoUpdate(BaseModel):
    """DTO para atualização de alerta gerado."""
    ind_lido: str | None = None
    ind_resolvido: str | None = None
    dat_leitura: datetime | None = None
    dat_resolucao: datetime | None = None
