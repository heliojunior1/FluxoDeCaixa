from ..models import db, Cenario, CenarioAjusteMensal
from sqlalchemy import func, extract

def get_all_cenarios():
    return Cenario.query.order_by(Cenario.nom_cenario).all()

def get_active_cenarios():
    return Cenario.query.filter_by(ind_status='A').order_by(Cenario.nom_cenario).all()

def get_cenario_by_id(cenario_id: int):
    return Cenario.query.get(cenario_id)

def get_cenarios_by_name_and_year(nom_cenario: str, year: int):
    return (
        Cenario.query
        .filter(
            Cenario.nom_cenario == nom_cenario,
            extract("year", Cenario.dat_criacao) == year,
        )
        .order_by(Cenario.dat_criacao)
        .all()
    )

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

def get_ajustes_by_cenario_and_year(cenario_id: int, ano: int):
    return CenarioAjusteMensal.query.filter_by(
        seq_cenario=cenario_id, 
        ano=ano
    ).all()

def get_ajuste_by_unique_keys(cenario_id: int, qualificador_id: int, ano: int, mes: int):
    return CenarioAjusteMensal.query.filter_by(
        seq_cenario=cenario_id,
        seq_qualificador=qualificador_id,
        ano=ano,
        mes=mes
    ).first()

def get_ajustes_by_filters(cenario_ids: list[int], anos: list[int], qualificador_ids: list[int]):
    return (
        CenarioAjusteMensal.query.filter(
            CenarioAjusteMensal.seq_cenario.in_(cenario_ids),
            CenarioAjusteMensal.ano.in_(anos),
            CenarioAjusteMensal.seq_qualificador.in_(qualificador_ids),
        ).all()
    )

def delete_ajustes_by_cenario_ano(cenario_id: int, ano: int):
    CenarioAjusteMensal.query.filter_by(seq_cenario=cenario_id, ano=ano).delete()
    db.session.commit()

def create_ajuste(ajuste: CenarioAjusteMensal):
    db.session.add(ajuste)
    # Note: Commit is usually done in batch in the service for adjustments
    return ajuste

def commit():
    db.session.commit()
