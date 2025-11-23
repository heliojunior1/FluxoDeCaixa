"""DFC (Demonstração de Fluxo de Caixa) service - Cash Flow Statement."""
from datetime import date, timedelta
import calendar
from sqlalchemy import extract

from ...models import Lancamento, Qualificador
from ...repositories.lancamento_repository import LancamentoRepository
from ...repositories.saldo_conta_repository import SaldoContaRepository
from ...repositories import cenario_repository, qualificador_repository
from ...utils.constants import DAY_ABBR_PT, MONTH_ABBR_PT, MONTH_NAME_PT


def get_dfc_data(
    periodo: str,
    ano_selecionado: int,
    mes_selecionado: int | None,
    meses_selecionados: list[int],
    estrategia: str,
    cenario_selecionado_id: int | None
) -> dict:
    """Get DFC (Cash Flow Statement) data.
    
    Args:
        periodo: 'mes' or 'ano'
        ano_selecionado: Year to analyze
        mes_selecionado: Month if periodo='mes' (1-12)
        meses_selecionados: List of months if periodo='ano'
        estrategia: 'realizado' or 'projetado'
        cenario_selecionado_id: Scenario ID if strategy is 'projetado'
    
    Returns:
        Dictionary with DFC hierarchical data and totals
    """
    hoje = date.today()
    
    if periodo == "mes":
        col_range = range(
            1, calendar.monthrange(ano_selecionado, mes_selecionado)[1] + 1
        )
        extractor = extract("day", Lancamento.dat_lancamento)
    else:
        col_range = range(1, 13)
        extractor = extract("month", Lancamento.dat_lancamento)

    # Initialize repositories
    lancamento_repo = LancamentoRepository()
    saldo_repo = SaldoContaRepository()
    
    # Get initial bank balance from day before period
    if periodo == "mes":
        data_inicial = date(ano_selecionado, mes_selecionado, 1)
    else:
        primeiro_mes = min(col_range)
        data_inicial = date(ano_selecionado, primeiro_mes, 1)
    
    data_saldo_anterior = data_inicial - timedelta(days=1)
    saldo_banco_inicial = saldo_repo.get_saldo_total_by_date(data_saldo_anterior)
    if saldo_banco_inicial == 0:
        saldo_banco_inicial = saldo_repo.get_latest_saldo_total_before_date(data_saldo_anterior)

    # Get actual lancamentos using repository
    if periodo == "mes":
        resultados_reais = lancamento_repo.get_grouped_by_qualificador_and_period(
            ano=ano_selecionado,
            mes=mes_selecionado,
            groupby_column=extract("day", Lancamento.dat_lancamento)
        )
    else:
        # Get results with month grouping, filtered by selected months
        resultados_reais = lancamento_repo.get_grouped_by_qualificador_and_period(
            ano=ano_selecionado,
            meses=meses_selecionados,
            groupby_column=extractor
        )

    valores_reais = {}
    for seq, col, total in resultados_reais:
        valores_reais.setdefault(seq, {})[int(col)] = float(total or 0)

    # Get base values and adjustments for projection mode
    valores_base = {}
    ajustes_cenario = {}
    proj_months = set()
    if periodo == "ano" and estrategia == "projetado" and cenario_selecionado_id:
        proj_months = {
            m
            for m in meses_selecionados
            if ano_selecionado > hoje.year
            or (ano_selecionado == hoje.year and m >= hoje.month)
        }
        if proj_months:
            query_base = lancamento_repo.get_base_values_by_month(
                ano=ano_selecionado,
                meses=list(proj_months)
            )
            
            for seq, col, total in query_base:
                valores_base.setdefault(seq, {})[int(col)] = float(total or 0)

            ajustes = cenario_repository.get_ajustes_by_cenario_and_year(
                cenario_id=cenario_selecionado_id,
                ano=ano_selecionado
            )
            ajustes_cenario = {(a.mes, a.seq_qualificador): a for a in ajustes}

    # Build hierarchical tree from root qualificadores
    qualificadores_root = qualificador_repository.get_root_qualificadores()

    def build_node(q: Qualificador) -> dict:
        """Recursively build DFC node with values and children."""
        vals = []
        proj_flags = []
        for c in col_range:
            if c in proj_months:
                base = valores_base.get(q.seq_qualificador, {}).get(c, 0)
                ajuste = ajustes_cenario.get((c, q.seq_qualificador))
                if ajuste:
                    if ajuste.cod_tipo_ajuste == "P":
                        base *= 1 + float(ajuste.val_ajuste) / 100
                    elif ajuste.cod_tipo_ajuste == "V":
                        base += float(ajuste.val_ajuste)
                vals.append(base)
                proj_flags.append(True)
            else:
                vals.append(valores_reais.get(q.seq_qualificador, {}).get(c, 0))
                proj_flags.append(False)

        children = [build_node(f) for f in q.filhos if f.ind_status == "A"]
        for child in children:
            vals = [v + cv for v, cv in zip(vals, child["values"])]
            proj_flags = [p or cp for p, cp in zip(proj_flags, child["proj"])]

        return {
            "id": q.seq_qualificador,
            "name": q.dsc_qualificador,
            "number": q.num_qualificador,
            "level": q.nivel,
            "values": vals,
            "proj": proj_flags,
            "children": children,
        }

    dfc_data = [build_node(r) for r in qualificadores_root]

    # Calculate totals from leaf nodes
    # Calculate totals based on root nodes 1 (Receita) and 2 (Despesa)
    totals = [0] * len(col_range)
    
    receita_node = next((n for n in dfc_data if str(n["number"]) == "1"), None)
    despesa_node = next((n for n in dfc_data if str(n["number"]) == "2"), None)
    
    if receita_node and despesa_node:
        for i in range(len(col_range)):
            # Sum values: Receita (positive) + Despesa (negative)
            totals[i] = receita_node["values"][i] + despesa_node["values"][i]

    # Build headers
    if periodo == "mes":
        headers = ["Nome"] + [
            f"{d:02d}/{DAY_ABBR_PT[date(ano_selecionado, mes_selecionado, d).weekday()]}"
            for d in col_range
        ]
    else:
        headers = ["Nome"] + [MONTH_ABBR_PT[m] for m in col_range]
        
    meses_nomes = MONTH_NAME_PT
    
    # Calculate accumulated bank balances for each column
    saldos_banco_anterior = []  # Saldo at start of each day/month
    saldos_banco_final = []      # Saldo at end of each day/month
    resultado_dia = []           # Net result (receitas - despesas)
    
    saldo_acumulado = saldo_banco_inicial
    for total_col in totals:
        saldos_banco_anterior.append(saldo_acumulado)
        resultado_dia.append(total_col)
        saldo_acumulado += total_col
        saldos_banco_final.append(saldo_acumulado)

    return {
        "headers": headers,
        "dre_data": dfc_data,
        "totals": totals,
        "meses_projetados": list(sorted(proj_months)),
        "meses_nomes": meses_nomes,
        "saldos_banco_anterior": saldos_banco_anterior,
        "saldos_banco_final": saldos_banco_final,
        "resultado_dia": resultado_dia,
    }


