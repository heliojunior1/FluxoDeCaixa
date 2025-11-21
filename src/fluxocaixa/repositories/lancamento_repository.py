from __future__ import annotations

from datetime import date
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import func, or_, extract

from ..models import Lancamento, Qualificador
from ..models.base import db
from ..domain import LancamentoCreate


class LancamentoRepository:
    """Data access layer for Lancamento records."""

    def __init__(self, session: Session | None = None):
        self.session = session or db.session

    def list(
        self,
        start_date: date | None = None,
        end_date: date | None = None,
        descricao: str | None = None,
        tipo: int | None = None,
        qualificador_folha: int | None = None,
    ):
        query = (
            self.session.query(Lancamento)
            .options(
                joinedload(Lancamento.qualificador),
                joinedload(Lancamento.tipo),
                joinedload(Lancamento.origem)
            )
            .filter_by(ind_status='A')
        )

        if start_date and end_date:
            query = query.filter(Lancamento.dat_lancamento.between(start_date, end_date))

        if descricao:
            query = query.join(Qualificador).filter(Qualificador.dsc_qualificador.ilike(f"%{descricao}%"))

        if tipo:
            query = query.filter(Lancamento.cod_tipo_lancamento == tipo)

        if qualificador_folha:
            query = query.filter(Lancamento.seq_qualificador == qualificador_folha)

        return query.order_by(Lancamento.dat_lancamento.desc()).all()

    def get_total_by_tipo_and_period(
        self,
        cod_tipo: int,
        ano: int,
        meses: list[int] | None = None,
        start_date: date | None = None,
        end_date: date | None = None
    ) -> float:
        """Get total sum of lancamentos by tipo and period.
        
        Args:
            cod_tipo: Tipo lancamento code
            ano: Year
            meses: Optional list of months (1-12)
            start_date: Optional start date (overrides ano/meses)
            end_date: Optional end date (overrides ano/meses)
        
        Returns:
            Total sum (0 if no results)
        """
        query = self.session.query(func.sum(Lancamento.val_lancamento)).filter(
            Lancamento.cod_tipo_lancamento == cod_tipo,
            Lancamento.ind_status == 'A'
        )

        if start_date and end_date:
            query = query.filter(Lancamento.dat_lancamento.between(start_date, end_date))
        elif meses:
            conditions = []
            for mes in meses:
                conditions.append(
                    (extract("year", Lancamento.dat_lancamento) == ano) &
                    (extract("month", Lancamento.dat_lancamento) == mes)
                )
            query = query.filter(or_(*conditions))
        else:
            query = query.filter(extract("year", Lancamento.dat_lancamento) == ano)

        return float(query.scalar() or 0)

    def get_monthly_summary(
        self,
        ano: int,
        mes: int,
        cod_tipo: int | None = None
    ) -> float:
        """Get monthly sum for a specific month.
        
        Args:
            ano: Year
            mes: Month (1-12)
            cod_tipo: Optional tipo filter
        
        Returns:
            Monthly sum
        """
        query = self.session.query(func.sum(Lancamento.val_lancamento)).filter(
            extract("year", Lancamento.dat_lancamento) == ano,
            extract("month", Lancamento.dat_lancamento) == mes,
            Lancamento.ind_status == 'A'
        )
        
        if cod_tipo:
            query = query.filter(Lancamento.cod_tipo_lancamento == cod_tipo)
        
        return float(query.scalar() or 0)

    def get_lancamentos_by_qualificador_and_period(
        self,
        seq_qualificador: int,
        ano: int,
        mes: int | None = None,
        dia: int | None = None,
        include_children: bool = False,
        qualificador_ids: list[int] | None = None
    ):
        """Get lancamentos for a qualificador and period.
        
        Args:
            seq_qualificador: Qualificador ID
            ano: Year
            mes: Optional month
            dia: Optional day (requires mes)
            include_children: Include child qualificadores
            qualificador_ids: Pre-computed list of qualificador IDs (overrides seq_qualificador)
        
        Returns:
            List of Lancamento objects
        """
        if qualificador_ids:
            ids = qualificador_ids
        else:
            ids = [seq_qualificador]
        
        query = self.session.query(Lancamento).filter(
            Lancamento.seq_qualificador.in_(ids),
            Lancamento.ind_status == 'A',
            extract("year", Lancamento.dat_lancamento) == ano
        )
        
        if mes:
            query = query.filter(extract("month", Lancamento.dat_lancamento) == mes)
        
        if dia and mes:
            query = query.filter(extract("day", Lancamento.dat_lancamento) == dia)
        
        return query.order_by(Lancamento.dat_lancamento).all()

    def get_grouped_by_qualificador_and_period(
        self,
        ano: int,
        mes: int | None = None,
        groupby_column=None
    ):
        """Get lancamentos grouped by qualificador and time period.
        
        Args:
            ano: Year
            mes: Optional specific month
            groupby_column: SQLAlchemy extract expression for grouping (day/month)
        
        Returns:
            List of tuples (seq_qualificador, period_value, total)
        """
        if groupby_column is None:
            groupby_column = extract("month", Lancamento.dat_lancamento)
        
        query = self.session.query(
            Lancamento.seq_qualificador,
            groupby_column.label("col"),
            func.sum(Lancamento.val_lancamento).label("total"),
        ).filter(
            extract("year", Lancamento.dat_lancamento) == ano,
            Lancamento.ind_status == "A",
        )
        
        if mes:
            query = query.filter(extract("month", Lancamento.dat_lancamento) == mes)
        
        return query.group_by("seq_qualificador", "col").all()

    def get_sum_by_origem_and_period(
        self,
        cod_origem: int,
        cod_tipo: int,
        start_date: date,
        end_date: date
    ) -> float:
        """Get sum by origem and period.
        
        Args:
            cod_origem: Origin code
            cod_tipo: Tipo code
            start_date: Start date
            end_date: End date
        
        Returns:
            Sum value
        """
        result = self.session.query(func.sum(Lancamento.val_lancamento)).filter(
            Lancamento.dat_lancamento.between(start_date, end_date),
            Lancamento.cod_tipo_lancamento == cod_tipo,
            Lancamento.cod_origem_lancamento == cod_origem,
            Lancamento.ind_status == 'A'
        ).scalar()
        
        return float(result or 0)

    def get_available_years(self) -> list[int]:
        """Get list of years with lancamento data.
        
        Returns:
            List of years sorted descending
        """
        years = self.session.query(
            extract("year", Lancamento.dat_lancamento)
        ).distinct().all()
        
        return sorted([int(y[0]) for y in years if y[0]], reverse=True)

    def create(self, data: LancamentoCreate) -> Lancamento:
        lanc = Lancamento(
            dat_lancamento=data.dat_lancamento,
            seq_qualificador=data.seq_qualificador,
            val_lancamento=data.val_lancamento,
            cod_tipo_lancamento=data.cod_tipo_lancamento,
            cod_origem_lancamento=data.cod_origem_lancamento,
            ind_origem='M',
            cod_pessoa_inclusao=1,
            seq_conta=data.seq_conta,
        )
        self.session.add(lanc)
        self.session.commit()
        return lanc

    def get(self, ident: int) -> Lancamento:
        return self.session.query(Lancamento).get_or_404(ident)

    def update(self, ident: int, data: LancamentoCreate) -> Lancamento:
        lanc = self.get(ident)
        lanc.dat_lancamento = data.dat_lancamento
        lanc.seq_qualificador = data.seq_qualificador
        lanc.val_lancamento = data.val_lancamento
        lanc.cod_tipo_lancamento = data.cod_tipo_lancamento
        lanc.cod_origem_lancamento = data.cod_origem_lancamento
        lanc.seq_conta = data.seq_conta
        self.session.commit()
        return lanc

    def soft_delete(self, ident: int) -> None:
        lanc = self.get(ident)
        lanc.ind_status = 'I'
        self.session.commit()
