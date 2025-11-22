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

    def get_by_qualificadores_and_month_year(
        self,
        qualificador_ids: list[int],
        ano: int,
        mes: int
    ):
        """Get lancamentos for a list of qualificadores in a specific month/year.
        
        Args:
            qualificador_ids: List of qualificador IDs
            ano: Year
            mes: Month
            
        Returns:
            List of Lancamento objects
        """
        return (
            self.session.query(Lancamento)
            .filter(
                Lancamento.seq_qualificador.in_(qualificador_ids),
                Lancamento.ind_status == "A",
                extract("year", Lancamento.dat_lancamento) == ano,
                extract("month", Lancamento.dat_lancamento) == mes
            )
            .order_by(Lancamento.dat_lancamento)
            .all()
        )

    def get_grouped_by_qualificador_and_period(
        self,
        ano: int,
        mes: int | None = None,
        groupby_column=None,
        meses: list[int] | None = None
    ):
        """Get lancamentos grouped by qualificador and time period.
        
        Args:
            ano: Year
            mes: Optional specific month
            groupby_column: SQLAlchemy extract expression for grouping (day/month)
            meses: Optional list of months to filter
        
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
        elif meses:
            query = query.filter(extract("month", Lancamento.dat_lancamento).in_(meses))
        
        return query.group_by("seq_qualificador", "col").all()

    def get_stats_by_tipo(self, cod_tipo: int) -> tuple[int, float]:
        """Get count and total sum for a specific tipo lancamento.
        
        Args:
            cod_tipo: Tipo Lancamento code
            
        Returns:
            Tuple (count, total)
        """
        count = self.session.query(Lancamento).filter_by(
            cod_tipo_lancamento=cod_tipo
        ).count()
        
        total = self.session.query(func.sum(Lancamento.val_lancamento)).filter_by(
            cod_tipo_lancamento=cod_tipo
        ).scalar()
        
        return count, float(total or 0)

    def count_by_qualificador(self, seq_qualificador: int) -> int:
        """Count lancamentos for a specific qualificador.
        
        Args:
            seq_qualificador: Qualificador ID
            
        Returns:
            Count of lancamentos
        """
        return self.session.query(Lancamento).filter_by(
            seq_qualificador=seq_qualificador
        ).count()

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

    def get_sum_by_account_before_date(
        self,
        seq_conta: int,
        before_date: date
    ) -> float:
        """Get sum of lancamentos for an account before a specific date.
        
        Args:
            seq_conta: Account sequence
            before_date: Date to filter before
        
        Returns:
            Sum value
        """
        result = self.session.query(func.sum(Lancamento.val_lancamento)).filter(
            Lancamento.seq_conta == seq_conta,
            Lancamento.dat_lancamento < before_date,
            Lancamento.ind_status == "A",
        ).scalar()
        
        return float(result or 0)

    def get_sum_by_account_on_date_positive(
        self,
        seq_conta: int,
        on_date: date
    ) -> float:
        """Get sum of positive lancamentos for an account on a specific date.
        
        Args:
            seq_conta: Account sequence
            on_date: Specific date
        
        Returns:
            Sum of positive values
        """
        result = self.session.query(func.sum(Lancamento.val_lancamento)).filter(
            Lancamento.seq_conta == seq_conta,
            Lancamento.dat_lancamento == on_date,
            Lancamento.val_lancamento > 0,
            Lancamento.ind_status == "A",
        ).scalar()
        
        return float(result or 0)

    def get_sum_by_account_on_date_negative(
        self,
        seq_conta: int,
        on_date: date
    ) -> float:
        """Get sum of negative lancamentos for an account on a specific date.
        
        Args:
            seq_conta: Account sequence
            on_date: Specific date
        
        Returns:
            Sum of negative values (as absolute value)
        """
        result = self.session.query(func.sum(Lancamento.val_lancamento)).filter(
            Lancamento.seq_conta == seq_conta,
            Lancamento.dat_lancamento == on_date,
            Lancamento.val_lancamento < 0,
            Lancamento.ind_status == "A",
        ).scalar()
        
        return abs(float(result or 0))

    def get_daily_sums_in_period(
        self,
        start_date: date,
        end_date: date
    ) -> dict[date, float]:
        """Get daily sums of lancamentos in a period.
        
        Args:
            start_date: Start date
            end_date: End date
        
        Returns:
            Dictionary mapping date to sum
        """
        results = self.session.query(
            Lancamento.dat_lancamento,
            func.sum(Lancamento.val_lancamento)
            ).filter(
            Lancamento.ind_status == "A",
            Lancamento.dat_lancamento >= start_date,
            Lancamento.dat_lancamento <= end_date,
        ).group_by(Lancamento.dat_lancamento).all()
        
        return {d: float(val or 0) for d, val in results}

    def get_sum_before_date(self, before_date: date) -> float:
        """Get total sum of all lancamentos before a specific date.
        
        Args:
            before_date: Date to filter before
        
        Returns:
            Sum value
        """
        result = self.session.query(func.sum(Lancamento.val_lancamento)).filter(
            Lancamento.ind_status == "A",
            Lancamento.dat_lancamento < before_date,
        ).scalar()
        
        return float(result or 0)

    def get_comparative_by_origem(
        self,
        cod_tipo: int,
        anos: list[int],
        meses: list[int]
    ) -> list:
        """Get comparative data by origem lancamento.
        
        Args:
            cod_tipo: Tipo lancamento code
            anos: List of years to compare
            meses: List of months to include
        
        Returns:
            List of tuples (origem, year, month, total)
        """
        from ..models import OrigemLancamento
        
        results = self.session.query(
            OrigemLancamento.dsc_origem_lancamento,
            extract("year", Lancamento.dat_lancamento).label("year"),
            extract("month", Lancamento.dat_lancamento).label("month"),
            func.sum(Lancamento.val_lancamento).label("total"),
        ).join(OrigemLancamento).filter(
            Lancamento.cod_tipo_lancamento == cod_tipo,
            extract("year", Lancamento.dat_lancamento).in_(anos),
            extract("month", Lancamento.dat_lancamento).in_(meses),
        ).group_by("dsc_origem_lancamento", "year", "month").all()
        
        return results

    def get_grouped_by_qualificador_year_month(
        self,
        qualificador_ids: list[int],
        anos: list[int],
        meses: list[int]
    ) -> list:
        """Get lancamentos grouped by qualificador, year and month.
        
        Args:
            qualificador_ids: List of qualificador IDs
            anos: List of years to include
            meses: List of months to include
        
        Returns:
            List of rows with seq_qualificador, ano, mes, cod_tipo_lancamento, total
        """
        results = self.session.query(
            Lancamento.seq_qualificador,
            extract("year", Lancamento.dat_lancamento).label("ano"),
            extract("month", Lancamento.dat_lancamento).label("mes"),
            Lancamento.cod_tipo_lancamento,
            func.sum(Lancamento.val_lancamento).label("total"),
        ).filter(
            Lancamento.seq_qualificador.in_(qualificador_ids),
            extract("year", Lancamento.dat_lancamento).in_(anos),
            extract("month", Lancamento.dat_lancamento).in_(meses),
            Lancamento.ind_status == "A",
        ).group_by(
            Lancamento.seq_qualificador,
            "ano",
            "mes",
            Lancamento.cod_tipo_lancamento,
        ).all()
        
        return results

    def get_base_values_for_projection(
        self,
        ano: int,
        mes: int
    ) -> list:
        """Get base values from previous year for projection scenarios.
        
        Args:
            ano: Year to get base values for (will query ano-1)
            mes: Month to filter
        
        Returns:
            List of tuples (seq_qualificador, cod_tipo_lancamento, total)
        """
        results = self.session.query(
            Lancamento.seq_qualificador,
            Lancamento.cod_tipo_lancamento,
            func.sum(Lancamento.val_lancamento).label("total"),
        ).filter(
            extract("year", Lancamento.dat_lancamento) == ano - 1,
            extract("month", Lancamento.dat_lancamento) == mes,
            Lancamento.ind_status == "A",
        ).group_by(Lancamento.seq_qualificador, Lancamento.cod_tipo_lancamento).all()
        
        return results

    def get_base_values_by_month(
        self,
        ano: int,
        meses: list[int]
    ) -> list:
        """Get base values from previous year grouped by month for DFC projections.
        
        Args:
            ano: Year to get base values for (will query ano-1)
            meses: List of months to filter
        
        Returns:
            List of tuples (seq_qualificador, month, total)
        """
        results = self.session.query(
            Lancamento.seq_qualificador,
            extract("month", Lancamento.dat_lancamento).label("col"),
            func.sum(Lancamento.val_lancamento).label("total"),
        ).filter(
            extract("year", Lancamento.dat_lancamento) == ano - 1,
            extract("month", Lancamento.dat_lancamento).in_(meses),
            Lancamento.ind_status == "A",
        ).group_by("seq_qualificador", "col").all()
        
        return results

    def get_sum_by_qualificadores_and_month(
        self,
        qualificadores_ids: list[int],
        cod_tipo: int,
        ano: int,
        mes: int
    ) -> float:
        """Get sum of lancamentos for qualificadores in a specific month.
        
        Args:
            qualificadores_ids: List of qualificador IDs
            cod_tipo: Tipo lancamento code
            ano: Year
            mes: Month (1-12)
        
        Returns:
            Sum value
        """
        if not qualificadores_ids:
            return 0.0
        
        result = self.session.query(func.sum(Lancamento.val_lancamento)).filter(
            Lancamento.seq_qualificador.in_(qualificadores_ids),
            Lancamento.cod_tipo_lancamento == cod_tipo,
            extract('year', Lancamento.dat_lancamento) == ano,
            extract('month', Lancamento.dat_lancamento) == mes,
            Lancamento.ind_status == 'A'
        ).scalar()
        
        return float(result or 0)

    def get_sum_by_qualificadores_and_year(
        self,
        qualificadores_ids: list[int],
        cod_tipo: int,
        ano: int
    ) -> float:
        """Get sum of lancamentos for qualificadores in a full year.
        
        Args:
            qualificadores_ids: List of qualificador IDs
            cod_tipo: Tipo lancamento code
            ano: Year
        
        Returns:
            Sum value
        """
        if not qualificadores_ids:
            return 0.0
        
        result = self.session.query(func.sum(Lancamento.val_lancamento)).filter(
            Lancamento.seq_qualificador.in_(qualificadores_ids),
            Lancamento.cod_tipo_lancamento == cod_tipo,
            extract('year', Lancamento.dat_lancamento) == ano,
            Lancamento.ind_status == 'A'
        ).scalar()
        
        return float(result or 0)

    def get_sample(self, limit: int = 10) -> list[Lancamento]:
        """Get a sample of lancamentos.
        
        Args:
            limit: Number of records to return
            
        Returns:
            List of Lancamento objects
        """
        return self.session.query(Lancamento).limit(limit).all()

    def create(self, data: LancamentoCreate) -> Lancamento:
        lanc = Lancamento(
            dat_lancamento=data.dat_lancamento,
            seq_qualificador=data.seq_qualificador,
            val_lancamento=data.val_lancamento,
            cod_tipo_lancamento=data.cod_tipo_lancamento,
            cod_origem_lancamento=data.cod_origem_lancamento,
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
