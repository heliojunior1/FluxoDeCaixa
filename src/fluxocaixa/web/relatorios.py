import calendar
from datetime import date

from fastapi import Request
from fastapi.responses import JSONResponse
from . import router, templates, handle_exceptions
from ..services import (
    get_available_years,
    get_resumo_data,
    get_indicadores_data,
    get_analise_comparativa_data,
    get_saldos_diarios_data,
    get_dfc_data,
    get_dfc_eventos,
    list_active_cenarios,
    list_active_qualificadores,
    get_previsao_receita_data,
    get_controle_despesa_data,
    get_ldo_orcamento_data,
)
from ..utils.constants import MONTH_NAME_PT


@router.get("/relatorios")
@handle_exceptions
async def relatorios(request: Request):
    return templates.TemplateResponse("relatorios.html", {"request": request})


@router.get("/relatorios/previsao-receita", name="relatorio_previsao_receita")
@handle_exceptions
async def relatorio_previsao_receita(request: Request):
    """Página do relatório de Previsão de Receita."""
    anos_disponiveis = get_available_years()
    ano_default = anos_disponiveis[0] if anos_disponiveis else date.today().year
    cenarios = list_active_cenarios()
    
    # Buscar apenas qualificadores de receita (folha + tipo receita)
    todos_qualificadores = list_active_qualificadores()
    qualificadores_receita = [
        q for q in todos_qualificadores 
        if q.is_folha() and q.tipo_fluxo == 'receita'
    ]
    
    return templates.TemplateResponse(
        "rel_previsao_receita.html",
        {
            "request": request,
            "anos_disponiveis": anos_disponiveis,
            "ano_default": ano_default,
            "cenarios": cenarios,
            "qualificadores": qualificadores_receita,
        }
    )


@router.get("/relatorios/previsao-receita/data", name="relatorio_previsao_receita_data")
@handle_exceptions
async def relatorio_previsao_receita_data(request: Request):
    """API JSON para dados do gráfico de Previsão de Receita."""
    params = request.query_params
    ano = int(params.get("ano", date.today().year))
    cenario_id = int(params.get("cenario")) if params.get("cenario") else None
    qualificadores_ids = [
        int(q) for q in params.get("qualificadores", "").split(",") if q
    ]
    meses = [int(m) for m in params.get("meses", "").split(",") if m] or None
    
    data = get_previsao_receita_data(ano, cenario_id, qualificadores_ids, meses)
    return JSONResponse(data)


@router.get("/relatorios/controle-despesa", name="relatorio_controle_despesa")
@handle_exceptions
async def relatorio_controle_despesa(request: Request):
    """Página do relatório de Controle de Despesa."""
    anos_disponiveis = get_available_years()
    ano_default = anos_disponiveis[0] if anos_disponiveis else date.today().year
    cenarios = list_active_cenarios()
    
    # Buscar apenas qualificadores de despesa (folha + tipo despesa)
    todos_qualificadores = list_active_qualificadores()
    qualificadores_despesa = [
        q for q in todos_qualificadores 
        if q.is_folha() and q.tipo_fluxo == 'despesa'
    ]
    
    return templates.TemplateResponse(
        "rel_controle_despesa.html",
        {
            "request": request,
            "anos_disponiveis": anos_disponiveis,
            "ano_default": ano_default,
            "cenarios": cenarios,
            "qualificadores": qualificadores_despesa,
        }
    )


@router.get("/relatorios/controle-despesa/data", name="relatorio_controle_despesa_data")
@handle_exceptions
async def relatorio_controle_despesa_data(request: Request):
    """API JSON para dados do gráfico de Controle de Despesa."""
    params = request.query_params
    ano = int(params.get("ano", date.today().year))
    cenario_id = int(params.get("cenario")) if params.get("cenario") else None
    qualificadores_ids = [
        int(q) for q in params.get("qualificadores", "").split(",") if q
    ]
    meses = [int(m) for m in params.get("meses", "").split(",") if m] or None
    
    data = get_controle_despesa_data(ano, cenario_id, qualificadores_ids, meses)
    return JSONResponse(data)


@router.get("/relatorios/ldo-orcamento", name="relatorio_ldo_orcamento")
@handle_exceptions
async def relatorio_ldo_orcamento(request: Request):
    """Página do relatório de LDO & Orçamento."""
    anos_disponiveis = get_available_years()
    ano_default = anos_disponiveis[0] if anos_disponiveis else date.today().year
    
    # Buscar todos os qualificadores folha
    todos_qualificadores = list_active_qualificadores()
    qualificadores_receita = [
        q for q in todos_qualificadores 
        if q.is_folha() and q.tipo_fluxo == 'receita'
    ]
    qualificadores_despesa = [
        q for q in todos_qualificadores 
        if q.is_folha() and q.tipo_fluxo == 'despesa'
    ]
    
    return templates.TemplateResponse(
        "rel_ldo_orcamento.html",
        {
            "request": request,
            "anos_disponiveis": anos_disponiveis,
            "ano_default": ano_default,
            "qualificadores_receita": qualificadores_receita,
            "qualificadores_despesa": qualificadores_despesa,
        }
    )


