"""Service para o histórico de projeções (versões salvas)."""
import json
from datetime import date, datetime
from typing import Dict, List, Optional, Tuple

import pandas as pd
from sqlalchemy import and_, extract, func

from ..models import db, ProjecaoVersao, ProjecaoValor, Lancamento
from ..repositories import projecao_versao_repository as repo
from .simulador_cenario_service import (
    executar_simulacao,
    obter_simulador_completo,
)


# Mapeamento entre cod_tipo_lancamento (FK em flc_lancamento) e cod_tipo
# usado em flc_projecao_valor: 1 = Entrada → 'R', 2 = Saída → 'D'.
_TIPO_LANCAMENTO_PARA_PROJECAO = {1: 'R', 2: 'D'}


# ==================== Salvar nova versão ====================

def salvar_projecao_como_versao(
    seq_simulador_cenario: int,
    nom_versao: str,
    dsc_motivo: Optional[str] = None,
    user_id: Optional[int] = None,
    publicar: bool = False,
) -> ProjecaoVersao:
    """Executa a simulação atual do cenário e persiste como uma versão.

    Cria header em flc_projecao_versao + linhas em flc_projecao_valor numa
    única transação. Se algo falhar, faz rollback.
    """
    if not nom_versao or not nom_versao.strip():
        raise ValueError("nom_versao é obrigatório")

    resultado = executar_simulacao(seq_simulador_cenario)
    if resultado is None:
        raise ValueError(f"Simulação não pôde ser executada para cenário {seq_simulador_cenario}")

    cenario_completo = obter_simulador_completo(seq_simulador_cenario)
    json_inputs = _serializar_inputs(cenario_completo)
    json_resumo = json.dumps({
        'total_receita': float(resultado['resumo']['total_receita'] or 0),
        'total_despesa': float(resultado['resumo']['total_despesa'] or 0),
        'saldo_final': float(resultado['resumo']['saldo_final'] or 0),
    })

    try:
        versao = ProjecaoVersao(
            seq_simulador_cenario=seq_simulador_cenario,
            nom_versao=nom_versao.strip(),
            dsc_motivo=(dsc_motivo or '').strip() or None,
            dat_versao=datetime.now(),
            cod_pessoa=user_id,
            ind_publicado='S' if publicar else 'N',
            json_inputs=json_inputs,
            json_resumo=json_resumo,
        )
        repo.create_versao(versao)

        valores = _montar_linhas_valor(versao.seq_projecao_versao, resultado)
        repo.bulk_insert_valores(valores)

        repo.commit()
        return versao
    except Exception:
        repo.rollback()
        raise


def _serializar_inputs(cenario_completo: Optional[Dict]) -> str:
    """Serializa config + ajustes do cenário para auditoria (json_inputs)."""
    if not cenario_completo:
        return json.dumps({})

    def _config(secao):
        cfg = secao.get('config') if secao else None
        if not cfg:
            return None
        return {
            'cod_tipo_cenario': cfg.cod_tipo_cenario,
            'json_configuracao': cfg.json_configuracao,
        }

    def _ajustes(secao):
        return [
            {
                'seq_qualificador': a.seq_qualificador,
                'ano': a.ano,
                'mes': a.mes,
                'cod_tipo_ajuste': a.cod_tipo_ajuste,
                'val_ajuste': float(a.val_ajuste) if a.val_ajuste else 0,
            }
            for a in (secao.get('ajustes') or [])
        ]

    simulador = cenario_completo.get('simulador')
    return json.dumps({
        'simulador': {
            'nom_cenario': simulador.nom_cenario if simulador else None,
            'ano_base': simulador.ano_base if simulador else None,
            'meses_projecao': simulador.meses_projecao if simulador else None,
            'cod_periodicidade': getattr(simulador, 'cod_periodicidade', None),
            'cod_metodo_base': getattr(simulador, 'cod_metodo_base', None),
            'json_config_base': getattr(simulador, 'json_config_base', None),
        },
        'receita': {
            'config': _config(cenario_completo.get('receita')),
            'ajustes': _ajustes(cenario_completo.get('receita') or {}),
        },
        'despesa': {
            'config': _config(cenario_completo.get('despesa')),
            'ajustes': _ajustes(cenario_completo.get('despesa') or {}),
        },
    }, default=str)


