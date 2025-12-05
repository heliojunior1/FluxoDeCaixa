"""Unit and integration tests for Lancamentos functionality.

Tests cover:
- Lancamento CRUD operations
- Filtering and pagination
- Import functionality
- Repository methods
"""
import pytest
from datetime import date, timedelta


class TestLancamentoServiceUnit:
    """Unit tests for lancamento_service."""

    def test_list_lancamentos_empty_filters(self, client):
        """Should list lancamentos without filters."""
        from fluxocaixa.services.lancamento_service import list_lancamentos

        lancamentos, total = list_lancamentos()

        assert isinstance(lancamentos, list)
        assert isinstance(total, int)
        assert total >= 0

    def test_list_lancamentos_with_date_filter(self, client):
        """Should filter by date range."""
        from fluxocaixa.services.lancamento_service import list_lancamentos

        start = date(2024, 1, 1)
        end = date(2024, 12, 31)

        lancamentos, total = list_lancamentos(start_date=start, end_date=end)

        assert isinstance(lancamentos, list)
        # All returned lancamentos should be within date range
        for lanc in lancamentos:
            assert start <= lanc.dat_lancamento <= end

    def test_list_lancamentos_with_tipo_filter(self, client):
        """Should filter by tipo lancamento."""
        from fluxocaixa.services.lancamento_service import list_lancamentos

        lancamentos, total = list_lancamentos(tipo=1)  # Assuming 1 = Entrada

        # All should have the same tipo
        for lanc in lancamentos:
            assert lanc.cod_tipo_lancamento == 1

    def test_list_lancamentos_pagination(self, client):
        """Should paginate results correctly."""
        from fluxocaixa.services.lancamento_service import list_lancamentos

        page1, total = list_lancamentos(page=1, per_page=5)
        page2, _ = list_lancamentos(page=2, per_page=5)

        assert len(page1) <= 5
        assert len(page2) <= 5
        # Pages should have different items (if total > 5)
        if total > 5:
            page1_ids = [l.seq_lancamento for l in page1]
            page2_ids = [l.seq_lancamento for l in page2]
            assert not set(page1_ids) & set(page2_ids)

    def test_list_lancamentos_sorting(self, client):
        """Should sort results correctly."""
        from fluxocaixa.services.lancamento_service import list_lancamentos

        asc, _ = list_lancamentos(sort_by='dat_lancamento', sort_order='asc', per_page=100)
        desc, _ = list_lancamentos(sort_by='dat_lancamento', sort_order='desc', per_page=100)

        if len(asc) > 1:
            # ASC: first date <= last date
            assert asc[0].dat_lancamento <= asc[-1].dat_lancamento
        if len(desc) > 1:
            # DESC: first date >= last date
            assert desc[0].dat_lancamento >= desc[-1].dat_lancamento

    def test_list_tipos_lancamento(self, client):
        """Should list all tipos de lancamento."""
        from fluxocaixa.services.lancamento_service import list_tipos_lancamento

        tipos = list_tipos_lancamento()

        assert isinstance(tipos, list)
        assert len(tipos) >= 2  # At least Entrada and Saída

    def test_list_origens_lancamento(self, client):
        """Should list all origens de lancamento."""
        from fluxocaixa.services.lancamento_service import list_origens_lancamento

        origens = list_origens_lancamento()

        assert isinstance(origens, list)
        assert len(origens) >= 1

    def test_list_contas_bancarias(self, client):
        """Should list active bank accounts."""
        from fluxocaixa.services.lancamento_service import list_contas_bancarias

        contas = list_contas_bancarias()

        assert isinstance(contas, list)


class TestLancamentoIntegration:
    """Integration tests for lancamento web routes."""

    def test_lancamentos_page_loads(self, client):
        """Should load lancamentos page."""
        response = client.get('/saldos')
        assert response.status_code == 200

    def test_filter_by_tipo(self, client):
        """Should filter lancamentos by tipo via form."""
        response = client.post('/saldos', data={
            'tipo': '1',
            'start_date': '',
            'end_date': '',
        })
        assert response.status_code == 200

    def test_add_lancamento_page(self, client):
        """Should render add lancamento modal."""
        response = client.get('/saldos')
        assert response.status_code == 200
        # Page should have form/button for adding

    def test_create_lancamento(self, client):
        """Should create a new lancamento."""
        from fluxocaixa.services.qualificador_service import list_active_qualificadores
        
        qualificadores = list_active_qualificadores()
        if qualificadores:
            response = client.post('/saldos/add', data={
                'dat_lancamento': '2025-01-15',
                'seq_qualificador': str(qualificadores[0].seq_qualificador),
                'val_lancamento': '1000.00',
                'cod_tipo_lancamento': '1',
                'cod_origem_lancamento': '1',
                'seq_conta': '',
            })
            # Should redirect after creation
            assert response.status_code in (200, 303, 302)


class TestLancamentoRepository:
    """Tests for LancamentoRepository methods."""

    def test_get_total_by_tipo_and_period(self, client):
        """Should calculate totals by tipo and period."""
        from fluxocaixa.repositories import LancamentoRepository

        repo = LancamentoRepository()
        total = repo.get_total_by_tipo_and_period(
            cod_tipo=1,
            ano=2024,
            meses=[1, 2, 3]
        )

        assert isinstance(total, float)
        assert total >= 0

    def test_get_monthly_summary(self, client):
        """Should get monthly summary."""
        from fluxocaixa.repositories import LancamentoRepository

        repo = LancamentoRepository()
        summary = repo.get_monthly_summary(ano=2024, mes=1)

        assert isinstance(summary, float)

    def test_get_available_years(self, client):
        """Should get list of years with data."""
        from fluxocaixa.repositories import LancamentoRepository

        repo = LancamentoRepository()
        years = repo.get_available_years()

        assert isinstance(years, list)
        assert all(isinstance(y, int) for y in years)
        assert years == sorted(years, reverse=True)  # Should be descending

    def test_count_by_qualificador(self, client):
        """Should count lancamentos by qualificador."""
        from fluxocaixa.repositories import LancamentoRepository

        repo = LancamentoRepository()
        count = repo.count_by_qualificador(seq_qualificador=1)

        assert isinstance(count, int)
        assert count >= 0

    def test_get_daily_sums_in_period(self, client):
        """Should get daily sums."""
        from fluxocaixa.repositories import LancamentoRepository

        repo = LancamentoRepository()
        start = date(2024, 1, 1)
        end = date(2024, 1, 31)
        
        sums = repo.get_daily_sums_in_period(start, end)

        assert isinstance(sums, dict)


class TestLancamentoEdgeCases:
    """Edge case tests for lancamentos."""

    def test_empty_date_range(self, client):
        """Should handle future date range with no data."""
        from fluxocaixa.services.lancamento_service import list_lancamentos

        future_start = date(2030, 1, 1)
        future_end = date(2030, 12, 31)

        lancamentos, total = list_lancamentos(
            start_date=future_start,
            end_date=future_end
        )

        assert lancamentos == []
        assert total == 0

    def test_invalid_qualificador_filter(self, client):
        """Should handle non-existent qualificador filter."""
        from fluxocaixa.services.lancamento_service import list_lancamentos

        lancamentos, total = list_lancamentos(qualificador_folha=999999)

        assert lancamentos == []
        assert total == 0

    def test_very_large_page_number(self, client):
        """Should handle page beyond data."""
        from fluxocaixa.services.lancamento_service import list_lancamentos

        lancamentos, total = list_lancamentos(page=9999, per_page=10)

        assert lancamentos == []
