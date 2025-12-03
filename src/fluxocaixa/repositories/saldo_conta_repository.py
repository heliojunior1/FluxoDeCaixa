"""Repository for SaldoConta (Bank Account Balance) data access."""
from __future__ import annotations

from datetime import date
from sqlalchemy.orm import Session
from sqlalchemy import func, and_

from ..models import SaldoConta, ContaBancaria
from ..models.base import db


class SaldoContaRepository:
    """Data access layer for SaldoConta records."""
    
    def __init__(self, session: Session | None = None):
        self.session = session or db.session
    
    def get_saldo_by_conta_and_date(self, seq_conta: int, data: date) -> SaldoConta | None:
        """Get balance for a specific account on a specific date.
        
        Args:
            seq_conta: Account sequence ID
            data: Date to retrieve balance for
            
        Returns:
            SaldoConta object or None if not found
        """
        return self.session.query(SaldoConta).filter(
            and_(
                SaldoConta.seq_conta == seq_conta,
                SaldoConta.dat_saldo == data
            )
        ).first()
    
    def get_saldo_total_by_date(self, data: date) -> float:
        """Get sum of all active account balances on a specific date.
        
        Args:
            data: Date to retrieve balances for
            
        Returns:
            Sum of all account balances
        """
        result = self.session.query(
            func.coalesce(func.sum(SaldoConta.val_saldo), 0)
        ).join(
            ContaBancaria, SaldoConta.seq_conta == ContaBancaria.seq_conta
        ).filter(
            and_(
                SaldoConta.dat_saldo == data,
                ContaBancaria.ind_status == 'A'
            )
        ).scalar()
        
        return float(result or 0)
    
    def get_latest_saldo_before_date(self, seq_conta: int, data: date) -> SaldoConta | None:
        """Get the most recent balance before a specific date.
        
        Args:
            seq_conta: Account sequence ID
            data: Date to search before
            
        Returns:
            Most recent SaldoConta before the date, or None
        """
        return self.session.query(SaldoConta).filter(
            and_(
                SaldoConta.seq_conta == seq_conta,
                SaldoConta.dat_saldo < data
            )
        ).order_by(SaldoConta.dat_saldo.desc()).first()
    
    def get_latest_saldo_total_before_date(self, data: date) -> float:
        """Get sum of most recent balances for all active accounts before a date.
        
        For each account, gets the most recent balance before the specified date,
        then sums them all.
        
        Args:
            data: Date to search before
            
        Returns:
            Sum of most recent balances for all active accounts
        """
        contas = self.session.query(ContaBancaria).filter_by(ind_status='A').all()
        total = 0.0
        
        for conta in contas:
            saldo = self.get_latest_saldo_before_date(conta.seq_conta, data)
            if saldo:
                total += float(saldo.val_saldo)
        
        return total
    
    def get_saldos_periodo(
        self, 
        seq_conta: int, 
        data_inicio: date, 
        data_fim: date
    ) -> list[SaldoConta]:
        """Get all balances for an account within a date range.
        
        Args:
            seq_conta: Account sequence ID
            data_inicio: Start date (inclusive)
            data_fim: End date (inclusive)
            
        Returns:
            List of SaldoConta objects ordered by date
        """
        return self.session.query(SaldoConta).filter(
            and_(
                SaldoConta.seq_conta == seq_conta,
                SaldoConta.dat_saldo >= data_inicio,
                SaldoConta.dat_saldo <= data_fim
            )
        ).order_by(SaldoConta.dat_saldo).all()
    
    def exists(self, seq_conta: int, dat_saldo: date) -> bool:
        """Check if a balance record already exists for account and date.
        
        Args:
            seq_conta: Account sequence ID
            dat_saldo: Balance date
            
        Returns:
            True if record exists, False otherwise
        """
        return self.get_saldo_by_conta_and_date(seq_conta, dat_saldo) is not None

    def create(
        self, 
        seq_conta: int, 
        dat_saldo: date, 
        val_saldo: float, 
        cod_pessoa_inclusao: int
    ) -> tuple[SaldoConta | None, str | None]:
        """Create a new balance record.
        
        Args:
            seq_conta: Account sequence ID
            dat_saldo: Balance date
            val_saldo: Balance value
            cod_pessoa_inclusao: User ID who created the record
            
        Returns:
            Tuple of (Created SaldoConta object, error message)
            If successful: (SaldoConta, None)
            If error: (None, error_message)
        """
        # Check for duplicate
        if self.exists(seq_conta, dat_saldo):
            return None, f"Já existe um saldo cadastrado para esta conta na data {dat_saldo.strftime('%d/%m/%Y')}"
        
        try:
            saldo = SaldoConta(
                seq_conta=seq_conta,
                dat_saldo=dat_saldo,
                val_saldo=val_saldo,
                cod_pessoa_inclusao=cod_pessoa_inclusao
            )
            self.session.add(saldo)
            self.session.commit()
            return saldo, None
        except Exception as e:
            self.session.rollback()
            return None, f"Erro ao criar saldo: {str(e)}"
    
    def bulk_create(self, saldos_data: list[dict]) -> tuple[int, int, list[str]]:
        """Create multiple balance records in bulk, skipping duplicates.
        
        Args:
            saldos_data: List of dictionaries with keys: seq_conta, dat_saldo, 
                        val_saldo, cod_pessoa_inclusao
            
        Returns:
            Tuple of (created_count, skipped_count, errors)
        """
        created = 0
        skipped = 0
        errors = []
        
        for data in saldos_data:
            try:
                # Check if already exists
                if self.exists(data['seq_conta'], data['dat_saldo']):
                    skipped += 1
                    continue
                
                saldo = SaldoConta(**data)
                self.session.add(saldo)
                self.session.commit()
                created += 1
            except Exception as e:
                self.session.rollback()
                errors.append(f"Conta {data['seq_conta']} / Data {data['dat_saldo']}: {str(e)}")
        
        return created, skipped, errors
    
    def update(
        self, 
        seq_saldo_conta: int, 
        val_saldo: float, 
        cod_pessoa_alteracao: int
    ) -> SaldoConta | None:
        """Update an existing balance record.
        
        Args:
            seq_saldo_conta: Balance record ID
            val_saldo: New balance value
            cod_pessoa_alteracao: User ID who updated the record
            
        Returns:
            Updated SaldoConta object or None if not found
        """
        saldo = self.session.query(SaldoConta).get(seq_saldo_conta)
        if saldo:
            saldo.val_saldo = val_saldo
            saldo.dat_alteracao = date.today()
            saldo.cod_pessoa_alteracao = cod_pessoa_alteracao
            self.session.commit()
        return saldo
    
    def delete(self, seq_saldo_conta: int) -> bool:
        """Delete a balance record.
        
        Args:
            seq_saldo_conta: Balance record ID
            
        Returns:
            True if deleted, False if not found
        """
        saldo = self.session.query(SaldoConta).get(seq_saldo_conta)
        if saldo:
            self.session.delete(saldo)
            self.session.commit()
            return True
        return False
    
    def list(
        self,
        seq_conta: int | None = None,
        data_inicio: date | None = None,
        data_fim: date | None = None,
        page: int = 1,
        per_page: int = 50,
        sort_by: str = 'dat_saldo',
        sort_order: str = 'desc'
    ) -> tuple[list[SaldoConta], int]:
        """List balance records with optional filters and pagination.
        
        Args:
            seq_conta: Optional account filter
            data_inicio: Optional start date filter
            data_fim: Optional end date filter
            page: Page number (1-indexed)
            per_page: Items per page
            sort_by: Column to sort by
            sort_order: 'asc' or 'desc'
            
        Returns:
            Tuple of (List of SaldoConta objects, total count)
        """
        from sqlalchemy.orm import joinedload
        
        query = self.session.query(SaldoConta).options(
            joinedload(SaldoConta.conta)
        )
        
        if seq_conta is not None:
            query = query.filter(SaldoConta.seq_conta == seq_conta)
        
        if data_inicio is not None:
            query = query.filter(SaldoConta.dat_saldo >= data_inicio)
        
        if data_fim is not None:
            query = query.filter(SaldoConta.dat_saldo <= data_fim)
        
        # Dynamic sorting
        sort_column_map = {
            'dat_saldo': SaldoConta.dat_saldo,
            'val_saldo': SaldoConta.val_saldo,
            'seq_conta': SaldoConta.seq_conta,
        }
        sort_column = sort_column_map.get(sort_by, SaldoConta.dat_saldo)
        
        if sort_order == 'asc':
            query = query.order_by(sort_column.asc())
        else:
            query = query.order_by(sort_column.desc())
        
        # Get total count
        total_count = query.count()
        
        # Apply pagination
        offset = (page - 1) * per_page
        saldos = query.offset(offset).limit(per_page).all()
        
        return saldos, total_count
    
    def count(
        self,
        seq_conta: int | None = None,
        data_inicio: date | None = None,
        data_fim: date | None = None
    ) -> int:
        """Count balance records with optional filters.
        
        Args:
            seq_conta: Optional account filter
            data_inicio: Optional start date filter
            data_fim: Optional end date filter
            
        Returns:
            Count of matching records
        """
        query = self.session.query(func.count(SaldoConta.seq_saldo_conta))
        
        if seq_conta is not None:
            query = query.filter(SaldoConta.seq_conta == seq_conta)
        
        if data_inicio is not None:
            query = query.filter(SaldoConta.dat_saldo >= data_inicio)
        
        if data_fim is not None:
            query = query.filter(SaldoConta.dat_saldo <= data_fim)
        
        return query.scalar()
