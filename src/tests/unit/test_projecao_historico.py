"""Testes do histórico de projeções (Alternativa 2).

Foca no service e repository, sem depender da execução real de modelos
econômicos. O DataFrame de projeção é mockado via monkeypatch em
`executar_simulacao` e `obter_simulador_completo`.
"""
from datetime import datetime
import pandas as pd
import pytest


@pytest.fixture
def cenario_fake(client):
    """Cria um SimuladorCenario mínimo apenas para satisfazer a FK."""
    from fluxocaixa.models import db, SimuladorCenario
    s = SimuladorCenario(
        nom_cenario='Cenário Teste Histórico',
        dsc_cenario='para tests',
        ano_base=2026,
        meses_projecao=3,
        ind_status='A',
        cod_pessoa_inclusao=1,
    )
    db.session.add(s)
    db.session.commit()
    return s


def _mock_resultado(ano=2026):
    """Constrói um resultado de executar_simulacao com 3 meses x 2 qualificadores."""
    receita_rows = [
        {'data': pd.Timestamp(ano, 1, 15), 'seq_qualificador': 101, 'valor_projetado': 100.0},
        {'data': pd.Timestamp(ano, 2, 15), 'seq_qualificador': 101, 'valor_projetado': 110.0},
        {'data': pd.Timestamp(ano, 3, 15), 'seq_qualificador': 101, 'valor_projetado': 120.0},
        {'data': pd.Timestamp(ano, 1, 15), 'seq_qualificador': 102, 'valor_projetado': 50.0},
    ]
    despesa_rows = [
        {'data': pd.Timestamp(ano, 1, 15), 'seq_qualificador': 201, 'valor_projetado': -80.0},
        {'data': pd.Timestamp(ano, 2, 15), 'seq_qualificador': 201, 'valor_projetado': -85.0},
    ]
    receita_df = pd.DataFrame(receita_rows)
    despesa_df = pd.DataFrame(despesa_rows)
    return {
        'simulador': None,
        'projecao_receita': receita_df,
        'projecao_despesa': despesa_df,
        'projecao_receita_detalhada': receita_df,
        'projecao_despesa_detalhada': despesa_df,
        'cenario_total': pd.DataFrame(),
        'resumo': {
            'total_receita': float(receita_df['valor_projetado'].sum()),
            'total_despesa': float(despesa_df['valor_projetado'].sum()),
            'saldo_final': float(
                receita_df['valor_projetado'].sum() + despesa_df['valor_projetado'].sum()
            ),
        },
    }


def test_salvar_versao_persiste_header_e_linhas(client, cenario_fake, monkeypatch):
    from fluxocaixa.services import projecao_versao_service as svc

    monkeypatch.setattr(svc, 'executar_simulacao', lambda _id: _mock_resultado())
    monkeypatch.setattr(svc, 'obter_simulador_completo', lambda _id: {'simulador': cenario_fake})

    versao = svc.salvar_projecao_como_versao(
        seq_simulador_cenario=cenario_fake.seq_simulador_cenario,
        nom_versao='1ª Reestimativa',
        dsc_motivo='teste',
        user_id=42,
    )

    assert versao.seq_projecao_versao is not None
    assert versao.nom_versao == '1ª Reestimativa'
    assert versao.ind_publicado == 'N'
    assert versao.cod_pessoa == 42

    detalhe = svc.get_versao_detalhe(versao.seq_projecao_versao)
    assert detalhe is not None
    assert len(detalhe['receita']) == 4  # 3 + 1
    assert len(detalhe['despesa']) == 2
    assert detalhe['resumo']['total_receita'] == 380.0
    assert detalhe['resumo']['total_despesa'] == -165.0


def test_salvar_versao_nome_obrigatorio(client, cenario_fake, monkeypatch):
    from fluxocaixa.services import projecao_versao_service as svc

    monkeypatch.setattr(svc, 'executar_simulacao', lambda _id: _mock_resultado())
    monkeypatch.setattr(svc, 'obter_simulador_completo', lambda _id: {'simulador': cenario_fake})

    with pytest.raises(ValueError):
        svc.salvar_projecao_como_versao(
            seq_simulador_cenario=cenario_fake.seq_simulador_cenario,
            nom_versao='   ',
        )


def test_listar_versoes_ordem_decrescente(client, cenario_fake, monkeypatch):
    from fluxocaixa.services import projecao_versao_service as svc

    monkeypatch.setattr(svc, 'executar_simulacao', lambda _id: _mock_resultado())
    monkeypatch.setattr(svc, 'obter_simulador_completo', lambda _id: {'simulador': cenario_fake})

    v1 = svc.salvar_projecao_como_versao(cenario_fake.seq_simulador_cenario, 'A')
    v2 = svc.salvar_projecao_como_versao(cenario_fake.seq_simulador_cenario, 'B')

    versoes = svc.list_versoes(cenario_fake.seq_simulador_cenario)
    seqs = [v['seq_projecao_versao'] for v in versoes]
    # mais recente primeiro
    assert seqs[0] == v2.seq_projecao_versao
    assert v1.seq_projecao_versao in seqs


