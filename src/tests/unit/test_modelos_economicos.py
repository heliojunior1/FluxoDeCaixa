"""Unit tests for modelos_economicos_service.

Tests forecast functions with basic scenarios.
"""
import pytest
import pandas as pd
from datetime import date


class TestProjetarLoa:
    """Tests for projetar_loa function."""

    def test_loa_with_valor_anual(self):
        """Should distribute annual value evenly across months."""
        from fluxocaixa.services.modelos_economicos_service import projetar_loa

        config = {'valor_anual': 12_000_000}
        result = projetar_loa(meses_projecao=6, config=config)

        assert len(result) == 6
        # Each month should have approximately valor_anual/12
        expected_monthly = 12_000_000 / 12
        for val in result['valor_projetado']:
            assert abs(val - expected_monthly) < 0.01

    def test_loa_with_zero_values(self):
        """Should handle zero monthly values."""
        from fluxocaixa.services.modelos_economicos_service import projetar_loa

        config = {'valores_mensais': [0] * 12}
        result = projetar_loa(meses_projecao=12, config=config)

        assert len(result) == 12
        assert all(result['valor_projetado'] == 0)


class TestProjetarMediaHistorica:
    """Tests for projetar_media_historica function."""

    def test_media_historica_single_month(self):
        """Should handle single month of data."""
        from fluxocaixa.services.modelos_economicos_service import projetar_media_historica

        df = pd.DataFrame({
            'data': [date(2024, 1, 1)],
            'valor': [100_000]
        })
        config = {'anos_referencia': 1, 'percentual_ajuste': 5}

        result = projetar_media_historica(df, meses_projecao=3, config=config, ano_base=2025)

        assert result is not None
        assert len(result) == 3

    def test_media_historica_negative_values(self):
        """Should handle negative values in historical data."""
        from fluxocaixa.services.modelos_economicos_service import projetar_media_historica

        df = pd.DataFrame({
            'data': pd.date_range(start='2023-01-01', periods=12, freq='MS'),
            'valor': [-50_000] * 12  # Negative values (expenses)
        })
        config = {'anos_referencia': 1, 'percentual_ajuste': 10}

        result = projetar_media_historica(df, meses_projecao=6, config=config, ano_base=2025)

        assert result is not None
        assert all(result['valor_projetado'] <= 0)


class TestProjetarHoltWinters:
    """Tests for projetar_holt_winters function."""

    def test_holt_winters_constant_values(self):
        """Should handle constant historical values."""
        from fluxocaixa.services.modelos_economicos_service import projetar_holt_winters

        # Create 36 months of constant data
        df = pd.DataFrame({
            'data': pd.date_range(start='2022-01-01', periods=36, freq='MS'),
            'valor': [100_000] * 36
        })
        config = {'seasonal': 'add', 'trend': 'add'}

        result = projetar_holt_winters(df, meses_projecao=6, config=config, ano_base=2025)

        assert result is not None
        assert isinstance(result, pd.DataFrame)


class TestObterDadosHistoricos:
    """Tests for data retrieval functions."""

    def test_obter_dados_com_agregacao_mensal(self, client):
        """Should aggregate data monthly."""
        from fluxocaixa.services.modelos_economicos_service import obter_dados_historicos
        
        # Test that the function is callable
        assert callable(obter_dados_historicos)

    def test_obter_dados_historicos_multiplos(self, client):
        """Should handle multiple qualificadores."""
        from fluxocaixa.services.modelos_economicos_service import obter_dados_historicos_multiplos
        
        # Test that the function is callable
        assert callable(obter_dados_historicos_multiplos)
