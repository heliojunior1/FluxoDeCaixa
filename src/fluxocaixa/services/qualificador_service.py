from ..repositories import qualificador_repository
from ..models import Qualificador

def list_all_qualificadores():
    return qualificador_repository.get_all_qualificadores()

def list_active_qualificadores():
    return qualificador_repository.get_active_qualificadores()

def list_root_qualificadores():
    return qualificador_repository.get_root_qualificadores()

def get_qualificador(qualificador_id: int):
    return qualificador_repository.get_qualificador_by_id(qualificador_id)

def get_qualificador_by_name(name: str):
    return qualificador_repository.get_qualificador_by_name(name)

def list_receita_qualificadores():
    return qualificador_repository.get_receita_qualificadores()

def list_despesa_qualificadores():
    return qualificador_repository.get_despesa_qualificadores()

def list_receita_qualificadores_folha():
    """Retorna apenas qualificadores de receita que não têm filhos."""
    return qualificador_repository.get_receita_qualificadores_folha()

def list_despesa_qualificadores_folha():
    """Retorna apenas qualificadores de despesa que não têm filhos."""
    return qualificador_repository.get_despesa_qualificadores_folha()

def create_qualificador(num_qualificador: str, dsc_qualificador: str, cod_qualificador_pai: int = None):
    qualificador = Qualificador(
        num_qualificador=num_qualificador,
        dsc_qualificador=dsc_qualificador,
        cod_qualificador_pai=cod_qualificador_pai,
    )
    return qualificador_repository.create_qualificador(qualificador)

def update_qualificador(seq_qualificador: int, num_qualificador: str, dsc_qualificador: str, cod_qualificador_pai: int = None):
    qualificador = qualificador_repository.get_qualificador_by_id(seq_qualificador)
    if not qualificador:
        return None
    
    qualificador.num_qualificador = num_qualificador
    qualificador.dsc_qualificador = dsc_qualificador
    qualificador.cod_qualificador_pai = cod_qualificador_pai
    
    return qualificador_repository.update_qualificador(qualificador)

def delete_qualificador(seq_qualificador: int):
    return qualificador_repository.delete_qualificador_logical(seq_qualificador)
