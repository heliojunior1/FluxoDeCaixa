from ..models import db, Qualificador

def get_all_qualificadores():
    return Qualificador.query.order_by(Qualificador.num_qualificador).all()

def get_active_qualificadores():
    return Qualificador.query.filter_by(ind_status='A').order_by(Qualificador.num_qualificador).all()

def get_root_qualificadores():
    return Qualificador.query.filter_by(ind_status='A', cod_qualificador_pai=None).order_by(Qualificador.num_qualificador).all()

def get_qualificador_by_id(qualificador_id: int):
    return Qualificador.query.get(qualificador_id)

def get_qualificadores_by_ids(ids: list[int]):
    return Qualificador.query.filter(
        Qualificador.seq_qualificador.in_(ids)
    ).all()

def get_qualificador_by_name(name: str):
    from sqlalchemy import func
    return Qualificador.query.filter(func.lower(Qualificador.dsc_qualificador) == name.lower()).first()

def get_receita_qualificadores():
    return Qualificador.query.filter(
        Qualificador.num_qualificador.startswith('1'),
        Qualificador.ind_status == 'A',
    ).order_by(Qualificador.num_qualificador).all()

def get_despesa_qualificadores():
    return Qualificador.query.filter(
        Qualificador.num_qualificador.startswith('2'),
        Qualificador.ind_status == 'A',
    ).order_by(Qualificador.num_qualificador).all()

def get_receita_qualificadores_folha():
    """Retorna apenas qualificadores de receita que não têm filhos (folhas da árvore)."""
    from sqlalchemy import not_, exists, select
    
    # Subquery para verificar se existe algum filho
    subquery = select(Qualificador.seq_qualificador).where(
        Qualificador.cod_qualificador_pai == Qualificador.seq_qualificador
    ).correlate(Qualificador)
    
    # Buscar todos os qualificadores de receita
    todos = Qualificador.query.filter(
        Qualificador.num_qualificador.startswith('1'),
        Qualificador.ind_status == 'A',
    ).order_by(Qualificador.num_qualificador).all()
    
    # Filtrar apenas os que não têm filhos
    ids_pais = set(q.cod_qualificador_pai for q in todos if q.cod_qualificador_pai)
    folhas = [q for q in todos if q.seq_qualificador not in ids_pais]
    
    return folhas

def get_despesa_qualificadores_folha():
    """Retorna apenas qualificadores de despesa que não têm filhos (folhas da árvore)."""
    # Buscar todos os qualificadores de despesa
    todos = Qualificador.query.filter(
        Qualificador.num_qualificador.startswith('2'),
        Qualificador.ind_status == 'A',
    ).order_by(Qualificador.num_qualificador).all()
    
    # Filtrar apenas os que não têm filhos
    ids_pais = set(q.cod_qualificador_pai for q in todos if q.cod_qualificador_pai)
    folhas = [q for q in todos if q.seq_qualificador not in ids_pais]
    
    return folhas

def create_qualificador(qualificador: Qualificador):
    db.session.add(qualificador)
    db.session.commit()
    return qualificador

def update_qualificador(qualificador: Qualificador):
    db.session.commit()
    return qualificador

def delete_qualificador_logical(qualificador_id: int):
    qualificador = get_qualificador_by_id(qualificador_id)
    if qualificador:
        qualificador.ind_status = 'I'
        db.session.commit()
    return qualificador

def count_qualificadores():
    return Qualificador.query.count()

def get_qualificadores_limit(limit: int):
    return Qualificador.query.limit(limit).all()