def get_dfc_eventos(
    seq: int,
    periodo: str,
    col: int,
    mes_ano: str,
    estrategia: str,
    cenario_id: int | None
) -> dict:
    """Get detailed events (lancamentos) for a specific DFC cell.
    
    Args:
        seq: Qualificador sequence ID
        periodo: 'mes' or 'ano'
        col: Column number (day or month)
        mes_ano: Date string format "YYYY-MM" or "YYYY"
        estrategia: 'realizado' or 'projetado'
        cenario_id: Scenario ID for projections
    
    Returns:
        Dictionary with detailed events list and total
    """
    qual = qualificador_repository.get_qualificador_by_id(seq)
    ids = (
        [seq] + [f.seq_qualificador for f in qual.get_todos_filhos()] if qual else [seq]
    )
    
    # Initialize repository
    lancamento_repo = LancamentoRepository()

    if periodo == "mes":
        ano, mes = [int(x) for x in mes_ano.split("-")]
        registros = lancamento_repo.get_lancamentos_by_qualificador_and_period(
            seq_qualificador=seq,
            ano=ano,
            mes=mes,
            dia=col,
            qualificador_ids=ids
        )
        
        eventos = [
            {
                "data": r.dat_lancamento.strftime("%d/%m/%Y"),
                "descricao": f"{r.qualificador.num_qualificador} - {r.qualificador.dsc_qualificador}",
                "valor": float(r.val_lancamento),
                "tipo": r.tipo.dsc_tipo_lancamento,
                "origem": r.origem.dsc_origem_lancamento,
            }
            for r in registros
        ]
    else:
        ano = int(mes_ano)
        hoje = date.today()
        projetar = (
            estrategia == "projetado"
            and cenario_id
            and (ano > hoje.year or (ano == hoje.year and col >= hoje.month))
        )
        if projetar:
            eventos = []
            for qid in ids:
                # Get the specific value by qualificador
                rows = lancamento_repo.get_grouped_by_qualificador_year_month(
                    qualificador_ids=[qid],
                    anos=[ano - 1],
                    meses=[col]
                )
                base = sum(r.total for r in rows) if rows else 0
                base = float(base)
                
                ajuste = cenario_repository.get_ajuste_by_unique_keys(
                    cenario_id=int(cenario_id),
                    qualificador_id=qid,
                    ano=ano,
                    mes=col
                )
                
                valor = base
                if ajuste:
                    ajuste_val = float(ajuste.val_ajuste)
                    if ajuste.cod_tipo_ajuste == "P":
                        valor = base * (1 + ajuste_val / 100)
                    elif ajuste.cod_tipo_ajuste == "V":
                        valor = base + ajuste_val
                if valor != 0:
                    qobj = qualificador_repository.get_qualificador_by_id(qid)
                    eventos.append(
                        {
                            "data": f"{col:02d}/{ano}",
                            "descricao": f"{qobj.num_qualificador} - {qobj.dsc_qualificador}",
                            "valor": float(valor),
                            "tipo": "Projetado",
                            "origem": "Cenário",
                        }
                    )
        else:
            registros = lancamento_repo.get_by_qualificadores_and_month_year(
                qualificador_ids=ids,
                ano=ano,
                mes=col
            )
            eventos = [
                {
                    "data": r.dat_lancamento.strftime("%d/%m/%Y"),
                    "descricao": f"{r.qualificador.num_qualificador} - {r.qualificador.dsc_qualificador}",
                    "valor": float(r.val_lancamento),
                    "tipo": r.tipo.dsc_tipo_lancamento,
                    "origem": r.origem.dsc_origem_lancamento,
                }
                for r in registros
            ]

    total = sum(e["valor"] for e in eventos)
    return {"eventos": eventos, "total": total}
