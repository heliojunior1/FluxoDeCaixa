from ..models import db, Cenario, CenarioAjusteMensal
from sqlalchemy import func

def get_all_cenarios():
    return Cenario.query.order_by(Cenario.nom_cenario).all()

def get_active_cenarios():
    return Cenario.query.filter_by(ind_status='A').order_by(Cenario.nom_cenario).all()

def get_cenario_by_id(cenario_id: int):
    return Cenario.query.get(cenario_id)

def create_cenario(cenario: Cenario):
    db.session.add(cenario)
    db.session.commit()
    return cenario

def update_cenario(cenario: Cenario):
    db.session.commit()
    return cenario

def delete_cenario_logical(cenario_id: int, user_id: int):
    cenario = get_cenario_by_id(cenario_id)
    if cenario:
        cenario.ind_status = 'I'
        cenario.cod_pessoa_alteracao = user_id
        from datetime import date
        cenario.dat_alteracao = date.today()
        db.session.commit()
    return cenario

def get_ajustes_by_cenario(cenario_id: int):
    return CenarioAjusteMensal.query.filter_by(seq_cenario=cenario_id).all()

def delete_ajustes_by_cenario_ano(cenario_id: int, ano: int):
    CenarioAjusteMensal.query.filter_by(seq_cenario=cenario_id, ano=ano).delete()
    db.session.commit()

def create_ajuste(ajuste: CenarioAjusteMensal):
    db.session.add(ajuste)
    # Note: Commit is usually done in batch in the service for adjustments
    return ajuste

def commit():
    db.session.commit()
