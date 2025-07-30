import calendar
from datetime import date

from fastapi import Request
from . import router, templates
from sqlalchemy import func, extract, or_
from ..models import (
    db,
    TipoLancamento,
    OrigemLancamento,
    Pagamento,
    Lancamento,
    Orgao,
    Cenario,
    CenarioAjusteMensal,
)


@router.get('/relatorios')
async def relatorios(request: Request):
    return templates.TemplateResponse('relatorios.html', {'request': request})


@router.get('/relatorios/resumo')
@router.post('/relatorios/resumo')
async def relatorio_resumo(request: Request):
    lancamento_years = db.session.query(extract('year', Lancamento.dat_lancamento)).distinct().all()
    pagamento_years = db.session.query(extract('year', Pagamento.dat_pagamento)).distinct().all()
    anos_disponiveis = sorted({y[0] for y in lancamento_years + pagamento_years}, reverse=True)
    ano_default = anos_disponiveis[0] if anos_disponiveis else date.today().year
    form = await request.form() if request.method == 'POST' else {}
    ano_selecionado = int(form.get('ano', ano_default))
    estrategia = form.get('estrategia', 'realizado')
    cenario_id = form.get('cenario_id')
    cenarios_disponiveis = Cenario.query.filter_by(ind_status='A').all()
    cenario_selecionado_id = int(cenario_id) if cenario_id else None
    meses_selecionados_str = form.getlist('meses') if hasattr(form, 'getlist') else []
    meses_selecionados = list(range(1, 13)) if not meses_selecionados_str else [int(m) for m in meses_selecionados_str]
    meses_nomes = {i: calendar.month_name[i].capitalize() for i in range(1, 13)}
    tipo_entrada = TipoLancamento.query.filter_by(dsc_tipo_lancamento='Entrada').first()
    tipo_saida = TipoLancamento.query.filter_by(dsc_tipo_lancamento='Saída').first()
    id_entrada = tipo_entrada.cod_tipo_lancamento if tipo_entrada else -1
    id_saida = tipo_saida.cod_tipo_lancamento if tipo_saida else -1

    def criar_filtro_data(query_table):
        conditions = []
        for mes in meses_selecionados:
            conditions.append((extract('year', query_table) == ano_selecionado) & (extract('month', query_table) == mes))
        return conditions

    entradas_conditions = criar_filtro_data(Lancamento.dat_lancamento)
    total_entradas_periodo = 0
    if entradas_conditions:
        total_entradas_periodo = (
            db.session.query(func.sum(Lancamento.val_lancamento))
            .filter(Lancamento.cod_tipo_lancamento == id_entrada, or_(*entradas_conditions))
            .scalar()
            or 0
        )

    saidas_conditions = criar_filtro_data(Lancamento.dat_lancamento)
    total_saidas_lanc = 0
    if saidas_conditions:
        total_saidas_lanc = (
            db.session.query(func.sum(Lancamento.val_lancamento))
            .filter(Lancamento.cod_tipo_lancamento == id_saida, or_(*saidas_conditions))
            .scalar()
            or 0
        )
    total_saidas_periodo = abs(total_saidas_lanc)
    disponibilidade_periodo = total_entradas_periodo - total_saidas_periodo

    ajustes_cenario = {}
    if estrategia == 'projetado' and cenario_selecionado_id:
        ajustes = CenarioAjusteMensal.query.filter_by(
            seq_cenario=cenario_selecionado_id, ano=ano_selecionado
        ).all()
        ajustes_cenario = {
            (a.ano, a.mes, a.seq_qualificador): a
            for a in ajustes
        }

    cash_flow_data = {'labels': [], 'receitas': [], 'despesas': [], 'saldos': [], 'saldo_final': [], 'meses_projetados': []}
    saldo_acumulado = 0
    hoje = date.today()
    total_entradas_recalc = 0
    total_saidas_recalc = 0

    for mes in sorted(meses_selecionados):
        month_start = date(ano_selecionado, mes, 1)
        month_end = date(ano_selecionado, mes, calendar.monthrange(ano_selecionado, mes)[1])
        projetar_mes = (
            estrategia == 'projetado'
            and ajustes_cenario
            and (ano_selecionado > hoje.year or (ano_selecionado == hoje.year and mes >= hoje.month))
        )
        receitas_mes = 0
        despesas_mes = 0
        if projetar_mes:
            lancamentos_base = (
                db.session.query(
                    Lancamento.seq_qualificador,
                    Lancamento.cod_tipo_lancamento,
                    func.sum(Lancamento.val_lancamento).label('total'),
                )
                .filter(
                    extract('year', Lancamento.dat_lancamento) == ano_selecionado - 1,
                    extract('month', Lancamento.dat_lancamento) == mes,
                    Lancamento.ind_status == 'A',
                )
                .group_by(Lancamento.seq_qualificador, Lancamento.cod_tipo_lancamento)
                .all()
            )
            for seq_qualificador, cod_tipo_lancamento, total_base in lancamentos_base:
                total_base = float(total_base or 0)
                valor_ajustado = total_base
                key = (ano_selecionado, mes, seq_qualificador)
                if key in ajustes_cenario:
                    ajuste = ajustes_cenario[key]
                    if ajuste.cod_tipo_ajuste == 'P':
                        valor_ajustado = total_base * (1 + float(ajuste.val_ajuste) / 100)
                    elif ajuste.cod_tipo_ajuste == 'V':
                        valor_ajustado = total_base + float(ajuste.val_ajuste)
                if cod_tipo_lancamento == id_entrada:
                    receitas_mes += valor_ajustado
                elif cod_tipo_lancamento == id_saida:
                    despesas_mes += abs(valor_ajustado)
        else:
            receitas_mes = (
                db.session.query(func.sum(Lancamento.val_lancamento))
                .filter(
                    Lancamento.dat_lancamento.between(month_start, month_end),
                    Lancamento.cod_tipo_lancamento == id_entrada,
                    Lancamento.ind_status == 'A',
                )
                .scalar()
                or 0
            )
            despesas_lanc_mes = (
                db.session.query(func.sum(Lancamento.val_lancamento))
                .filter(
                    Lancamento.dat_lancamento.between(month_start, month_end),
                    Lancamento.cod_tipo_lancamento == id_saida,
                    Lancamento.ind_status == 'A',
                )
                .scalar()
                or 0
            )
            despesas_mes = abs(despesas_lanc_mes or 0)
        cash_flow_data['labels'].append(meses_nomes[mes][:3])
        cash_flow_data['receitas'].append(float(receitas_mes))
        cash_flow_data['despesas'].append(float(despesas_mes))
        cash_flow_data['meses_projetados'].append(projetar_mes)
        total_entradas_recalc += float(receitas_mes)
        total_saidas_recalc += float(despesas_mes)
        saldo_mes = float(receitas_mes) - float(despesas_mes)
        saldo_acumulado += saldo_mes
        cash_flow_data['saldos'].append(saldo_mes)
        cash_flow_data['saldo_final'].append(saldo_acumulado)

    if estrategia == 'projetado' and ajustes_cenario:
        total_entradas_periodo = total_entradas_recalc
        total_saidas_periodo = total_saidas_recalc
        disponibilidade_periodo = total_entradas_periodo - total_saidas_periodo

    return templates.TemplateResponse(
        'rel_resumo.html',
        {
            'request': request,
            'total_entradas_periodo': total_entradas_periodo,
            'total_saidas_periodo': total_saidas_periodo,
            'disponibilidade_periodo': disponibilidade_periodo,
            'cash_flow_data': cash_flow_data,
            'ano_selecionado': ano_selecionado,
            'anos_disponiveis': anos_disponiveis,
            'meses_selecionados': [str(m) for m in meses_selecionados],
            'meses_nomes': meses_nomes,
            'estrategia_selecionada': estrategia,
            'cenario_selecionado_id': cenario_selecionado_id,
            'cenarios_disponiveis': cenarios_disponiveis,
        },
    )


