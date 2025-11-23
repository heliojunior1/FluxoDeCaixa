"""Repository for Simulador de Cenários functionality."""

from typing import List, Optional
from sqlalchemy import and_

from ..models import (
    db,
    SimuladorCenario,
    CenarioReceita,
    CenarioReceitaAjuste,
    CenarioDespesa,
    CenarioDespesaAjuste,
    ModeloEconomicoParametro,
)


# ==================== SimuladorCenario ====================

def get_all_simuladores() -> List[SimuladorCenario]:
    """Retorna todos os cenários simuladores."""
    return SimuladorCenario.query.order_by(SimuladorCenario.dat_criacao.desc()).all()


def get_active_simuladores() -> List[SimuladorCenario]:
    """Retorna apenas cenários ativos."""
    return (
        SimuladorCenario.query
        .filter_by(ind_status='A')
        .order_by(SimuladorCenario.dat_criacao.desc())
        .all()
    )


def get_simulador_by_id(seq_simulador_cenario: int) -> Optional[SimuladorCenario]:
    """Busca um cenário simulador por ID."""
    return SimuladorCenario.query.get(seq_simulador_cenario)


def create_simulador(simulador: SimuladorCenario) -> SimuladorCenario:
    """Cria um novo cenário simulador."""
    db.session.add(simulador)
    db.session.commit()
    return simulador


def update_simulador(simulador: SimuladorCenario) -> SimuladorCenario:
    """Atualiza um cenário simulador existente."""
    db.session.commit()
    return simulador


def delete_simulador_logical(seq_simulador_cenario: int, user_id: int = 1) -> Optional[SimuladorCenario]:
    """Inativa logicamente um cenário simulador."""
    from datetime import date
    
    simulador = get_simulador_by_id(seq_simulador_cenario)
    if simulador:
        simulador.ind_status = 'I'
        simulador.cod_pessoa_alteracao = user_id
        simulador.dat_alteracao = date.today()
        db.session.commit()
    return simulador


# ==================== CenarioReceita ====================

def get_cenario_receita_by_simulador(seq_simulador_cenario: int) -> Optional[CenarioReceita]:
    """Busca configuração de receita por ID do simulador."""
    return CenarioReceita.query.filter_by(seq_simulador_cenario=seq_simulador_cenario).first()


def create_cenario_receita(cenario_receita: CenarioReceita) -> CenarioReceita:
    """Cria configuração de receita."""
    db.session.add(cenario_receita)
    db.session.commit()
    return cenario_receita


def update_cenario_receita(cenario_receita: CenarioReceita) -> CenarioReceita:
    """Atualiza configuração de receita."""
    db.session.commit()
    return cenario_receita


# ==================== CenarioReceitaAjuste ====================

def get_ajustes_receita_by_cenario(seq_cenario_receita: int) -> List[CenarioReceitaAjuste]:
    """Retorna todos os ajustes de um cenário de receita."""
    return CenarioReceitaAjuste.query.filter_by(seq_cenario_receita=seq_cenario_receita).all()


def get_ajustes_receita_by_cenario_and_year(seq_cenario_receita: int, ano: int) -> List[CenarioReceitaAjuste]:
    """Retorna ajustes de receita por ano."""
    return (
        CenarioReceitaAjuste.query
        .filter_by(seq_cenario_receita=seq_cenario_receita, ano=ano)
        .all()
    )


def create_ajuste_receita(ajuste: CenarioReceitaAjuste) -> CenarioReceitaAjuste:
    """Cria um ajuste de receita."""
    db.session.add(ajuste)
    return ajuste


def delete_ajustes_receita_by_cenario_ano(seq_cenario_receita: int, ano: int):
    """Remove todos os ajustes de receita para um ano específico."""
    CenarioReceitaAjuste.query.filter_by(
        seq_cenario_receita=seq_cenario_receita,
        ano=ano
    ).delete()
    db.session.commit()


# ==================== CenarioDespesa ====================

def get_cenario_despesa_by_simulador(seq_simulador_cenario: int) -> Optional[CenarioDespesa]:
    """Busca configuração de despesa por ID do simulador."""
    return CenarioDespesa.query.filter_by(seq_simulador_cenario=seq_simulador_cenario).first()


def create_cenario_despesa(cenario_despesa: CenarioDespesa) -> CenarioDespesa:
    """Cria configuração de despesa."""
    db.session.add(cenario_despesa)
    db.session.commit()
    return cenario_despesa


def update_cenario_despesa(cenario_despesa: CenarioDespesa) -> CenarioDespesa:
    """Atualiza configuração de despesa."""
    db.session.commit()
    return cenario_despesa


# ==================== CenarioDespesaAjuste ====================

def get_ajustes_despesa_by_cenario(seq_cenario_despesa: int) -> List[CenarioDespesaAjuste]:
    """Retorna todos os ajustes de um cenário de despesa."""
    return CenarioDespesaAjuste.query.filter_by(seq_cenario_despesa=seq_cenario_despesa).all()


def get_ajustes_despesa_by_cenario_and_year(seq_cenario_despesa: int, ano: int) -> List[CenarioDespesaAjuste]:
    """Retorna ajustes de despesa por ano."""
    return (
        CenarioDespesaAjuste.query
        .filter_by(seq_cenario_despesa=seq_cenario_despesa, ano=ano)
        .all()
    )


def create_ajuste_despesa(ajuste: CenarioDespesaAjuste) -> CenarioDespesaAjuste:
    """Cria um ajuste de despesa."""
    db.session.add(ajuste)
    return ajuste


def delete_ajustes_despesa_by_cenario_ano(seq_cenario_despesa: int, ano: int):
    """Remove todos os ajustes de despesa para um ano específico."""
    CenarioDespesaAjuste.query.filter_by(
        seq_cenario_despesa=seq_cenario_despesa,
        ano=ano
    ).delete()
    db.session.commit()


# ==================== ModeloEconomicoParametro ====================

def get_parametros_by_cenario_receita(seq_cenario_receita: int) -> List[ModeloEconomicoParametro]:
    """Retorna parâmetros econômicos de um cenário de receita."""
    return ModeloEconomicoParametro.query.filter_by(seq_cenario_receita=seq_cenario_receita).all()


def create_parametro_economico(parametro: ModeloEconomicoParametro) -> ModeloEconomicoParametro:
    """Cria um parâmetro econômico."""
    db.session.add(parametro)
    return parametro


def delete_parametros_by_cenario_receita(seq_cenario_receita: int):
    """Remove todos os parâmetros de um cenário de receita."""
    ModeloEconomicoParametro.query.filter_by(seq_cenario_receita=seq_cenario_receita).delete()
    db.session.commit()


# ==================== Commit ====================

def commit():
    """Commit manual para operações em lote."""
    db.session.commit()