def _montar_linhas_valor(seq_versao: int, resultado: Dict) -> List[Dict]:
    """Constrói lista de dicts para bulk_insert em flc_projecao_valor.

    Prefere o DataFrame `_detalhada` (com seq_qualificador). Se não houver
    (modelos agregados como ARIMA/HOLT_WINTERS), persiste com
    seq_qualificador NULL — o total ainda é consultável.
    """
    linhas: List[Dict] = []

    receita_df = resultado.get('projecao_receita_detalhada')
    if receita_df is None or len(receita_df) == 0:
        receita_df = resultado.get('projecao_receita')
    linhas.extend(_df_para_linhas(receita_df, seq_versao, 'R'))

    despesa_df = resultado.get('projecao_despesa_detalhada')
    if despesa_df is None or len(despesa_df) == 0:
        despesa_df = resultado.get('projecao_despesa')
    linhas.extend(_df_para_linhas(despesa_df, seq_versao, 'D'))

    return linhas


def _df_para_linhas(df, seq_versao: int, cod_tipo: str) -> List[Dict]:
    if df is None or len(df) == 0:
        return []
    out: List[Dict] = []
    for _, row in df.iterrows():
        data = row.get('data')
        if pd.isna(data):
            continue
        ano = int(data.year)
        mes = int(data.month)
        seq_q = row.get('seq_qualificador') if 'seq_qualificador' in df.columns else None
        if pd.isna(seq_q):
            seq_q = None
        elif seq_q is not None:
            seq_q = int(seq_q)
        valor = row.get('valor_projetado', 0)
        if pd.isna(valor):
            valor = 0
        out.append({
            'seq_projecao_versao': seq_versao,
            'seq_qualificador': seq_q,
            'cod_tipo': cod_tipo,
            'ano': ano,
            'mes': mes,
            'val_projetado': float(valor),
        })
    return out


# ==================== Listagem / leitura ====================

def list_versoes(seq_simulador_cenario: int) -> List[Dict]:
    """Lista versões com resumo expandido para a tela de histórico."""
    versoes = repo.list_versoes_by_simulador(seq_simulador_cenario)
    out = []
    for v in versoes:
        resumo = {}
        if v.json_resumo:
            try:
                resumo = json.loads(v.json_resumo)
            except (json.JSONDecodeError, TypeError):
                resumo = {}
        out.append({
            'seq_projecao_versao': v.seq_projecao_versao,
            'nom_versao': v.nom_versao,
            'dsc_motivo': v.dsc_motivo,
            'dat_versao': v.dat_versao,
            'ind_publicado': v.ind_publicado,
            'cod_pessoa': v.cod_pessoa,
            'total_receita': resumo.get('total_receita', 0),
            'total_despesa': resumo.get('total_despesa', 0),
            'saldo_final': resumo.get('saldo_final', 0),
        })
    return out


def get_versao_detalhe(seq_projecao_versao: int) -> Optional[Dict]:
    versao = repo.get_versao_by_id(seq_projecao_versao)
    if versao is None:
        return None
    valores = repo.get_valores_by_versao(seq_projecao_versao)
    resumo = {}
    if versao.json_resumo:
        try:
            resumo = json.loads(versao.json_resumo)
        except (json.JSONDecodeError, TypeError):
            resumo = {}

    receita_linhas = []
    despesa_linhas = []
    for v in valores:
        item = {
            'seq_qualificador': v.seq_qualificador,
            'qualificador_desc': v.qualificador.dsc_qualificador if v.qualificador else None,
            'ano': v.ano,
            'mes': v.mes,
            'val_projetado': float(v.val_projetado or 0),
            'val_realizado': float(v.val_realizado) if v.val_realizado is not None else None,
        }
        if v.cod_tipo == 'R':
            receita_linhas.append(item)
        else:
            despesa_linhas.append(item)

    return {
        'versao': versao,
        'resumo': resumo,
        'receita': receita_linhas,
        'despesa': despesa_linhas,
    }


def comparar_versoes(seq_versao_a: int, seq_versao_b: int) -> Optional[Dict]:
    versao_a = repo.get_versao_by_id(seq_versao_a)
    versao_b = repo.get_versao_by_id(seq_versao_b)
    if versao_a is None or versao_b is None:
        return None
    if versao_a.seq_simulador_cenario != versao_b.seq_simulador_cenario:
        raise ValueError("Versões pertencem a cenários diferentes")

    linhas = repo.get_comparativo(seq_versao_a, seq_versao_b)

    # Enriquecer com descrição do qualificador (consulta única em batch).
    seq_quals = {l['seq_qualificador'] for l in linhas if l['seq_qualificador']}
    desc_map = {}
    if seq_quals:
        from ..models import Qualificador
        for q in Qualificador.query.filter(Qualificador.seq_qualificador.in_(seq_quals)).all():
            desc_map[q.seq_qualificador] = q.dsc_qualificador

    for l in linhas:
        l['qualificador_desc'] = desc_map.get(l['seq_qualificador'])

    total_a = sum(l['val_a'] for l in linhas)
    total_b = sum(l['val_b'] for l in linhas)
    return {
        'versao_a': versao_a,
        'versao_b': versao_b,
        'linhas': linhas,
        'total_a': total_a,
        'total_b': total_b,
        'delta_total': total_b - total_a,
    }