@router.get("/relatorios/ldo-orcamento/data", name="relatorio_ldo_orcamento_data")
@handle_exceptions
async def relatorio_ldo_orcamento_data(request: Request):
    """API JSON para dados do gráfico de LDO & Orçamento."""
    params = request.query_params
    ano = int(params.get("ano", date.today().year))
    
    data = get_ldo_orcamento_data(ano)
    return JSONResponse(data)



@router.get("/relatorios/previsao-realizado", name="relatorio_previsao_realizado")
@handle_exceptions
async def relatorio_previsao_realizado(request: Request):
    anos_disponiveis = get_available_years()
    ano_default = anos_disponiveis[0] if anos_disponiveis else date.today().year
    cenarios = list_active_cenarios()
    meses = [(i, MONTH_NAME_PT[i]) for i in range(1, 13)]
    qualificadores = [
        q for q in list_active_qualificadores() if q.is_folha()
    ]
    return templates.TemplateResponse(
        "rel_previsao_realizado.html",
        {
            "request": request,
            "anos_disponiveis": anos_disponiveis,
            "ano_default": ano_default,
            "cenarios": cenarios,
            "meses": meses,
            "qualificadores": qualificadores,
        },
    )


@router.get(
    "/relatorios/previsao-realizado/data",
    name="relatorio_previsao_realizado_data",
)
@handle_exceptions

async def relatorio_previsao_realizado_data(request: Request):
    from ..services.previsao_service import get_previsao_realizado_data
    
    params = request.query_params
    ano = int(params.get("ano", date.today().year))
    cenario_id = int(params.get("cenario")) if params.get("cenario") else None
    meses = [int(m) for m in params.get("meses", "").split(",") if m]
    qualificadores_ids = [
        int(q) for q in params.get("qualificadores", "").split(",") if q
    ]
    
    data = get_previsao_realizado_data(ano, cenario_id, meses, qualificadores_ids)
    return JSONResponse(data)
@router.get("/relatorios/resumo")
@router.post("/relatorios/resumo")
@handle_exceptions
async def relatorio_resumo(request: Request):
    anos_disponiveis = get_available_years()
    ano_default = anos_disponiveis[0] if anos_disponiveis else date.today().year
    form = await request.form() if request.method == "POST" else {}
    ano_selecionado = int(form.get("ano", ano_default))
    estrategia = form.get("estrategia", "realizado")
    cenario_id = form.get("cenario_id")
    cenarios_disponiveis = list_active_cenarios()
    cenario_selecionado_id = int(cenario_id) if cenario_id else None
    meses_selecionados_str = form.getlist("meses") if hasattr(form, "getlist") else []
    meses_selecionados = (
        list(range(1, 13))
        if not meses_selecionados_str
        else [int(m) for m in meses_selecionados_str]
    )
    
    data = get_resumo_data(ano_selecionado, meses_selecionados, estrategia, cenario_selecionado_id)

    return templates.TemplateResponse(
        "rel_resumo.html",
        {
            "request": request,
            "total_entradas_periodo": data["total_entradas_periodo"],
            "total_saidas_periodo": data["total_saidas_periodo"],
            "disponibilidade_periodo": data["disponibilidade_periodo"],
            "cash_flow_data": data["cash_flow_data"],
            "ano_selecionado": ano_selecionado,
            "anos_disponiveis": anos_disponiveis,
            "meses_selecionados": [str(m) for m in meses_selecionados],
            "meses_nomes": data["meses_nomes"],
            "estrategia_selecionada": estrategia,
            "cenario_selecionado_id": cenario_selecionado_id,
            "cenarios_disponiveis": cenarios_disponiveis,
        },
    )


@router.get("/relatorios/indicadores")
@router.post("/relatorios/indicadores")
@handle_exceptions
async def relatorio_indicadores(request: Request):
    anos_disponiveis = get_available_years()
    ano_default = anos_disponiveis[0] if anos_disponiveis else date.today().year
    form = await request.form() if request.method == "POST" else {}
    ano_selecionado = int(form.get("ano", ano_default))
    tipo_selecionado = form.get("tipo", "ambos")
    meses_selecionados_str = form.getlist("meses") if hasattr(form, "getlist") else []
    meses_selecionados = (
        list(range(1, 13))
        if not meses_selecionados_str
        else [int(m) for m in meses_selecionados_str]
    )
    
    data = get_indicadores_data(ano_selecionado, meses_selecionados, tipo_selecionado)

    return templates.TemplateResponse(
        "rel_indicadores.html",
        {
            "request": request,
            "area_chart_data": data["area_chart_data"],
            "pie_chart_data": data["pie_chart_data"],
            "projection_chart_data": data["projection_chart_data"],
            "ano_selecionado": ano_selecionado,
            "anos_disponiveis": anos_disponiveis,
            "tipo_selecionado": tipo_selecionado,
            "meses_selecionados": [str(m) for m in meses_selecionados],
            "meses_nomes": data["meses_nomes"],
        },
    )


