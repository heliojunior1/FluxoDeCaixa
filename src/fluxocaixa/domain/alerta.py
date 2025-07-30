from datetime import date
from pydantic import BaseModel

class AlertaCreate(BaseModel):
    nom_alerta: str
    metric: str
    logic: str
    valor: float | None = None
    period: str | None = None
    seq_qualificador: int | None = None
    notif_system: str = 'S'
    notif_email: str = 'N'

class AlertaUpdate(AlertaCreate):
    dat_alteracao: date | None = None
