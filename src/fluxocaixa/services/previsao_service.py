from datetime import date

from fastapi import Request
from fastapi.responses import JSONResponse
from sqlalchemy import extract, func

from ..models import (
    db,
    TipoLancamento,
    Lancamento,
    Cenario,
    CenarioAjusteMensal,
    Qualificador,
)
from ..utils import format_currency
from ..utils.constants import MONTH_ABBR_PT


async def relatorio_previsao_realizado_data(request: Request):
    params = request.query_params
    ano = int(params.get("ano", date.today().year))
    cenario_id = int(params.get("cenario")) if params.get("cenario") else None
    meses = [int(m) for m in params.get("meses", "").split(",") if m]
    qualificadores_ids = [
        int(q) for q in params.get("qualificadores", "").split(",") if q
    ]
    if not meses:
        meses = list(range(1, 13))

    tipo_entrada = TipoLancamento.query.filter_by(
        dsc_tipo_lancamento="Entrada"
    ).first()
    tipo_saida = TipoLancamento.query.filter_by(
        dsc_tipo_lancamento="Saída"
    ).first()
    cod_entrada = tipo_entrada.cod_tipo_lancamento if tipo_entrada else None
    cod_saida = tipo_saida.cod_tipo_lancamento if tipo_saida else None

    qs = Qualificador.query.filter(
        Qualificador.seq_qualificador.in_(qualificadores_ids)
    ).all()
    qual_tipo_map = {
        q.seq_qualificador: (cod_saida if q.tipo_fluxo == "despesa" else cod_entrada)
        for q in qs
    }

    anos_range = [ano - 2, ano - 1, ano]
    anos_base = {a - 1 for a in anos_range}
    anos_needed = set(anos_range) | anos_base
    lanc_rows = (
        db.session.query(
            Lancamento.seq_qualificador,
            extract("year", Lancamento.dat_lancamento).label("ano"),
            extract("month", Lancamento.dat_lancamento).label("mes"),
            Lancamento.cod_tipo_lancamento,
            func.sum(Lancamento.val_lancamento).label("total"),
        )
        .filter(
            Lancamento.seq_qualificador.in_(qualificadores_ids),
            extract("year", Lancamento.dat_lancamento).in_(anos_needed),
            extract("month", Lancamento.dat_lancamento).in_(range(1, 13)),
            Lancamento.ind_status == "A",
        )
        .group_by(
            Lancamento.seq_qualificador,
            "ano",
            "mes",
            Lancamento.cod_tipo_lancamento,
        )
        .all()
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

    cenario_base = Cenario.query.get(cenario_id) if cenario_id else None
    cenario_cache = {}

    def get_cenario_ids_for_year(year):
        if not cenario_base:
            return None, None
        if year in cenario_cache:
            return cenario_cache[year]
        cenarios_year = (
            Cenario.query
            .filter(
                Cenario.nom_cenario == cenario_base.nom_cenario,
                extract("year", Cenario.dat_criacao) == year,
            )
            .order_by(Cenario.dat_criacao)
            .all()
        )
        if not cenarios_year:
            cenario_cache[year] = (None, None)
        else:
            cenario_cache[year] = (
                cenarios_year[0].seq_cenario,
                cenarios_year[-1].seq_cenario,
            )
        return cenario_cache[year]

    for yr in anos_range:
        get_cenario_ids_for_year(yr)
    cenario_ini_id, cenario_fin_id = cenario_cache.get(ano, (None, None))
    cenario_ids_needed = {
        cid
        for pair in cenario_cache.values()
        for cid in pair
        if cid is not None
    }
    ajustes = (
        CenarioAjusteMensal.query.filter(
            CenarioAjusteMensal.seq_cenario.in_(cenario_ids_needed),
            CenarioAjusteMensal.ano.in_(anos_range),
            CenarioAjusteMensal.seq_qualificador.in_(qualificadores_ids),
        ).all()
        if cenario_ids_needed
        else []
    )
    ajuste_map = {
        (a.seq_cenario, a.seq_qualificador, a.ano, a.mes): a for a in ajustes
    }

    def previsao_val_for_year(cenario_ref_id, q_id, mes, ano_ref):
        base = lanc_val(q_id, ano_ref - 1, mes, qual_tipo_map.get(q_id, cod_entrada))
        if cenario_ref_id:
            ajuste = ajuste_map.get((cenario_ref_id, q_id, ano_ref, mes))
            if ajuste:
                if ajuste.cod_tipo_ajuste == "P":
                    return base * (1 + float(ajuste.val_ajuste) / 100)
                return base + float(ajuste.val_ajuste)
        return base

    def real_val(q_id, ano_ref, meses_ref):
        cod_tipo = qual_tipo_map[q_id]
        return sum(lanc_val(q_id, ano_ref, m, cod_tipo) for m in meses_ref)

    tabela = []
    total_prev_ini = total_prev_fin = total_real = 0
    for q in qs:
        prev_ini = sum(
            previsao_val_for_year(cenario_ini_id, q.seq_qualificador, m, ano)
            for m in meses
        )
        prev_fin = sum(
            previsao_val_for_year(cenario_fin_id, q.seq_qualificador, m, ano)
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
        prev_total = sum(
            previsao_val_for_year(cenario_fin_id, q_id, m, ano)
            for q_id in qualificadores_ids
        )
        real_total = sum(
            real_val(q_id, ano, [m]) for q_id in qualificadores_ids
        )
        previsao_series.append(round(prev_total / 1_000_000_000, 3))
        realizado_series.append(round(real_total / 1_000_000_000, 3))

    diff_final = []
    diff_inicial = []
    for a in anos_range:
        c_ini_id, c_fin_id = cenario_cache.get(a, (None, None))
        inicial_sum = sum(
            previsao_val_for_year(c_ini_id, q_id, m, a)
            for q_id in qualificadores_ids
            for m in range(1, 13)
        )
        final_sum = sum(
            previsao_val_for_year(c_fin_id, q_id, m, a)
            for q_id in qualificadores_ids
            for m in range(1, 13)
        )
        real_year = sum(
            real_val(q_id, a, list(range(1, 13))) for q_id in qualificadores_ids
        )
        diff_final.append(round((real_year - final_sum) / 1_000_000_000, 3))
        diff_inicial.append(round((real_year - inicial_sum) / 1_000_000_000, 3))

    return JSONResponse(
        {
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
    )