@router.get("/relatorios/analise-comparativa")
@router.post("/relatorios/analise-comparativa")
@handle_exceptions
async def relatorio_analise_comparativa(request: Request):
    form = await request.form() if request.method == "POST" else {}
    tipo_analise = form.get("tipo_analise", "receitas")
    anos_disponiveis = get_available_years()
    ano1_default = (
        anos_disponiveis[1] if len(anos_disponiveis) > 1 else (date.today().year - 1)
    )
    ano2_default = anos_disponiveis[0] if anos_disponiveis else date.today().year
    ano1 = int(form.get("ano1", ano1_default))
    ano2 = int(form.get("ano2", ano2_default))
    meses_selecionados_str = form.getlist("meses") if hasattr(form, "getlist") else []
    meses_selecionados = (
        list(range(1, 13))
        if not meses_selecionados_str
        else [int(m) for m in meses_selecionados_str]
    )
    
    data = get_analise_comparativa_data(ano1, ano2, meses_selecionados, tipo_analise)

    return templates.TemplateResponse(
        "rel_analise_comparativa.html",
        {
            "request": request,
            "data": data["data"],
            "totals": data["totals"],
            "tipo_analise": tipo_analise,
            "ano1": ano1,
            "ano2": ano2,
            "anos_disponiveis": anos_disponiveis,
            "meses_selecionados": [str(m) for m in meses_selecionados],
            "meses_nomes": data["meses_nomes"],
        },
    )

@router.get("/relatorios/saldos-diarios", name="relatorio_saldos_diarios")
@router.post("/relatorios/saldos-diarios", name="relatorio_saldos_diarios")
@handle_exceptions
async def relatorio_saldos_diarios(request: Request):
    form = await request.form() if request.method == "POST" else {}
    data_ref_str = form.get("data_ref")
    hoje = date.today()
    data_ref = date.fromisoformat(data_ref_str) if data_ref_str else hoje

    data = get_saldos_diarios_data(data_ref)

    return templates.TemplateResponse(
        "rel_saldos_diarios.html",
        {
            "request": request,
            "data_ref": data_ref,
            "rows": data["rows"],
            "totais": data["totais"],
            "evolucao_labels": data["evolucao_labels"],
            "evolucao_saldos": data["evolucao_saldos"],
        },
    )


@router.get("/relatorios/dfc")
@router.post("/relatorios/dfc")
@handle_exceptions
async def relatorio_dfc(request: Request):
    """Tela de Análise de Fluxo (DFC) com dados reais ou projetados."""

    form = await request.form() if request.method == "POST" else {}
    periodo = form.get("periodo", "mes")
    data_sel = form.get("mes_ano")

    lancamento_years = (
        get_available_years()
    )
    anos_disponiveis = sorted(lancamento_years, reverse=True)

    hoje = date.today()
    if periodo == "mes":
        default = f"{hoje.year}-{hoje.month:02d}"
        data_sel = data_sel or default
        ano_selecionado, mes_selecionado = [int(x) for x in data_sel.split("-")]
    else:
        default = str(anos_disponiveis[0] if anos_disponiveis else hoje.year)
        data_sel = data_sel or default
        ano_selecionado = int(data_sel)
        mes_selecionado = None

    estrategia = form.get("estrategia", "realizado")
    cenario_id = form.get("cenario_id")
    cenario_selecionado_id = int(cenario_id) if cenario_id else None

    meses_selecionados_str = form.getlist("meses") if hasattr(form, "getlist") else []
    meses_selecionados = (
        [int(m) for m in meses_selecionados_str]
        if meses_selecionados_str
        else list(range(1, 13))
    )

    cenarios_disponiveis = list_active_cenarios()

    data = get_dfc_data(
        periodo,
        ano_selecionado,
        mes_selecionado,
        meses_selecionados,
        estrategia,
        cenario_selecionado_id,
    )

    return templates.TemplateResponse(
        "rel_dfc.html",
        {
            "request": request,
            "periodo": periodo,
            "mes_ano": data_sel,
            "headers": data["headers"],
            "dre_data": data["dre_data"],
            "totals": data["totals"],
            "estrategia_selecionada": estrategia,
            "cenario_selecionado_id": cenario_selecionado_id,
            "cenarios_disponiveis": cenarios_disponiveis,
            "meses_selecionados": [str(m) for m in meses_selecionados],
            "meses_nomes": data["meses_nomes"],
            "anos_disponiveis": anos_disponiveis,
            "meses_projetados": data["meses_projetados"],
        },
    )


@router.get("/relatorios/dfc/eventos")
@handle_exceptions
async def dfc_eventos(request: Request):
    """Retorna os eventos (lançamentos) para um qualificador e coluna."""

    seq = int(request.query_params.get("seq"))
    periodo = request.query_params.get("periodo", "mes")
    col = int(request.query_params.get("col"))
    mes_ano = request.query_params.get("mes_ano")
    estrategia = request.query_params.get("estrategia", "realizado")
    cenario_id = request.query_params.get("cenario_id")

    data = get_dfc_eventos(seq, periodo, col, mes_ano, estrategia, cenario_id)

    return JSONResponse({"eventos": data["eventos"], "total": data["total"]})