def test_comparar_versoes_calcula_delta(client, cenario_fake, monkeypatch):
    from fluxocaixa.services import projecao_versao_service as svc

    # Versão A com valores menores
    monkeypatch.setattr(svc, 'executar_simulacao', lambda _id: _mock_resultado())
    monkeypatch.setattr(svc, 'obter_simulador_completo', lambda _id: {'simulador': cenario_fake})
    v_a = svc.salvar_projecao_como_versao(cenario_fake.seq_simulador_cenario, 'A')

    # Versão B: receita do qualificador 101 / mes 1 sobe de 100 para 150
    def _resultado_b():
        r = _mock_resultado()
        r['projecao_receita'].loc[
            (r['projecao_receita']['seq_qualificador'] == 101)
            & (r['projecao_receita']['data'] == pd.Timestamp(2026, 1, 15)),
            'valor_projetado',
        ] = 150.0
        r['projecao_receita_detalhada'] = r['projecao_receita']
        r['resumo']['total_receita'] = float(r['projecao_receita']['valor_projetado'].sum())
        r['resumo']['saldo_final'] = (
            r['resumo']['total_receita'] + r['resumo']['total_despesa']
        )
        return r

    monkeypatch.setattr(svc, 'executar_simulacao', lambda _id: _resultado_b())
    v_b = svc.salvar_projecao_como_versao(cenario_fake.seq_simulador_cenario, 'B')

    cmp = svc.comparar_versoes(v_a.seq_projecao_versao, v_b.seq_projecao_versao)
    assert cmp is not None

    linha = next(
        l for l in cmp['linhas']
        if l['cod_tipo'] == 'R' and l['seq_qualificador'] == 101 and l['mes'] == 1
    )
    assert linha['val_a'] == 100.0
    assert linha['val_b'] == 150.0
    assert linha['delta'] == 50.0
    assert linha['delta_pct'] == 50.0
    assert cmp['delta_total'] == 50.0


def test_publicada_nao_pode_ser_deletada(client, cenario_fake, monkeypatch):
    from fluxocaixa.services import projecao_versao_service as svc

    monkeypatch.setattr(svc, 'executar_simulacao', lambda _id: _mock_resultado())
    monkeypatch.setattr(svc, 'obter_simulador_completo', lambda _id: {'simulador': cenario_fake})
    v = svc.salvar_projecao_como_versao(
        cenario_fake.seq_simulador_cenario, 'X', publicar=True
    )
    assert v.ind_publicado == 'S'

    with pytest.raises(ValueError):
        svc.deletar_versao(v.seq_projecao_versao)


def test_rota_listar_versoes_responde(client, cenario_fake):
    resp = client.get(f'/simulador/{cenario_fake.seq_simulador_cenario}/historico')
    assert resp.status_code == 200
    assert 'Histórico de Projeções' in resp.text


def test_atualizar_realizados_de_lancamentos(client, cenario_fake, monkeypatch):
    """Smoke do RF-24: agrega flc_lancamento em val_realizado."""
    from datetime import date as _date
    import pandas as pd

    from fluxocaixa.models import (
        db,
        Lancamento,
        Qualificador,
        TipoLancamento,
        OrigemLancamento,
    )
    from fluxocaixa.services import projecao_versao_service as svc

    # Garantir tipo/origem (podem já existir no seed).
    if not TipoLancamento.query.get(1):
        db.session.add(TipoLancamento(cod_tipo_lancamento=1, dsc_tipo_lancamento='Entrada'))
    if not OrigemLancamento.query.get(1):
        db.session.add(OrigemLancamento(cod_origem_lancamento=1, dsc_origem_lancamento='Manual'))

    # Qualificador dedicado para isolar do seed.
    qual = Qualificador(
        num_qualificador='9999',
        dsc_qualificador='Realizado Test',
        ind_status='A',
    )
    db.session.add(qual)
    db.session.commit()

    # Criar versão com 1 linha de receita em janeiro/2024 (mês fechado).
    receita_df = pd.DataFrame([
        {'data': pd.Timestamp(2024, 1, 15),
         'seq_qualificador': qual.seq_qualificador,
         'valor_projetado': 1000.0},
    ])
    despesa_df = pd.DataFrame(columns=['data', 'seq_qualificador', 'valor_projetado'])
    resultado = {
        'simulador': None,
        'projecao_receita': receita_df,
        'projecao_despesa': despesa_df,
        'projecao_receita_detalhada': receita_df,
        'projecao_despesa_detalhada': despesa_df,
        'cenario_total': pd.DataFrame(),
        'resumo': {'total_receita': 1000.0, 'total_despesa': 0.0, 'saldo_final': 1000.0},
    }
    monkeypatch.setattr(svc, 'executar_simulacao', lambda _id: resultado)
    monkeypatch.setattr(svc, 'obter_simulador_completo', lambda _id: {'simulador': cenario_fake})

    versao = svc.salvar_projecao_como_versao(
        cenario_fake.seq_simulador_cenario, 'Versão Realizado'
    )

    # Inserir 2 lançamentos em jan/2024 totalizando 750
    db.session.add_all([
        Lancamento(
            dat_lancamento=_date(2024, 1, 10),
            seq_qualificador=qual.seq_qualificador,
            val_lancamento=300,
            cod_tipo_lancamento=1,
            cod_origem_lancamento=1,
            cod_pessoa_inclusao=1,
            ind_status='A',
        ),
        Lancamento(
            dat_lancamento=_date(2024, 1, 20),
            seq_qualificador=qual.seq_qualificador,
            val_lancamento=450,
            cod_tipo_lancamento=1,
            cod_origem_lancamento=1,
            cod_pessoa_inclusao=1,
            ind_status='A',
        ),
    ])
    db.session.commit()

    atualizadas = svc.atualizar_realizados_de_lancamentos(versao.seq_projecao_versao)
    assert atualizadas == 1

    detalhe = svc.get_versao_detalhe(versao.seq_projecao_versao)
    linha = detalhe['receita'][0]
    assert linha['val_realizado'] == 750.0
    assert linha['val_projetado'] == 1000.0
