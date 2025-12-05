"""Repository for Simulador de Cenários functionality."""
from __future__ import annotations

from datetime import date
from typing import List, Optional
from sqlalchemy.orm import Session

from ..models import (
    SimuladorCenario,
    CenarioReceita,
    CenarioReceitaAjuste,
    CenarioDespesa,
    CenarioDespesaAjuste,
    ModeloEconomicoParametro,
)
from ..models.base import db


class SimuladorCenarioRepository:
    """Data access layer for Simulador de Cenários."""

    def __init__(self, session: Session | None = None):
        self.session = session or db.session

    # ==================== SimuladorCenario ====================

    def get_all(self) -> List[SimuladorCenario]:
        """Retorna todos os cenários simuladores."""
        return (
            self.session.query(SimuladorCenario)
            .order_by(SimuladorCenario.dat_criacao.desc())
            .all()
        )

    def get_active(self) -> List[SimuladorCenario]:
        """Retorna apenas cenários ativos."""
        return (
            self.session.query(SimuladorCenario)
            .filter_by(ind_status='A')
            .order_by(SimuladorCenario.dat_criacao.desc())
            .all()
        )

    def get_by_id(self, seq_simulador_cenario: int) -> Optional[SimuladorCenario]:
        """Busca um cenário simulador por ID."""
        return self.session.get(SimuladorCenario, seq_simulador_cenario)

    def create(self, simulador: SimuladorCenario) -> SimuladorCenario:
        """Cria um novo cenário simulador."""
        self.session.add(simulador)
        self.session.commit()
        return simulador

    def update(self, simulador: SimuladorCenario) -> SimuladorCenario:
        """Atualiza um cenário simulador existente."""
        self.session.commit()
        return simulador

    def delete_logical(self, seq_simulador_cenario: int, user_id: int = 1) -> Optional[SimuladorCenario]:
        """Inativa logicamente um cenário simulador."""
        simulador = self.get_by_id(seq_simulador_cenario)
        if simulador:
            simulador.ind_status = 'I'
            simulador.cod_pessoa_alteracao = user_id
            simulador.dat_alteracao = date.today()
            self.session.commit()
        return simulador

    # ==================== CenarioReceita ====================

    def get_cenario_receita(self, seq_simulador_cenario: int) -> Optional[CenarioReceita]:
        """Busca configuração de receita por ID do simulador."""
        return (
            self.session.query(CenarioReceita)
            .filter_by(seq_simulador_cenario=seq_simulador_cenario)
            .first()
        )

    def create_cenario_receita(self, cenario_receita: CenarioReceita) -> CenarioReceita:
        """Cria configuração de receita."""
        self.session.add(cenario_receita)
        self.session.commit()
        return cenario_receita

    def update_cenario_receita(self, cenario_receita: CenarioReceita) -> CenarioReceita:
        """Atualiza configuração de receita."""
        self.session.commit()
        return cenario_receita

    # ==================== CenarioReceitaAjuste ====================

    def get_ajustes_receita(self, seq_cenario_receita: int) -> List[CenarioReceitaAjuste]:
        """Retorna todos os ajustes de um cenário de receita."""
        return (
            self.session.query(CenarioReceitaAjuste)
            .filter_by(seq_cenario_receita=seq_cenario_receita)
            .all()
        )

    def get_ajustes_receita_by_year(self, seq_cenario_receita: int, ano: int) -> List[CenarioReceitaAjuste]:
        """Retorna ajustes de receita por ano."""
        return (
            self.session.query(CenarioReceitaAjuste)
            .filter_by(seq_cenario_receita=seq_cenario_receita, ano=ano)
            .all()
        )

    def create_ajuste_receita(self, ajuste: CenarioReceitaAjuste) -> CenarioReceitaAjuste:
        """Cria um ajuste de receita."""
        self.session.add(ajuste)
        return ajuste

    def delete_ajustes_receita_by_year(self, seq_cenario_receita: int, ano: int) -> None:
        """Remove todos os ajustes de receita para um ano específico."""
        self.session.query(CenarioReceitaAjuste).filter_by(
            seq_cenario_receita=seq_cenario_receita,
            ano=ano
        ).delete()
        self.session.commit()

    # ==================== CenarioDespesa ====================

    def get_cenario_despesa(self, seq_simulador_cenario: int) -> Optional[CenarioDespesa]:
        """Busca configuração de despesa por ID do simulador."""
        return (
            self.session.query(CenarioDespesa)
            .filter_by(seq_simulador_cenario=seq_simulador_cenario)
            .first()
        )

    def create_cenario_despesa(self, cenario_despesa: CenarioDespesa) -> CenarioDespesa:
        """Cria configuração de despesa."""
        self.session.add(cenario_despesa)
        self.session.commit()
        return cenario_despesa

    def update_cenario_despesa(self, cenario_despesa: CenarioDespesa) -> CenarioDespesa:
        """Atualiza configuração de despesa."""
        self.session.commit()
        return cenario_despesa

    # ==================== CenarioDespesaAjuste ====================

    def get_ajustes_despesa(self, seq_cenario_despesa: int) -> List[CenarioDespesaAjuste]:
        """Retorna todos os ajustes de um cenário de despesa."""
        return (
            self.session.query(CenarioDespesaAjuste)
            .filter_by(seq_cenario_despesa=seq_cenario_despesa)
            .all()
        )

    def get_ajustes_despesa_by_year(self, seq_cenario_despesa: int, ano: int) -> List[CenarioDespesaAjuste]:
        """Retorna ajustes de despesa por ano."""
        return (
            self.session.query(CenarioDespesaAjuste)
            .filter_by(seq_cenario_despesa=seq_cenario_despesa, ano=ano)
            .all()
        )

    def create_ajuste_despesa(self, ajuste: CenarioDespesaAjuste) -> CenarioDespesaAjuste:
        """Cria um ajuste de despesa."""
        self.session.add(ajuste)
        return ajuste

    def delete_ajustes_despesa_by_year(self, seq_cenario_despesa: int, ano: int) -> None:
        """Remove todos os ajustes de despesa para um ano específico."""
        self.session.query(CenarioDespesaAjuste).filter_by(
            seq_cenario_despesa=seq_cenario_despesa,
            ano=ano
        ).delete()
        self.session.commit()

    # ==================== ModeloEconomicoParametro ====================

    def get_parametros_economicos(self, seq_cenario_receita: int) -> List[ModeloEconomicoParametro]:
        """Retorna parâmetros econômicos de um cenário de receita."""
        return (
            self.session.query(ModeloEconomicoParametro)
            .filter_by(seq_cenario_receita=seq_cenario_receita)
            .all()
        )

    def create_parametro_economico(self, parametro: ModeloEconomicoParametro) -> ModeloEconomicoParametro:
        """Cria um parâmetro econômico."""
        self.session.add(parametro)
        return parametro

    def delete_parametros_by_cenario(self, seq_cenario_receita: int) -> None:
        """Remove todos os parâmetros de um cenário de receita."""
        self.session.query(ModeloEconomicoParametro).filter_by(
            seq_cenario_receita=seq_cenario_receita
        ).delete()
        self.session.commit()

    # ==================== Utility ====================

    def commit(self) -> None:
        """Commit manual para operações em lote."""
        self.session.commit()
