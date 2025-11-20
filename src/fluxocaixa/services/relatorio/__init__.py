"""Relatorio services - modular organization.

This package contains modularized services for different types of reports,
replacing the monolithic relatorio_service.py.
"""
from .resumo_service import get_resumo_data
from .indicadores_service import get_indicadores_data
from .comparativo_service import get_analise_comparativa_data
from .saldos_service import get_saldos_diarios_data
from .dfc_service import get_dfc_data, get_dfc_eventos
from .years_service import get_available_years

__all__ = [
    'get_resumo_data',
    'get_indicadores_data',
    'get_analise_comparativa_data',
    'get_saldos_diarios_data',
    'get_dfc_data',
    'get_dfc_eventos',
    'get_available_years',
]