@router.get('/relatorios/indicadores')
@router.post('/relatorios/indicadores')
async def relatorio_indicadores(request: Request):
    lancamento_years = db.session.query(extract('year', Lancamento.dat_lancamento)).distinct().all()
    pagamento_years = db.session.query(extract('year', Pagamento.dat_pagamento)).distinct().all()
    anos_disponiveis = sorted({y[0] for y in lancamento_years + pagamento_years}, reverse=True)
    ano_default = anos_disponiveis[0] if anos_disponiveis else date.today().year
    form = await request.form() if request.method == 'POST' else {}
    ano_selecionado = int(form.get('ano', ano_default))
    tipo_selecionado = form.get('tipo', 'ambos')
    meses_selecionados_str = form.getlist('meses') if hasattr(form, 'getlist') else []
    meses_selecionados = list(range(1, 13)) if not meses_selecionados_str else [int(m) for m in meses_selecionados_str]
    meses_nomes = {i: calendar.month_name[i].capitalize() for i in range(1, 13)}
    tipo_entrada = TipoLancamento.query.filter_by(dsc_tipo_lancamento='Entrada').first()
    tipo_saida = TipoLancamento.query.filter_by(dsc_tipo_lancamento='Saída').first()
    id_entrada = tipo_entrada.cod_tipo_lancamento if tipo_entrada else -1
    id_saida = tipo_saida.cod_tipo_lancamento if tipo_saida else -1
    area_chart_data = {'labels': [], 'receitas': [], 'despesas': []}

    for mes in sorted(meses_selecionados):
        month_start = date(ano_selecionado, mes, 1)
        month_end = date(ano_selecionado + 1, 1, 1) if mes == 12 else date(ano_selecionado, mes + 1, 1)
        receitas_mes = (
            db.session.query(func.sum(Lancamento.val_lancamento))
            .filter(
                Lancamento.dat_lancamento.between(month_start, month_end),
                Lancamento.cod_tipo_lancamento == id_entrada,
            )
            .scalar()
            or 0
        )
        despesas_lanc_mes = (
            db.session.query(func.sum(Lancamento.val_lancamento))
            .filter(
                Lancamento.dat_lancamento.between(month_start, month_end),
                Lancamento.cod_tipo_lancamento == id_saida,
            )
            .scalar()
            or 0
        )
        despesas_mes = abs(despesas_lanc_mes or 0)
        area_chart_data['labels'].append(meses_nomes[mes][:3])
        area_chart_data['receitas'].append(float(receitas_mes))
        area_chart_data['despesas'].append(float(despesas_mes))

    pie_chart_data = {'labels': [], 'values': []}
    if tipo_selecionado in ('receita', 'ambos'):
        origens = OrigemLancamento.query.all()
        for origem in origens:
            total_origem = 0
            for mes in meses_selecionados:
                month_start = date(ano_selecionado, mes, 1)
                month_end = date(ano_selecionado + 1, 1, 1) if mes == 12 else date(ano_selecionado, mes + 1, 1)
                valor = (
                    db.session.query(func.sum(Lancamento.val_lancamento))
                    .filter(
                        Lancamento.dat_lancamento.between(month_start, month_end),
                        Lancamento.cod_tipo_lancamento == id_entrada,
                        Lancamento.cod_origem_lancamento == origem.cod_origem_lancamento,
                    )
                    .scalar()
                    or 0
                )
                total_origem += float(valor)
            if total_origem > 0:
                pie_chart_data['labels'].append(origem.dsc_origem_lancamento)
                pie_chart_data['values'].append(total_origem)
    elif tipo_selecionado == 'despesa':
        orgaos = Orgao.query.all()
        for orgao in orgaos:
            total_orgao = 0
            for mes in meses_selecionados:
                month_start = date(ano_selecionado, mes, 1)
                month_end = date(ano_selecionado + 1, 1, 1) if mes == 12 else date(ano_selecionado, mes + 1, 1)
                valor = (
                    db.session.query(func.sum(Pagamento.val_pagamento))
                    .filter(
                        Pagamento.dat_pagamento.between(month_start, month_end),
                        Pagamento.cod_orgao == orgao.cod_orgao,
                    )
                    .scalar()
                    or 0
                )
                total_orgao += float(valor)
            if total_orgao > 0:
                pie_chart_data['labels'].append(orgao.nom_orgao)
                pie_chart_data['values'].append(total_orgao)

    projection_chart_data = {'labels': [], 'saldo': []}
    saldo_acumulado = 0
    for mes in sorted(meses_selecionados):
        month_start = date(ano_selecionado, mes, 1)
        month_end = date(ano_selecionado + 1, 1, 1) if mes == 12 else date(ano_selecionado, mes + 1, 1)
        receitas_mes = (
            db.session.query(func.sum(Lancamento.val_lancamento))
            .filter(
                Lancamento.dat_lancamento.between(month_start, month_end),
                Lancamento.cod_tipo_lancamento == id_entrada,
            )
            .scalar()
            or 0
        )
        despesas_lanc_mes = (
            db.session.query(func.sum(Lancamento.val_lancamento))
            .filter(
                Lancamento.dat_lancamento.between(month_start, month_end),
                Lancamento.cod_tipo_lancamento == id_saida,
            )
            .scalar()
            or 0
        )
        despesas_mes = abs(despesas_lanc_mes or 0)
        saldo_mes = float(receitas_mes) - float(despesas_mes)
        saldo_acumulado += saldo_mes
        projection_chart_data['labels'].append(meses_nomes[mes][:3])
        projection_chart_data['saldo'].append(saldo_acumulado)

    return templates.TemplateResponse(
        'rel_indicadores.html',
        {
            'request': request,
            'area_chart_data': area_chart_data,
            'pie_chart_data': pie_chart_data,
            'projection_chart_data': projection_chart_data,
            'ano_selecionado': ano_selecionado,
            'anos_disponiveis': anos_disponiveis,
            'tipo_selecionado': tipo_selecionado,
            'meses_selecionados': [str(m) for m in meses_selecionados],
            'meses_nomes': meses_nomes,
        },
    )