# ==================== Mutações administrativas ====================

def deletar_versao(seq_projecao_versao: int) -> int:
    return repo.delete_versao(seq_projecao_versao)


def publicar_versao(seq_projecao_versao: int) -> Optional[ProjecaoVersao]:
    return repo.publicar_versao(seq_projecao_versao)


# ==================== Frustração x Excesso (RF-24) ====================

def atualizar_realizados_de_lancamentos(
    seq_projecao_versao: int,
    ate_data: Optional[date] = None,
) -> int:
    """Preenche val_realizado em ProjecaoValor agregando flc_lancamento.

    Considera apenas linhas cujo (ano, mês) já esteja no passado em relação a
    `ate_data` (default: hoje) — o mês corrente não é fechado, então não
    sobrescreve com valor parcial.

    Retorna a quantidade de linhas atualizadas.
    """
    versao = repo.get_versao_by_id(seq_projecao_versao)
    if versao is None:
        raise ValueError(f"Versão {seq_projecao_versao} não encontrada")

    ate = ate_data or date.today()
    primeiro_dia_mes_corrente = date(ate.year, ate.month, 1)

    # 1. Carrega chaves (seq_qualificador, cod_tipo, ano, mes) da versão para
    #    meses já fechados.
    linhas_versao = (
        db.session.query(
            ProjecaoValor.seq_qualificador,
            ProjecaoValor.cod_tipo,
            ProjecaoValor.ano,
            ProjecaoValor.mes,
        )
        .filter(ProjecaoValor.seq_projecao_versao == seq_projecao_versao)
        .filter(ProjecaoValor.seq_qualificador.isnot(None))
        .all()
    )
    chaves_fechadas = [
        (sq, tipo, ano, mes)
        for sq, tipo, ano, mes in linhas_versao
        if date(ano, mes, 1) < primeiro_dia_mes_corrente
    ]
    if not chaves_fechadas:
        return 0

    # 2. Agrega flc_lancamento por (qualificador, tipo, ano, mes). Faz um
    #    único query agrupado e indexa em memória — evita N round-trips.
    seq_quals = {sq for sq, _, _, _ in chaves_fechadas}
    anos = {ano for _, _, ano, _ in chaves_fechadas}

    rows = (
        db.session.query(
            Lancamento.seq_qualificador,
            Lancamento.cod_tipo_lancamento,
            extract('year', Lancamento.dat_lancamento).label('ano'),
            extract('month', Lancamento.dat_lancamento).label('mes'),
            func.sum(Lancamento.val_lancamento).label('total'),
        )
        .filter(Lancamento.ind_status == 'A')
        .filter(Lancamento.seq_qualificador.in_(seq_quals))
        .filter(extract('year', Lancamento.dat_lancamento).in_(anos))
        .filter(Lancamento.dat_lancamento < primeiro_dia_mes_corrente)
        .group_by(
            Lancamento.seq_qualificador,
            Lancamento.cod_tipo_lancamento,
            'ano',
            'mes',
        )
        .all()
    )
    realizados_idx: Dict[Tuple[int, str, int, int], float] = {}
    for sq, cod_tipo_lanc, ano, mes, total in rows:
        tipo = _TIPO_LANCAMENTO_PARA_PROJECAO.get(cod_tipo_lanc)
        if tipo is None:
            continue
        chave = (int(sq), tipo, int(ano), int(mes))
        realizados_idx[chave] = float(total or 0)

    # 3. Constrói a lista de tuplas para o repository (linhas sem realizado
    #    ficam com 0 — significa "mês fechado e zerado").
    realizados: List[Tuple[int, str, int, int, float]] = []
    for sq, tipo, ano, mes in chaves_fechadas:
        valor = realizados_idx.get((sq, tipo, ano, mes), 0.0)
        realizados.append((sq, tipo, ano, mes, valor))

    return repo.atualizar_realizado(seq_projecao_versao, realizados)
