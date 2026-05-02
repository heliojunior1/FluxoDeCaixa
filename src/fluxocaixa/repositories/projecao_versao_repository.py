"""Repository para o histórico de projeções (versões e valores normalizados)."""
from typing import Iterable, List, Optional, Dict, Tuple

from sqlalchemy import func

from ..models import db, ProjecaoVersao, ProjecaoValor


# ==================== Versão (header) ====================

def create_versao(versao: ProjecaoVersao) -> ProjecaoVersao:
    db.session.add(versao)
    db.session.flush()  # garante seq_projecao_versao antes do bulk_insert
    return versao


def commit():
    db.session.commit()


def rollback():
    db.session.rollback()


def get_versao_by_id(seq_projecao_versao: int) -> Optional[ProjecaoVersao]:
    return ProjecaoVersao.query.get(seq_projecao_versao)


def list_versoes_by_simulador(seq_simulador_cenario: int) -> List[ProjecaoVersao]:
    return (
        ProjecaoVersao.query
        .filter_by(seq_simulador_cenario=seq_simulador_cenario)
        .order_by(ProjecaoVersao.dat_versao.desc())
        .all()
    )


def delete_versao(seq_projecao_versao: int) -> int:
    """Apaga uma versão. Apenas rascunhos podem ser deletados."""
    versao = ProjecaoVersao.query.get(seq_projecao_versao)
    if versao is None:
        return 0
    if versao.ind_publicado == 'S':
        raise ValueError("Versão publicada não pode ser deletada")
    db.session.delete(versao)
    db.session.commit()
    return 1


def publicar_versao(seq_projecao_versao: int) -> Optional[ProjecaoVersao]:
    versao = ProjecaoVersao.query.get(seq_projecao_versao)
    if versao is None:
        return None
    versao.ind_publicado = 'S'
    db.session.commit()
    return versao


# ==================== Valor (linhas) ====================

def bulk_insert_valores(valores: Iterable[Dict]) -> int:
    """Insere em lote linhas de ProjecaoValor.

    Cada dict deve conter:
        seq_projecao_versao, cod_tipo, ano, mes, val_projetado
        seq_qualificador (opcional, pode ser None para modelos agregados),
        val_realizado (opcional)
    """
    valores = list(valores)
    if not valores:
        return 0
    db.session.bulk_insert_mappings(ProjecaoValor, valores)
    return len(valores)


def get_valores_by_versao(
    seq_projecao_versao: int,
    cod_tipo: Optional[str] = None,
) -> List[ProjecaoValor]:
    query = ProjecaoValor.query.filter_by(seq_projecao_versao=seq_projecao_versao)
    if cod_tipo:
        query = query.filter_by(cod_tipo=cod_tipo)
    return (
        query.order_by(
            ProjecaoValor.cod_tipo,
            ProjecaoValor.seq_qualificador,
            ProjecaoValor.ano,
            ProjecaoValor.mes,
        ).all()
    )


def get_totais_por_tipo(seq_projecao_versao: int) -> Dict[str, float]:
    """Retorna {'R': total_receita, 'D': total_despesa} via SQL."""
    rows = (
        db.session.query(
            ProjecaoValor.cod_tipo,
            func.coalesce(func.sum(ProjecaoValor.val_projetado), 0),
        )
        .filter(ProjecaoValor.seq_projecao_versao == seq_projecao_versao)
        .group_by(ProjecaoValor.cod_tipo)
        .all()
    )
    return {tipo: float(total or 0) for tipo, total in rows}


def get_comparativo(
    seq_versao_a: int,
    seq_versao_b: int,
) -> List[Dict]:
    """Compara duas versões linha a linha (full outer join via UNION).

    Retorna lista de dicts com:
        seq_qualificador, cod_tipo, ano, mes, val_a, val_b, delta, delta_pct
    """
    rows_a = {
        (v.cod_tipo, v.seq_qualificador, v.ano, v.mes): float(v.val_projetado or 0)
        for v in get_valores_by_versao(seq_versao_a)
    }
    rows_b = {
        (v.cod_tipo, v.seq_qualificador, v.ano, v.mes): float(v.val_projetado or 0)
        for v in get_valores_by_versao(seq_versao_b)
    }

    chaves = sorted(set(rows_a.keys()) | set(rows_b.keys()))
    resultado = []
    for chave in chaves:
        cod_tipo, seq_qualificador, ano, mes = chave
        val_a = rows_a.get(chave, 0.0)
        val_b = rows_b.get(chave, 0.0)
        delta = val_b - val_a
        delta_pct = (delta / val_a * 100) if val_a else None
        resultado.append({
            'cod_tipo': cod_tipo,
            'seq_qualificador': seq_qualificador,
            'ano': ano,
            'mes': mes,
            'val_a': val_a,
            'val_b': val_b,
            'delta': delta,
            'delta_pct': delta_pct,
        })
    return resultado


def atualizar_realizado(
    seq_projecao_versao: int,
    realizados: List[Tuple[int, str, int, int, float]],
) -> int:
    """Atualiza val_realizado em lote.

    realizados: lista de (seq_qualificador, cod_tipo, ano, mes, val_realizado).
    """
    count = 0
    for seq_q, tipo, ano, mes, val in realizados:
        atualizadas = (
            ProjecaoValor.query
            .filter_by(
                seq_projecao_versao=seq_projecao_versao,
                seq_qualificador=seq_q,
                cod_tipo=tipo,
                ano=ano,
                mes=mes,
            )
            .update({'val_realizado': val})
        )
        count += atualizadas
    db.session.commit()
    return count
