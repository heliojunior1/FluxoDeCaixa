from datetime import date

from ..repositories.lancamento_repository import LancamentoRepository
from ..repositories.tipo_lancamento_repository import TipoLancamentoRepository
from ..repositories import cenario_repository, qualificador_repository
from ..services.simulador_cenario_service import get_versao_inicial_cenario, get_versao_final_cenario
from ..utils import format_currency
from ..utils.constants import MONTH_ABBR_PT


def get_previsao_realizado_data(
    ano: int,
    cenario_id: int | None,
    meses: list[int],
    qualificadores_ids: list[int]
) -> dict:
    if not meses:
        meses = list(range(1, 13))

    tipo_repo = TipoLancamentoRepository()
    tipo_entrada = tipo_repo.get_by_descricao("Entrada")
    tipo_saida = tipo_repo.get_by_descricao("Saída")
    cod_entrada = tipo_entrada.cod_tipo_lancamento if tipo_entrada else None
    cod_saida = tipo_saida.cod_tipo_lancamento if tipo_saida else None

    qs = qualificador_repository.get_qualificadores_by_ids(qualificadores_ids)
    qual_tipo_map = {
        q.seq_qualificador: (cod_saida if q.tipo_fluxo == "despesa" else cod_entrada)
        for q in qs
    }

    anos_range = [ano - 2, ano - 1, ano]
    anos_base = {a - 1 for a in anos_range}
    anos_needed = set(anos_range) | anos_base
    
    lancamento_repo = LancamentoRepository()
    lanc_rows = lancamento_repo.get_grouped_by_qualificador_year_month(
        qualificador_ids=qualificadores_ids,
        anos=list(anos_needed),
        meses=list(range(1, 13))
    )
    
    lanc_map = {
        (
            row.seq_qualificador,
            int(row.ano),
            int(row.mes),
            row.cod_tipo_lancamento,
        ): float(row.total or 0)
        for row in lanc_rows
    }

    def lanc_val(q_id, ano_ref, mes, cod_tipo):
        return lanc_map.get((q_id, ano_ref, mes, cod_tipo), 0.0)

    # Obter versões inicial e final do cenário usando o novo sistema de histórico
    versao_inicial = None
    versao_final = None
    
    if cenario_id:
        versao_inicial = get_versao_inicial_cenario(cenario_id, ano)
        versao_final = get_versao_final_cenario(cenario_id, ano)
    
    def get_ajustes_from_versao(versao, tipo='receita'):
        """Extrai ajustes de uma versão do cenário."""
        if not versao:
            return {}
        
        ajustes_list = versao.get(tipo, {}).get('ajustes', [])
        ajustes_map = {}
        
        for ajuste in ajustes_list:
            key = (
                ajuste['seq_qualificador'],
                ajuste['ano'],
                ajuste['mes']
            )
            ajustes_map[key] = {
                'cod_tipo_ajuste': ajuste['cod_tipo_ajuste'],
                'val_ajuste': ajuste['val_ajuste']
            }
        
        return ajustes_map
    
    # Criar mapas de ajustes para versão inicial e final
    ajustes_ini_receita = get_ajustes_from_versao(versao_inicial, 'receita')
    ajustes_ini_despesa = get_ajustes_from_versao(versao_inicial, 'despesa')
    ajustes_fin_receita = get_ajustes_from_versao(versao_final, 'receita')
    ajustes_fin_despesa = get_ajustes_from_versao(versao_final, 'despesa')

    def previsao_val_for_year(ajustes_map, q_id, mes, ano_ref):
        base = lanc_val(q_id, ano_ref - 1, mes, qual_tipo_map.get(q_id, cod_entrada))
        
        ajuste = ajustes_map.get((q_id, ano_ref, mes))
        if ajuste:
            if ajuste['cod_tipo_ajuste'] == "P":
                return base * (1 + float(ajuste['val_ajuste']) / 100)
            return base + float(ajuste['val_ajuste'])
        return base

    def real_val(q_id, ano_ref, meses_ref):
        cod_tipo = qual_tipo_map.get(q_id)
        return sum(lanc_val(q_id, ano_ref, m, cod_tipo) for m in meses_ref)

    tabela = []
    total_prev_ini = total_prev_fin = total_real = 0
    
    # Determinar qual mapa de ajustes usar baseado no tipo de qualificador
    for q in qs:
        # Selecionar mapa de ajustes correto (receita ou despesa)
        ajustes_ini = ajustes_ini_despesa if q.tipo_fluxo == "despesa" else ajustes_ini_receita
        ajustes_fin = ajustes_fin_despesa if q.tipo_fluxo == "despesa" else ajustes_fin_receita
        
        prev_ini = sum(
            previsao_val_for_year(ajustes_ini, q.seq_qualificador, m, ano)
            for m in meses
        )
        prev_fin = sum(
            previsao_val_for_year(ajustes_fin, q.seq_qualificador, m, ano)
            for m in meses
        )
        real = real_val(q.seq_qualificador, ano, meses)
        tabela.append(
            {
                "descricao": q.dsc_qualificador,
                "previsao_inicial": format_currency(prev_ini),
                "previsao_final": format_currency(prev_fin),
                "realizado": format_currency(real),
            }
        )
        total_prev_ini += prev_ini
        total_prev_fin += prev_fin
        total_real += real

    if len(tabela) > 1:
        tabela.append(
            {
                "descricao": "Total",
                "previsao_inicial": format_currency(total_prev_ini),
                "previsao_final": format_currency(total_prev_fin),
                "realizado": format_currency(total_real),
            }
        )

    labels = [MONTH_ABBR_PT[m] for m in meses]
    previsao_series = []
    realizado_series = []
    for m in meses:
        prev_total = 0
        for q_id in qualificadores_ids:
            q = next((qual for qual in qs if qual.seq_qualificador == q_id), None)
            if q:
                ajustes_fin = ajustes_fin_despesa if q.tipo_fluxo == "despesa" else ajustes_fin_receita
                prev_total += previsao_val_for_year(ajustes_fin, q_id, m, ano)
        
        real_total = sum(
            real_val(q_id, ano, [m]) for q_id in qualificadores_ids
        )
        previsao_series.append(round(prev_total / 1_000_000_000, 3))
        realizado_series.append(round(real_total / 1_000_000_000, 3))

    diff_final = []
    diff_inicial = []
    for a in anos_range:
        inicial_sum = 0
        final_sum = 0
        
        for q in qs:
            ajustes_ini = ajustes_ini_despesa if q.tipo_fluxo == "despesa" else ajustes_ini_receita
            ajustes_fin = ajustes_fin_despesa if q.tipo_fluxo == "despesa" else ajustes_fin_receita
            
            for m in range(1, 13):
                inicial_sum += previsao_val_for_year(ajustes_ini, q.seq_qualificador, m, a)
                final_sum += previsao_val_for_year(ajustes_fin, q.seq_qualificador, m, a)
        
        real_year = sum(
            real_val(q_id, a, list(range(1, 13))) for q_id in qualificadores_ids
        )
        diff_final.append(round((real_year - final_sum) / 1_000_000_000, 3))
        diff_inicial.append(round((real_year - inicial_sum) / 1_000_000_000, 3))

    return {
        "tabela": tabela,
        "evolucao": {
            "labels": labels,
            "previsao": previsao_series,
            "realizado": realizado_series,
        },
        "diferenca": {
            "labels": anos_range,
            "final": diff_final,
            "inicial": diff_inicial,
        },
    }
