"""Common utilities and base classes for relatorio services."""
from datetime import date
from sqlalchemy import extract, or_
from ...repositories.tipo_lancamento_repository import TipoLancamentoRepository


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
    repo = TipoLancamentoRepository()
    tipo_entrada = repo.get_by_descricao("Entrada")
    tipo_saida = repo.get_by_descricao("Saída")
    
    return {
        'entrada': tipo_entrada.cod_tipo_lancamento if tipo_entrada else -1,
        'saida': tipo_saida.cod_tipo_lancamento if tipo_saida else -1,
    }
