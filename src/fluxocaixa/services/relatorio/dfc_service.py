"""DFC (Demonstração de Fluxo de Caixa) service - Cash Flow Statement."""
from datetime import date
import calendar
from sqlalchemy import func, extract

from ...models import db, Lancamento, CenarioAjusteMensal, Qualificador
from ...utils.constants import DAY_ABBR_PT, MONTH_ABBR_PT


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

    # Get actual lancamentos
    query_real = db.session.query(
        Lancamento.seq_qualificador,
        extractor.label("col"),
        func.sum(Lancamento.val_lancamento).label("total"),
    ).filter(
        extract("year", Lancamento.dat_lancamento) == ano_selecionado,
        Lancamento.ind_status == "A",
    )
    if periodo == "mes":
        query_real = query_real.filter(
            extract("month", Lancamento.dat_lancamento) == mes_selecionado
        )
    else:
        query_real = query_real.filter(
            extract("month", Lancamento.dat_lancamento).in_(meses_selecionados)
        )

    resultados_reais = query_real.group_by("seq_qualificador", "col").all()

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
            query_base = (
                db.session.query(
                    Lancamento.seq_qualificador,
                    extract("month", Lancamento.dat_lancamento).label("col"),
                    func.sum(Lancamento.val_lancamento).label("total"),
                )
                .filter(
                    extract("year", Lancamento.dat_lancamento) == ano_selecionado - 1,
                    extract("month", Lancamento.dat_lancamento).in_(proj_months),
                    Lancamento.ind_status == "A",
                )
                .group_by("seq_qualificador", "col")
            )
            for seq, col, total in query_base.all():
                valores_base.setdefault(seq, {})[int(col)] = float(total or 0)

            ajustes = CenarioAjusteMensal.query.filter_by(
                seq_cenario=cenario_selecionado_id, ano=ano_selecionado
            ).all()
            ajustes_cenario = {(a.mes, a.seq_qualificador): a for a in ajustes}

    # Build hierarchical tree from root qualificadores
    qualificadores_root = (
        Qualificador.query.filter_by(cod_qualificador_pai=None, ind_status="A")
        .order_by(Qualificador.num_qualificador)
        .all()
    )

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
    totals = [0] * len(col_range)

    def sum_leaf(node):
        """Sum values only from leaf nodes."""
        if not node["children"]:
            for i, v in enumerate(node["values"]):
                totals[i] += v
        else:
            for ch in node["children"]:
                sum_leaf(ch)

    for root in dfc_data:
        sum_leaf(root)

    # Build headers
    if periodo == "mes":
        headers = ["Nome"] + [
            f"{d:02d}/{DAY_ABBR_PT[date(ano_selecionado, mes_selecionado, d).weekday()]}"
            for d in col_range
        ]
    else:
        headers = ["Nome"] + [MONTH_ABBR_PT[m] for m in col_range]
        
    meses_nomes = {i: calendar.month_name[i].capitalize() for i in range(1, 13)}

    return {
        "headers": headers,
        "dre_data": dfc_data,
        "totals": totals,
        "meses_projetados": list(sorted(proj_months)),
        "meses_nomes": meses_nomes,
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
    qual = Qualificador.query.get(seq)
    ids = (
        [seq] + [f.seq_qualificador for f in qual.get_todos_filhos()] if qual else [seq]
    )

    if periodo == "mes":
        ano, mes = [int(x) for x in mes_ano.split("-")]
        query = (
            Lancamento.query.filter(
                Lancamento.seq_qualificador.in_(ids), Lancamento.ind_status == "A"
            )
            .filter(extract("year", Lancamento.dat_lancamento) == ano)
            .filter(extract("month", Lancamento.dat_lancamento) == mes)
            .filter(extract("day", Lancamento.dat_lancamento) == col)
        )
        registros = query.order_by(Lancamento.dat_lancamento).all()
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
                base = (
                    db.session.query(func.sum(Lancamento.val_lancamento))
                    .filter(
                        Lancamento.seq_qualificador == qid,
                        extract("year", Lancamento.dat_lancamento) == ano - 1,
                        extract("month", Lancamento.dat_lancamento) == col,
                        Lancamento.ind_status == "A",
                    )
                    .scalar()
                    or 0
                )
                base = float(base)
                ajuste = (
                    CenarioAjusteMensal.query.filter_by(
                        seq_cenario=int(cenario_id),
                        seq_qualificador=qid,
                        ano=ano,
                        mes=col,
                    ).first()
                    if cenario_id
                    else None
                )
                valor = base
                if ajuste:
                    ajuste_val = float(ajuste.val_ajuste)
                    if ajuste.cod_tipo_ajuste == "P":
                        valor = base * (1 + ajuste_val / 100)
                    elif ajuste.cod_tipo_ajuste == "V":
                        valor = base + ajuste_val
                if valor != 0:
                    qobj = Qualificador.query.get(qid)
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
            query = (
                Lancamento.query.filter(
                    Lancamento.seq_qualificador.in_(ids), Lancamento.ind_status == "A"
                )
                .filter(extract("year", Lancamento.dat_lancamento) == ano)
                .filter(extract("month", Lancamento.dat_lancamento) == col)
            )
            registros = query.order_by(Lancamento.dat_lancamento).all()
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
