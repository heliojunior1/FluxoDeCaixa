"""Common utilities and base classes for relatorio services."""
from datetime import date
from sqlalchemy import extract, or_
from ...models import TipoLancamento


def criar_filtro_data_meses(ano_selecionado: int, meses_selecionados: list[int], query_table):
    """Create date filter conditions for multiple months.
    
    Args:
        ano_selecionado: Year to filter
        meses_selecionados: List of months (1-12)
        query_table: SQLAlchemy column to filter on (e.g., Lancamento.dat_lancamento)
    
    Returns:
        List of conditions that can be combined with or_()
    """
    conditions = []
    for mes in meses_selecionados:
        conditions.append(
            (extract("year", query_table) == ano_selecionado)
            & (extract("month", query_table) == mes)
        )
    return conditions


def get_tipo_lancamento_ids() -> dict[str, int]:
    """Get tipo_lancamento IDs for common types.
    
    Returns:
        Dictionary with 'entrada' and 'saida' keys mapping to their IDs
    """
    tipo_entrada = TipoLancamento.query.filter_by(dsc_tipo_lancamento="Entrada").first()
    tipo_saida = TipoLancamento.query.filter_by(dsc_tipo_lancamento="Saída").first()
    
    return {
        'entrada': tipo_entrada.cod_tipo_lancamento if tipo_entrada else -1,
        'saida': tipo_saida.cod_tipo_lancamento if tipo_saida else -1,
    }