@router.get('/relatorios/analise-comparativa')
@router.post('/relatorios/analise-comparativa')
async def relatorio_analise_comparativa(request: Request):
    form = await request.form() if request.method == 'POST' else {}
    tipo_analise = form.get('tipo_analise', 'receitas')
    lancamento_years = db.session.query(extract('year', Lancamento.dat_lancamento)).distinct().all()
    pagamento_years = db.session.query(extract('year', Pagamento.dat_pagamento)).distinct().all()
    anos_disponiveis = sorted({y[0] for y in lancamento_years + pagamento_years}, reverse=True)
    ano1_default = anos_disponiveis[1] if len(anos_disponiveis) > 1 else (date.today().year - 1)
    ano2_default = anos_disponiveis[0] if anos_disponiveis else date.today().year
    ano1 = int(form.get('ano1', ano1_default))
    ano2 = int(form.get('ano2', ano2_default))
    meses_selecionados_str = form.getlist('meses') if hasattr(form, 'getlist') else []
    meses_selecionados = list(range(1, 13)) if not meses_selecionados_str else [int(m) for m in meses_selecionados_str]
    meses_nomes = {i: calendar.month_name[i].capitalize() for i in range(1, 13)}
    data = {}
    totals = {str(m): {str(ano1): 0, str(ano2): 0} for m in meses_selecionados}
    totals['total'] = {str(ano1): 0, str(ano2): 0}

    if tipo_analise == 'receitas':
        tipo_entrada = TipoLancamento.query.filter_by(dsc_tipo_lancamento='Entrada').first()
        id_entrada = tipo_entrada.cod_tipo_lancamento if tipo_entrada else -1
        query = (
            db.session.query(
                OrigemLancamento.dsc_origem_lancamento,
                extract('year', Lancamento.dat_lancamento).label('year'),
                extract('month', Lancamento.dat_lancamento).label('month'),
                func.sum(Lancamento.val_lancamento).label('total'),
            )
            .join(OrigemLancamento)
            .filter(
                Lancamento.cod_tipo_lancamento == id_entrada,
                extract('year', Lancamento.dat_lancamento).in_([ano1, ano2]),
                extract('month', Lancamento.dat_lancamento).in_(meses_selecionados),
            )
            .group_by('dsc_origem_lancamento', 'year', 'month')
        )
        results = query.all()
        all_items = [item[0] for item in db.session.query(OrigemLancamento.dsc_origem_lancamento).distinct().all()]
    else:
        query = (
            db.session.query(
                Orgao.nom_orgao,
                extract('year', Pagamento.dat_pagamento).label('year'),
                extract('month', Pagamento.dat_pagamento).label('month'),
                func.sum(Pagamento.val_pagamento).label('total'),
            )
            .join(Orgao)
            .filter(
                extract('year', Pagamento.dat_pagamento).in_([ano1, ano2]),
                extract('month', Pagamento.dat_pagamento).in_(meses_selecionados),
            )
            .group_by('nom_orgao', 'year', 'month')
        )
        results = query.all()
        all_items = [item[0] for item in db.session.query(Orgao.nom_orgao).distinct().all()]

    for item_name in all_items:
        data[item_name] = {str(m): {str(ano1): 0, str(ano2): 0} for m in range(1, 13)}
        data[item_name]['total'] = {str(ano1): 0, str(ano2): 0}

    for item, year, month, total_val in results:
        if item in data:
            data[item][str(month)][str(year)] = float(total_val or 0)

    for item_name, item_data in data.items():
        total1 = sum(item_data[str(m)][str(ano1)] for m in meses_selecionados)
        total2 = sum(item_data[str(m)][str(ano2)] for m in meses_selecionados)
        data[item_name]['total'][str(ano1)] = total1
        data[item_name]['total'][str(ano2)] = total2
        totals['total'][str(ano1)] += total1
        totals['total'][str(ano2)] += total2
        for m in meses_selecionados:
            totals[str(m)][str(ano1)] += item_data[str(m)][str(ano1)]
            totals[str(m)][str(ano2)] += item_data[str(m)][str(ano2)]

    return templates.TemplateResponse(
        'rel_analise_comparativa.html',
        {
            'request': request,
            'data': data,
            'totals': totals,
            'tipo_analise': tipo_analise,
            'ano1': ano1,
            'ano2': ano2,
            'anos_disponiveis': anos_disponiveis,
            'meses_selecionados': [str(m) for m in meses_selecionados],
            'meses_nomes': meses_nomes,
        },
    )

