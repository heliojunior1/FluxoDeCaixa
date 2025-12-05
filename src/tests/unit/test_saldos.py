"""Unit and integration tests for Saldos Bancários functionality.

Tests cover:
- Bank balance CRUD operations
- Daily balance calculations
- Import functionality
- Balance history
"""
import pytest
from datetime import date, timedelta


class TestSaldoContaServiceUnit:
    """Unit tests for saldo_conta_service."""

    def test_list_saldos_conta_empty_filters(self, client):
        """Should list saldos without filters."""
        from fluxocaixa.services.saldo_conta_service import list_saldos_conta

        saldos, total = list_saldos_conta()

        assert isinstance(saldos, list)
        assert isinstance(total, int)

    def test_list_saldos_with_conta_filter(self, client):
        """Should filter by specific account."""
        from fluxocaixa.services.saldo_conta_service import list_saldos_conta

        saldos, total = list_saldos_conta(seq_conta=1)

        # All should have the same conta
        for saldo in saldos:
            assert saldo.seq_conta == 1

    def test_list_saldos_with_date_range(self, client):
        """Should filter by date range."""
        from fluxocaixa.services.saldo_conta_service import list_saldos_conta

        start = date(2024, 1, 1)
        end = date(2024, 12, 31)

        saldos, total = list_saldos_conta(data_inicio=start, data_fim=end)

        for saldo in saldos:
            assert start <= saldo.dat_saldo <= end

    def test_list_saldos_pagination(self, client):
        """Should paginate correctly."""
        from fluxocaixa.services.saldo_conta_service import list_saldos_conta

        page1, total = list_saldos_conta(page=1, per_page=5)
        page2, _ = list_saldos_conta(page=2, per_page=5)

        assert len(page1) <= 5
        assert len(page2) <= 5

    def test_list_saldos_sorting(self, client):
        """Should sort correctly."""
        from fluxocaixa.services.saldo_conta_service import list_saldos_conta

        desc, _ = list_saldos_conta(sort_by='dat_saldo', sort_order='desc', per_page=100)

        if len(desc) > 1:
            assert desc[0].dat_saldo >= desc[-1].dat_saldo

    def test_get_saldo_conta_existing(self, client):
        """Should get existing saldo by ID."""
        from fluxocaixa.services.saldo_conta_service import list_saldos_conta, get_saldo_conta

        saldos, _ = list_saldos_conta(per_page=1)
        if saldos:
            saldo = get_saldo_conta(saldos[0].seq_saldo_conta)
            assert saldo is not None
            assert saldo.seq_saldo_conta == saldos[0].seq_saldo_conta

    def test_get_saldo_conta_nonexistent(self, client):
        """Should return None for non-existent saldo."""
        from fluxocaixa.services.saldo_conta_service import get_saldo_conta

        saldo = get_saldo_conta(999999)
        assert saldo is None


class TestSaldoContaRepository:
    """Tests for SaldoContaRepository methods."""

    def test_get_saldo_by_conta_and_date(self, client):
        """Should get balance for specific account and date."""
        from fluxocaixa.repositories import SaldoContaRepository

        repo = SaldoContaRepository()
        saldo = repo.get_saldo_by_conta_and_date(
            seq_conta=1,
            data=date.today()
        )

        # May be None if no balance for today
        assert saldo is None or hasattr(saldo, 'val_saldo')

    def test_get_latest_saldo_before_date(self, client):
        """Should get most recent balance before date."""
        from fluxocaixa.repositories import SaldoContaRepository

        repo = SaldoContaRepository()
        saldo = repo.get_latest_saldo_before_date(
            seq_conta=1,
            data=date.today()
        )

        assert saldo is None or hasattr(saldo, 'val_saldo')

    def test_get_saldo_total_by_date(self, client):
        """Should get total balance across all accounts."""
        from fluxocaixa.repositories import SaldoContaRepository

        repo = SaldoContaRepository()
        total = repo.get_saldo_total_by_date(date.today())

        assert isinstance(total, (int, float))

    def test_get_latest_saldo_total_before_date(self, client):
        """Should get latest total before date."""
        from fluxocaixa.repositories import SaldoContaRepository

        repo = SaldoContaRepository()
        total = repo.get_latest_saldo_total_before_date(date.today())

        assert isinstance(total, (int, float))


class TestSaldosBancariosIntegration:
    """Integration tests for saldos bancarios web routes."""

    def test_saldos_page_loads(self, client):
        """Should load saldos bancarios page."""
        response = client.get('/saldos-bancarios')
        assert response.status_code == 200

    def test_saldos_page_with_filters(self, client):
        """Should filter saldos via form."""
        response = client.post('/saldos-bancarios', data={
            'seq_conta': '',
            'data_inicio': '2024-01-01',
            'data_fim': '2024-12-31',
        })
        assert response.status_code == 200

    def test_download_template(self, client):
        """Should download import template."""
        response = client.get('/saldos-bancarios/template-xlsx')
        assert response.status_code == 200
        assert 'application' in response.headers.get('content-type', '')


class TestSaldosDiariosService:
    """Tests for the daily balance report service."""

    def test_get_saldos_diarios_data(self, client):
        """Should get daily balance data."""
        from fluxocaixa.services.relatorio.saldos_service import get_saldos_diarios_data

        result = get_saldos_diarios_data(date.today())

        assert 'rows' in result
        assert 'totais' in result
        assert 'evolucao_labels' in result
        assert 'evolucao_saldos' in result

    def test_saldos_diarios_structure(self, client):
        """Should have correct structure."""
        from fluxocaixa.services.relatorio.saldos_service import get_saldos_diarios_data

        result = get_saldos_diarios_data(date.today())

        # Check totais structure
        totais = result['totais']
        assert 'saldo_anterior' in totais
        assert 'entradas' in totais
        assert 'saidas' in totais
        assert 'saldo_final' in totais

    def test_saldos_30_day_evolution(self, client):
        """Should have 30 days of evolution data."""
        from fluxocaixa.services.relatorio.saldos_service import get_saldos_diarios_data

        result = get_saldos_diarios_data(date.today())

        assert len(result['evolucao_labels']) == 30
        assert len(result['evolucao_saldos']) == 30


class TestSaldosEdgeCases:
    """Edge case tests for saldos."""

    def test_saldos_future_date(self, client):
        """Should handle future date with no data."""
        from fluxocaixa.services.saldo_conta_service import list_saldos_conta

        future = date(2030, 1, 1)
        saldos, total = list_saldos_conta(data_inicio=future, data_fim=future)

        assert total == 0

    def test_saldos_very_old_date(self, client):
        """Should handle very old date."""
        from fluxocaixa.services.relatorio.saldos_service import get_saldos_diarios_data

        old_date = date(2000, 1, 1)
        result = get_saldos_diarios_data(old_date)

        # Should still return valid structure
        assert 'rows' in result
        assert 'totais' in result

    def test_saldos_nonexistent_account(self, client):
        """Should handle non-existent account filter."""
        from fluxocaixa.services.saldo_conta_service import list_saldos_conta

        saldos, total = list_saldos_conta(seq_conta=999999)

        assert total == 0
        assert saldos == []