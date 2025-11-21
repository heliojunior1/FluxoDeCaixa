"""Comparative analysis service."""
from datetime import date
import calendar

from ...repositories.lancamento_repository import LancamentoRepository
from ...repositories.pagamento_repository import PagamentoRepository
from ...repositories.tipo_lancamento_repository import TipoLancamentoRepository
from ...repositories.origem_lancamento_repository import OrigemLancamentoRepository


def get_analise_comparativa_data(
    ano1: int,
    ano2: int,
    meses_selecionados: list[int],
    tipo_analise: str
) -> dict:
    """Get comparative analysis data between two years.
    
    Args:
        ano1: First year to compare
        ano2: Second year to compare
        meses_selecionados: List of months to include (1-12)
        tipo_analise: 'receitas' or 'despesas'
    
    Returns:
        Dictionary with comparative data per item and totals
    """
    meses_nomes = {i: calendar.month_name[i].capitalize() for i in range(1, 13)}
    data = {}
    totals = {str(m): {str(ano1): 0, str(ano2): 0} for m in meses_selecionados}
    totals["total"] = {str(ano1): 0, str(ano2): 0}

    if tipo_analise == "receitas":
        tipo_repo = TipoLancamentoRepository()
        lancamento_repo = LancamentoRepository()
        origem_repo = OrigemLancamentoRepository()
        
        tipo_entrada = tipo_repo.get_by_descricao("Entrada")
        id_entrada = tipo_entrada.cod_tipo_lancamento if tipo_entrada else -1
        
        results = lancamento_repo.get_comparative_by_origem(
            cod_tipo=id_entrada,
            anos=[ano1, ano2],
            meses=meses_selecionados
        )
        
        all_items = [o.dsc_origem_lancamento for o in origem_repo.list_all()]
    else:
        pagamento_repo = PagamentoRepository()
        
        results = pagamento_repo.get_comparative_by_orgao(
            anos=[ano1, ano2],
            meses=meses_selecionados
        )
        
        all_items = [o.nom_orgao for o in pagamento_repo.list_orgaos()]

    for item_name in all_items:
        data[item_name] = {str(m): {str(ano1): 0, str(ano2): 0} for m in range(1, 13)}
        data[item_name]["total"] = {str(ano1): 0, str(ano2): 0}

    for item, year, month, total_val in results:
        if item in data:
            data[item][str(month)][str(year)] = float(total_val or 0)

    for item_name, item_data in data.items():
        total1 = sum(item_data[str(m)][str(ano1)] for m in meses_selecionados)
        total2 = sum(item_data[str(m)][str(ano2)] for m in meses_selecionados)
        data[item_name]["total"][str(ano1)] = total1
        data[item_name]["total"][str(ano2)] = total2
        totals["total"][str(ano1)] += total1
        totals["total"][str(ano2)] += total2
        for m in meses_selecionados:
            totals[str(m)][str(ano1)] += item_data[str(m)][str(ano1)]
            totals[str(m)][str(ano2)] += item_data[str(m)][str(ano2)]
            
    return {
        "data": data,
        "totals": totals,
        "meses_nomes": meses_nomes,
    }
