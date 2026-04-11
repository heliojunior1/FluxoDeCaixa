"""Repository for Fórmulas Parametrizáveis."""

from typing import List, Optional

from ..models import db
from ..models.formula import RubricaFormula, ParametroGlobal, CenarioParametroValor


# ==================== RubricaFormula ====================

def get_all_formulas() -> List[RubricaFormula]:
    """Retorna todas as fórmulas ativas."""
    return (
        RubricaFormula.query
        .filter_by(ind_status='A')
        .order_by(RubricaFormula.nom_formula)
        .all()
    )


def get_formula_by_id(seq_rubrica_formula: int) -> Optional[RubricaFormula]:
    """Busca fórmula por ID."""
    return RubricaFormula.query.get(seq_rubrica_formula)


def get_formula_by_qualificador(seq_qualificador: int) -> Optional[RubricaFormula]:
    """Busca fórmula pelo qualificador associado."""
    return (
        RubricaFormula.query
        .filter_by(seq_qualificador=seq_qualificador, ind_status='A')
        .first()
    )


def get_formulas_by_qualificadores(seq_qualificadores: List[int]) -> List[RubricaFormula]:
    """Busca fórmulas para uma lista de qualificadores."""
    return (
        RubricaFormula.query
        .filter(
            RubricaFormula.seq_qualificador.in_(seq_qualificadores),
            RubricaFormula.ind_status == 'A',
        )
        .all()
    )


def create_formula(formula: RubricaFormula) -> RubricaFormula:
    """Cria nova fórmula."""
    db.session.add(formula)
    db.session.commit()
    return formula


def update_formula(formula: RubricaFormula) -> RubricaFormula:
    """Atualiza fórmula (commit)."""
    db.session.commit()
    return formula


def delete_formula(seq_rubrica_formula: int) -> Optional[RubricaFormula]:
    """Inativa logicamente uma fórmula."""
    formula = get_formula_by_id(seq_rubrica_formula)
    if formula:
        formula.ind_status = 'I'
        db.session.commit()
    return formula


# ==================== ParametroGlobal ====================

def get_all_parametros_globais() -> List[ParametroGlobal]:
    """Retorna todos os parâmetros globais ativos."""
    return (
        ParametroGlobal.query
        .filter_by(ind_status='A')
        .order_by(ParametroGlobal.nom_parametro)
        .all()
    )


def get_parametro_global_by_id(seq_parametro_global: int) -> Optional[ParametroGlobal]:
    """Busca parâmetro global por ID."""
    return ParametroGlobal.query.get(seq_parametro_global)


def get_parametro_global_by_nome(nom_parametro: str) -> Optional[ParametroGlobal]:
    """Busca parâmetro global pelo nome."""
    return (
        ParametroGlobal.query
        .filter_by(nom_parametro=nom_parametro, ind_status='A')
        .first()
    )


def create_parametro_global(parametro: ParametroGlobal) -> ParametroGlobal:
    """Cria novo parâmetro global."""
    db.session.add(parametro)
    db.session.commit()
    return parametro


def update_parametro_global(parametro: ParametroGlobal) -> ParametroGlobal:
    """Atualiza parâmetro global (commit)."""
    db.session.commit()
    return parametro


def delete_parametro_global(seq_parametro_global: int) -> Optional[ParametroGlobal]:
    """Inativa logicamente um parâmetro global."""
    parametro = get_parametro_global_by_id(seq_parametro_global)
    if parametro:
        parametro.ind_status = 'I'
        db.session.commit()
    return parametro


# ==================== CenarioParametroValor ====================

def get_valores_cenario(seq_simulador_cenario: int) -> List[CenarioParametroValor]:
    """Retorna todos os valores de parâmetros de um cenário."""
    return (
        CenarioParametroValor.query
        .filter_by(seq_simulador_cenario=seq_simulador_cenario)
        .all()
    )


def get_valor_cenario(
    seq_simulador_cenario: int,
    nom_parametro: str,
) -> Optional[CenarioParametroValor]:
    """Busca o valor de um parâmetro específico num cenário."""
    return (
        CenarioParametroValor.query
        .filter_by(
            seq_simulador_cenario=seq_simulador_cenario,
            nom_parametro=nom_parametro,
        )
        .first()
    )


def set_valor_cenario(valor: CenarioParametroValor) -> CenarioParametroValor:
    """Cria ou atualiza o valor de um parâmetro num cenário."""
    existente = get_valor_cenario(
        valor.seq_simulador_cenario,
        valor.nom_parametro,
    )
    if existente:
        existente.val_parametro = valor.val_parametro
        db.session.commit()
        return existente
    else:
        db.session.add(valor)
        db.session.commit()
        return valor


def delete_valores_cenario(seq_simulador_cenario: int):
    """Remove todos os valores de parâmetros de um cenário."""
    CenarioParametroValor.query.filter_by(
        seq_simulador_cenario=seq_simulador_cenario,
    ).delete()
    db.session.commit()


def set_valores_cenario_batch(
    seq_simulador_cenario: int,
    parametros: dict,
):
    """Define valores de parâmetros em lote para um cenário.

    Args:
        seq_simulador_cenario: ID do cenário
        parametros: Dict {nom_parametro: val_parametro}
    """
    # Remover valores antigos
    CenarioParametroValor.query.filter_by(
        seq_simulador_cenario=seq_simulador_cenario,
    ).delete()

    # Criar novos
    for nom, val in parametros.items():
        valor = CenarioParametroValor(
            seq_simulador_cenario=seq_simulador_cenario,
            nom_parametro=nom,
            val_parametro=val,
        )
        db.session.add(valor)

    db.session.commit()


# ==================== Commit ====================

def commit():
    """Commit manual para operações em lote."""
    db.session.commit()
