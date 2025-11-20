from ..repositories import cenario_repository
from ..models import Cenario, CenarioAjusteMensal
from datetime import date

def list_cenarios():
    return cenario_repository.get_all_cenarios()

def list_active_cenarios():
    return cenario_repository.get_active_cenarios()

def get_cenario(cenario_id: int):
    return cenario_repository.get_cenario_by_id(cenario_id)

def create_cenario_with_ajustes(nom_cenario: str, dsc_cenario: str, ano: int, ajustes_data: dict, user_id: int = 1):
    novo_cenario = Cenario(
        nom_cenario=nom_cenario,
        dsc_cenario=dsc_cenario,
        ind_status='A',
        cod_pessoa_inclusao=user_id,
    )
    cenario_repository.create_cenario(novo_cenario)
    
    for key, value in ajustes_data.items():
        if key.startswith('val_ajuste_') and value:
            parts = key.split('_')
            mes = parts[2]
            seq_q = parts[3]
            seq_qualificador = int(seq_q)
            val_ajuste = float(value)
            cod_tipo_ajuste = ajustes_data.get(f'cod_tipo_ajuste_{mes}_{seq_qualificador}', 'P')
            
            novo_ajuste = CenarioAjusteMensal(
                seq_cenario=novo_cenario.seq_cenario,
                seq_qualificador=seq_qualificador,
                ano=ano,
                mes=int(mes),
                cod_tipo_ajuste=cod_tipo_ajuste,
                val_ajuste=val_ajuste,
            )
            cenario_repository.create_ajuste(novo_ajuste)
            
    cenario_repository.commit()
    return novo_cenario

def update_cenario_with_ajustes(cenario_id: int, nom_cenario: str, dsc_cenario: str, ano: int, ajustes_data: dict, user_id: int = 1):
    cenario = cenario_repository.get_cenario_by_id(cenario_id)
    if not cenario:
        return None
        
    cenario.nom_cenario = nom_cenario
    cenario.dsc_cenario = dsc_cenario
    cenario.dat_alteracao = date.today()
    cenario.cod_pessoa_alteracao = user_id
    
    cenario_repository.delete_ajustes_by_cenario_ano(cenario_id, ano)
    
    for key, value in ajustes_data.items():
        if key.startswith('val_ajuste_') and value:
            parts = key.split('_')
            mes = parts[2]
            seq_q = parts[3]
            seq_qualificador = int(seq_q)
            cod_tipo_ajuste = ajustes_data.get(f'cod_tipo_ajuste_{mes}_{seq_qualificador}')
            
            novo_ajuste = CenarioAjusteMensal(
                seq_cenario=cenario.seq_cenario,
                seq_qualificador=seq_qualificador,
                ano=ano,
                mes=int(mes),
                cod_tipo_ajuste=cod_tipo_ajuste,
                val_ajuste=float(value),
            )
            cenario_repository.create_ajuste(novo_ajuste)
            
    cenario_repository.commit()
    return cenario

def delete_cenario(cenario_id: int, user_id: int = 1):
    return cenario_repository.delete_cenario_logical(cenario_id, user_id)

def get_ajustes_dict(cenario_id: int):
    ajustes = cenario_repository.get_ajustes_by_cenario(cenario_id)
    return {
        f"{a.ano}_{a.mes}_{a.seq_qualificador}": {
            'ano': a.ano,
            'mes': a.mes,
            'cod_tipo_ajuste': a.cod_tipo_ajuste,
            'val_ajuste': float(a.val_ajuste),
        }
        for a in ajustes
    }

def get_ajustes_list(cenario_id: int):
    return cenario_repository.get_ajustes_by_cenario(cenario_id)
