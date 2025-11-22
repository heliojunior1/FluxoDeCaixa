"""Comparative analysis service."""
from datetime import date
import calendar

from ...repositories.lancamento_repository import LancamentoRepository
from ...repositories.pagamento_repository import PagamentoRepository
from ...repositories.tipo_lancamento_repository import TipoLancamentoRepository
from ...utils.constants import MONTH_NAME_PT


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
    meses_nomes = MONTH_NAME_PT
    data = {}
    totals = {str(m): {str(ano1): 0, str(ano2): 0} for m in meses_selecionados}
    totals["total"] = {str(ano1): 0, str(ano2): 0}

    if tipo_analise == "receitas":
        from ...models import Qualificador
        tipo_repo = TipoLancamentoRepository()
        lancamento_repo = LancamentoRepository()
        
        tipo_entrada = tipo_repo.get_by_descricao("Entrada")
        id_entrada = tipo_entrada.cod_tipo_lancamento if tipo_entrada else -1
        
        # Get all leaf qualifiers for revenues
        qualificadores = Qualificador.query.filter_by(ind_status='A').all()
        qualificadores_folha = [q for q in qualificadores if q.is_folha() and q.tipo_fluxo == 'receita']
        
        # Get all qualificador IDs
        qualificador_ids = [q.seq_qualificador for q in qualificadores_folha]
        
        # Get comparative data by qualificador
        results = lancamento_repo.get_grouped_by_qualificador_year_month(
            qualificador_ids=qualificador_ids,
            anos=[ano1, ano2],
            meses=meses_selecionados
        )
        
        # Map seq_qualificador to description for display
        qualificador_map = {q.seq_qualificador: q.dsc_qualificador for q in qualificadores_folha}
        all_items = [q.dsc_qualificador for q in qualificadores_folha]
    else:
        pagamento_repo = PagamentoRepository()
        
        results = pagamento_repo.get_comparative_by_qualificador(
            anos=[ano1, ano2],
            meses=meses_selecionados
        )
        
        qualificadores = pagamento_repo.list_qualificadores()
        all_items = [q.dsc_qualificador for q in qualificadores if q.tipo_fluxo == 'despesa']

    for item_name in all_items:
        data[item_name] = {str(m): {str(ano1): 0, str(ano2): 0} for m in range(1, 13)}
        data[item_name]["total"] = {str(ano1): 0, str(ano2): 0}

    # Process results
    if tipo_analise == "receitas":
        # Results format: (seq_qualificador, ano, mes, cod_tipo_lancamento, total)
        for seq_qual, year, month, cod_tipo, total_val in results:
            item_name = qualificador_map.get(seq_qual)
            if item_name and item_name in data:
                data[item_name][str(month)][str(year)] = float(total_val or 0)
    else:
        # Results format for despesas: (item, year, month, total)
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