@router.get('/relatorios/dre')
@router.post('/relatorios/dre')
async def relatorio_dre(request: Request):
    lancamento_years = db.session.query(extract('year', Lancamento.dat_lancamento)).distinct().all()
    pagamento_years = db.session.query(extract('year', Pagamento.dat_pagamento)).distinct().all()
    anos_disponiveis = sorted({y[0] for y in lancamento_years + pagamento_years}, reverse=True)

    form = await request.form() if request.method == 'POST' else {}
    periodo = form.get('periodo', 'mensal')
    mes_ano = form.get('mes_ano')
    estrategia = form.get('estrategia', 'realizado')
    cenario_id = form.get('cenario_id')
    meses_analise = int(form.get('meses_analise', 6))
    if not mes_ano:
        today = date.today()
        mes_ano = f"{today.year}-{today.month:02d}"

    cenarios = Cenario.query.filter_by(ind_status='A').all()
    cenario_id_int = int(cenario_id) if cenario_id else None

    year, month = map(int, mes_ano.split('-'))
    start_date = date(year, month, 1)

    def add_months(dt, months):
        y = dt.year + (dt.month - 1 + months) // 12
        m = (dt.month - 1 + months) % 12 + 1
        return date(y, m, 1)

    periodos = []
    current = start_date
    for i in range(meses_analise):
        label = f"{calendar.month_name[current.month][:3]}/{current.year}"
        end_day = calendar.monthrange(current.year, current.month)[1]
        periodos.append({
            'label': label,
            'start': current.isoformat(),
            'end': date(current.year, current.month, end_day).isoformat(),
        })
        current = add_months(current, 1)

    valores = {}
    for idx, p in enumerate(periodos):
        res = (
            db.session.query(
                Lancamento.seq_qualificador,
                func.sum(Lancamento.val_lancamento)
            )
            .filter(
                Lancamento.dat_lancamento.between(p['start'], p['end']),
                Lancamento.ind_status == 'A'
            )
            .group_by(Lancamento.seq_qualificador)
            .all()
        )
        for seq, total in res:
            valores[(seq, idx)] = float(total or 0)

    qualificadores = Qualificador.query.filter_by(ind_status='A').order_by(Qualificador.num_qualificador).all()
    qual_map = {q.seq_qualificador: q for q in qualificadores}
    roots = [q for q in qualificadores if q.cod_qualificador_pai is None]

    def calc_totais(q):
        totals = [valores.get((q.seq_qualificador, i), 0) for i in range(len(periodos))]
        for filho in q.filhos:
            if filho.ind_status == 'A':
                child_totals = calc_totais(filho)
                totals = [a + b for a, b in zip(totals, child_totals)]
        q._totals = totals
        return totals

    for r in roots:
        calc_totais(r)

    dre_data = []

    def build_rows(q, nivel=0, parent=None):
        row = {
            'id': q.seq_qualificador,
            'descricao': q.dsc_qualificador,
            'nivel': nivel,
            'parent': parent,
            'has_children': any(f.ind_status == 'A' for f in q.filhos),
            'values': list(zip(q._totals, periodos))
        }
        dre_data.append(row)
        for f in q.filhos:
            if f.ind_status == 'A':
                build_rows(f, nivel + 1, q.seq_qualificador)

    for r in roots:
        build_rows(r)

    return templates.TemplateResponse(
        'rel_dre.html',
        {
            'request': request,
            'periodos': periodos,
            'dre_data': dre_data,
            'periodo': periodo,
            'mes_ano': mes_ano,
            'estrategia': estrategia,
            'cenario_id': cenario_id_int,
            'cenarios': cenarios,
            'meses_analise': meses_analise,
            'anos_disponiveis': anos_disponiveis,
        },
    )


@router.get('/relatorios/dre/eventos')
async def relatorio_dre_eventos(qualificador_id: int, start: str, end: str):
    start_date = date.fromisoformat(start)
    end_date = date.fromisoformat(end)
    registros = (
        Lancamento.query
        .filter(
            Lancamento.seq_qualificador == qualificador_id,
            Lancamento.dat_lancamento.between(start_date, end_date),
            Lancamento.ind_status == 'A'
        ).all()
    )
    result = []
    for r in registros:
        result.append({
            'data': r.dat_lancamento.isoformat(),
            'valor': float(r.val_lancamento),
            'origem': r.origem.dsc_origem_lancamento if r.origem else '',
        })
    return result
