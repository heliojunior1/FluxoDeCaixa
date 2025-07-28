from datetime import date, timedelta
from sqlalchemy import func
import calendar
from ..models import (
    Mapeamento,
    Pagamento,
    Lancamento,
    Qualificador,
    Orgao,
    OrigemLancamento,
    TipoLancamento,
    Cenario,
    CenarioAjusteMensal,
    Conferencia,
)
from ..models.base import db

def seed_data(session=None):
    """Populate the database with some basic records for testing."""
    session = session or db.session
    # Clear existing data to ensure a clean slate for new values
    try:
        session.query(Mapeamento).delete()
    except:
        pass  # Table might not exist yet
    session.query(Pagamento).delete()
    session.query(Lancamento).delete()
    session.query(Qualificador).delete()
    session.query(Orgao).delete()
    session.query(OrigemLancamento).delete()
    session.query(TipoLancamento).delete()
    session.commit()

    # Base types and origins
    if not TipoLancamento.query.first():
        session.add_all([
            TipoLancamento(dsc_tipo_lancamento='Entrada'),
            TipoLancamento(dsc_tipo_lancamento='Saída'),
        ])

    if not OrigemLancamento.query.first():
        session.add_all([
            OrigemLancamento(dsc_origem_lancamento='IR'),
            OrigemLancamento(dsc_origem_lancamento='IPVA'),
            OrigemLancamento(dsc_origem_lancamento='ITCMD'),
            OrigemLancamento(dsc_origem_lancamento='ICMS'),
            OrigemLancamento(dsc_origem_lancamento='FECOEP'),
            OrigemLancamento(dsc_origem_lancamento='FPE'),
            OrigemLancamento(dsc_origem_lancamento='ROYALTIES'),
            OrigemLancamento(dsc_origem_lancamento='APLICAÇÕES FINANCEIRAS'),
            OrigemLancamento(dsc_origem_lancamento='DEMAIS RECEITAS'),
        ])

    if not Orgao.query.first():
        session.add_all([
            Orgao(nom_orgao='REPASSE MUNICÍPIOS'),
            Orgao(nom_orgao='REPASSE FUNDEB'),
            Orgao(nom_orgao='SAÚDE 12%'),
            Orgao(nom_orgao='EDUCAÇÃO 5%'),
            Orgao(nom_orgao='PODERES'),
            Orgao(nom_orgao='DÍVIDAS'),
            Orgao(nom_orgao='PASEP'),
            Orgao(nom_orgao='PRECATÓRIOS'),
            Orgao(nom_orgao='FOLHA'),
            Orgao(nom_orgao='CUSTEIO'),
            Orgao(nom_orgao='INVESTIMENTO + AUMENTO DE CAPITAL'),
            Orgao(nom_orgao='RESTOS A PAGAR TESOURO e DEMAIS'),
            Orgao(nom_orgao='FECOEP - RESTOS A PAGAR - FONTE 761'),
        ])

    # Populate Qualificadores (estrutura hierárquica)
    if not Qualificador.query.first():
        # Criar estrutura hierárquica baseada na imagem
        # Nível 0 - Saldo Inicial
        saldo_inicial = Qualificador(
            num_qualificador='0',
            dsc_qualificador='SALDO INICIAL',
            cod_qualificador_pai=None
        )
        session.add(saldo_inicial)
        session.flush()  # Para obter o ID
        
        # Nível 1 - Receita Líquida
        receita_liquida = Qualificador(
            num_qualificador='1',
            dsc_qualificador='RECEITA LÍQUIDA',
            cod_qualificador_pai=None
        )
        session.add(receita_liquida)
        session.flush()
        
        # Nível 2 - Impostos (dentro de Receita Líquida)
        impostos = Qualificador(
            num_qualificador='1.0',
            dsc_qualificador='IMPOSTOS',
            cod_qualificador_pai=receita_liquida.seq_qualificador
        )
        session.add(impostos)
        session.flush()
        
        # Nível 3 - Impostos específicos
        impostos_list = [
            ('1.0.0', 'ICMS'),
            ('1.0.1', 'IPVA'),
            ('1.5.2', 'ITCMD')
        ]
        
        for num, desc in impostos_list:
            qualif = Qualificador(
                num_qualificador=num,
                dsc_qualificador=desc,
                cod_qualificador_pai=impostos.seq_qualificador
            )
            session.add(qualif)
        
        session.flush()
        
        # Nível 2 - Transferências Federais
        transf_federais = Qualificador(
            num_qualificador='1.1',
            dsc_qualificador='TRANSFERÊNCIAS FEDERAIS',
            cod_qualificador_pai=receita_liquida.seq_qualificador
        )
        session.add(transf_federais)
        session.flush()
        
        # Adicionar FPE sob Transferências Federais
        fpe = Qualificador(
            num_qualificador='1.1.1',
            dsc_qualificador='FPE',
            cod_qualificador_pai=transf_federais.seq_qualificador
        )
        session.add(fpe)
        
        # Nível 2 - Demais Receitas
        demais_receitas = Qualificador(
            num_qualificador='1.2',
            dsc_qualificador='DEMAIS RECEITAS',
            cod_qualificador_pai=receita_liquida.seq_qualificador
        )
        session.add(demais_receitas)
        session.flush()
        
        # Receitas específicas
        outras_receitas = [
            ('1.2.1', 'FECOEP'),
            ('1.2.2', 'ROYALTIES'),
            ('1.2.3', 'APLICAÇÕES FINANCEIRAS'),
            ('1.2.4', 'IR'),
            ('1.2.5', 'OUTRAS RECEITAS')
        ]
        
        for num, desc in outras_receitas:
            qualif = Qualificador(
                num_qualificador=num,
                dsc_qualificador=desc,
                cod_qualificador_pai=demais_receitas.seq_qualificador
            )
            session.add(qualif)
        
        session.flush()
        
        # Nível 1 - Despesas
        despesas = Qualificador(
            num_qualificador='2',
            dsc_qualificador='DESPESAS',
            cod_qualificador_pai=None
        )
        session.add(despesas)
        session.flush()
        
        # Nível 2 - Pessoal
        pessoal = Qualificador(
            num_qualificador='2.0',
            dsc_qualificador='PESSOAL',
            cod_qualificador_pai=despesas.seq_qualificador
        )
        session.add(pessoal)
        session.flush()
        
        # Despesas de pessoal
        despesas_pessoal = [
            ('2.0.1', 'FOLHA'),
            ('2.0.2', 'PASEP')
        ]
        
        for num, desc in despesas_pessoal:
            qualif = Qualificador(
                num_qualificador=num,
                dsc_qualificador=desc,
                cod_qualificador_pai=pessoal.seq_qualificador
            )
            session.add(qualif)
        
        # Nível 2 - Serviço da Dívida
        servico_divida = Qualificador(
            num_qualificador='2.1',
            dsc_qualificador='SERVIÇO DA DÍVIDA',
            cod_qualificador_pai=despesas.seq_qualificador
        )
        session.add(servico_divida)
        session.flush()
        
        # Adicionar DÍVIDAS e PRECATÓRIOS
        dividas_list = [
            ('2.1.1', 'DÍVIDAS'),
            ('2.1.2', 'PRECATÓRIOS')
        ]
        
        for num, desc in dividas_list:
            qualif = Qualificador(
                num_qualificador=num,
                dsc_qualificador=desc,
                cod_qualificador_pai=servico_divida.seq_qualificador
            )
            session.add(qualif)
        
        # Nível 2 - Custeio - Cota Financeira
        custeio = Qualificador(
            num_qualificador='2.2',
            dsc_qualificador='CUSTEIO - COTA FINANCEIRA',
            cod_qualificador_pai=despesas.seq_qualificador
        )
        session.add(custeio)
        session.flush()
        
        # Adicionar CUSTEIO
        custeio_item = Qualificador(
            num_qualificador='2.2.1',
            dsc_qualificador='CUSTEIO',
            cod_qualificador_pai=custeio.seq_qualificador
        )
        session.add(custeio_item)
        
        # Nível 2 - Investimento - Cota Financeira
        investimento = Qualificador(
            num_qualificador='2.3',
            dsc_qualificador='INVESTIMENTO - COTA FINANCEIRA',
            cod_qualificador_pai=despesas.seq_qualificador
        )
        session.add(investimento)
        session.flush()
        
        # Adicionar INVESTIMENTO + AUMENTO DE CAPITAL
        investimento_item = Qualificador(
            num_qualificador='2.3.1',
            dsc_qualificador='INVESTIMENTO + AUMENTO DE CAPITAL',
            cod_qualificador_pai=investimento.seq_qualificador
        )
        session.add(investimento_item)
        
        # Nível 2 - Encargos Gerais
        encargos = Qualificador(
            num_qualificador='2.4',
            dsc_qualificador='ENCARGOS GERAIS',
            cod_qualificador_pai=despesas.seq_qualificador
        )
        session.add(encargos)
        session.flush()
        
        # Encargos específicos
        encargos_list = [
            ('2.4.1', 'REPASSE MUNICÍPIOS'),
            ('2.4.2', 'REPASSE FUNDEB'),
            ('2.4.3', 'SAÚDE 12%'),
            ('2.4.4', 'EDUCAÇÃO 5%'),
            ('2.4.5', 'PODERES')
        ]
        
        for num, desc in encargos_list:
            qualif = Qualificador(
                num_qualificador=num,
                dsc_qualificador=desc,
                cod_qualificador_pai=encargos.seq_qualificador
            )
            session.add(qualif)
        
        # Nível 2 - Restos a Pagar
        restos_pagar = Qualificador(
            num_qualificador='2.5',
            dsc_qualificador='RESTOS A PAGAR',
            cod_qualificador_pai=despesas.seq_qualificador
        )
        session.add(restos_pagar)
        session.flush()
        
        # Restos a pagar específicos
        restos_list = [
            ('2.5.1', 'RESTOS A PAGAR TESOURO e DEMAIS'),
            ('2.5.2', 'FECOEP - RESTOS A PAGAR - FONTE 761')
        ]
        
        for num, desc in restos_list:
            qualif = Qualificador(
                num_qualificador=num,
                dsc_qualificador=desc,
                cod_qualificador_pai=restos_pagar.seq_qualificador
            )
            session.add(qualif)

    session.commit()

    # Função auxiliar para encontrar qualificador por descrição
    def encontrar_qualificador(descricao):
        return Qualificador.query.filter(func.lower(Qualificador.dsc_qualificador) == func.lower(descricao)).first()

    # Real data for 2025 (Receitas)
    receitas_2025 = {
        'IR': [90000.00, 52000.00, 53000.00, 54000.00, 55000.00, 56000.00, 57000.00, 58000.00, 59000.00, 60000.00, 61000.00, 62000.00],
        'IPVA': [250000.00, 60000.00, 45000.00, 40000.00, 35000.00, 30000.00, 28000.00, 26000.00, 24000.00, 22000.00, 20000.00, 18000.00],  # arrecadação alta no início do ano
        'ITCMD': [8000.00, 8500.00, 8200.00, 7800.00, 8000.00, 8500.00, 8700.00, 9000.00, 8800.00, 8700.00, 8600.00, 8900.00],
        'ICMS': [700000.00, 710000.00, 720000.00, 715000.00, 725000.00, 730000.00, 735000.00, 740000.00, 745000.00, 750000.00, 755000.00, 760000.00],
        'FECOEP': [21178.94, 36524.47, 35987.48, 39252.47, 39307.61, 37356.79, 37044.59, 39004.69, 38919.40, 38931.95, 44438.52, 48658.61],
        'FPE': [700000.00, 710000.00, 720000.00, 730000.00, 740000.00, 750000.00, 760000.00, 770000.00, 780000.00, 790000.00, 800000.00, 810000.00],
        'ROYALTIES': [8000.00, 8500.00, 9000.00, 9500.00, 9000.00, 8500.00, 8000.00, 9500.00, 10000.00, 10500.00, 10000.00, 9500.00],
        'APLICAÇÕES FINANCEIRAS': [5000.00, 5200.00, 5300.00, 5500.00, 5600.00, 5800.00, 5900.00, 6000.00, 6200.00, 6400.00, 6500.00, 6700.00],
        'DEMAIS RECEITAS': [100000.00, 105000.00, 110000.00, 115000.00, 120000.00, 125000.00, 130000.00, 135000.00, 140000.00, 145000.00, 150000.00, 155000.00]
    }

    # Create 2024 data (similar patterns but different values)
    receitas_2024 = {
        'IR': [78500.23, 175432.15, 102456.78, 115689.45, 82345.67, 105789.34, 95234.78, 89765.43, 84567.89, 85234.56, 51789.34, 83567.89],
        'IPVA': [93456.78, 43567.89, 54234.56, 60987.34, 71234.56, 66234.56, 72345.67, 53456.78, 44234.56, 36789.45, 23678.90, 19234.56],
        'ITCMD': [8345.67, 6234.56, 4123.45, 3945.67, 4023.45, 5678.90, 4612.34, 11345.67, 7234.56, 7945.67, 4178.90, 8012.34],
        'ICMS': [645678.90, 665234.56, 576789.45, 583456.78, 582345.67, 585678.90, 557890.12, 592345.67, 572345.67, 595678.90, 665890.12, 692345.67],
        'FECOEP': [37123.45, 32890.12, 32456.78, 35345.67, 35456.78, 33678.90, 33390.12, 35123.45, 35067.89, 35078.90, 40012.34, 43789.45],
        'FPE': [649234.56, 889567.89, 582345.67, 589012.34, 753456.78, 733234.56, 469789.23, 620890.12, 506789.45, 537234.56, 694567.89, 778890.12],
        'ROYALTIES': [7123.45, 7845.67, 9456.78, 8067.89, 8190.12, 3195.23, 4597.89, 12089.34, 6878.90, 6005.67, 7067.89, 8034.56],
        'APLICAÇÕES FINANCEIRAS': [6208.90, 5763.45, 5029.34, 4179.89, 3272.67, 4063.45, 3211.23, 2453.67, 2017.89, 7856.78, 6703.45, 4233.89],
        'DEMAIS RECEITAS': [238194.12, 275768.90, 112289.34, 179055.67, 113601.89, 75102.90, 67796.90, 74420.45, 56952.45, 66895.67, 57826.67, 144493.12]
    }

    # Despesas 2025
    despesas_2025 = {
        'REPASSE MUNICÍPIOS': [420000.00, 410000.00, 430000.00, 440000.00, 435000.00, 450000.00, 455000.00, 460000.00, 470000.00, 480000.00, 490000.00, 500000.00],
        'REPASSE FUNDEB': [362906.70, 341543.95, 250028.96, 243188.98, 284470.31, 293335.05, 218522.18, 257860.50, 227197.00, 237250.65, 283180.29, 308261.00],
        'SAÚDE 12%': [134591.16, 186912.35, 160623.47, 190017.82, 172867.54, 166268.08, 166268.08, 166268.08, 166268.08, 166268.08, 166268.08, 166268.08],
        'EDUCAÇÃO 5%': [8363.08, 31280.92, 23021.76, 47514.74, 51380.41, 74200.27, 74200.27, 74200.27, 74200.27, 74200.27, 74200.27, 74200.27],
        'PODERES': [190000.00, 195000.00, 200000.00, 205000.00, 210000.00, 215000.00, 220000.00, 225000.00, 230000.00, 235000.00, 240000.00, 245000.00],
        'PASEP': [20000.00, 21000.00, 20500.00, 21500.00, 22000.00, 22500.00, 23000.00, 23500.00, 24000.00, 24500.00, 25000.00, 25500.00],
        'PRECATÓRIOS': [10000.00, 9000.00, 8500.00, 8000.00, 7500.00, 7000.00, 6500.00, 6000.00, 5500.00, 5000.00, 4500.00, 4000.00],
        'FOLHA': [520000.00, 525000.00, 530000.00, 535000.00, 540000.00, 545000.00, 550000.00, 555000.00, 560000.00, 565000.00, 570000.00, 580000.00],
        'CUSTEIO': [90000.00, 95000.00, 97000.00, 99000.00, 100000.00, 102000.00, 104000.00, 106000.00, 108000.00, 110000.00, 112000.00, 115000.00],
        'INVESTIMENTO + AUMENTO DE CAPITAL': [12649.53, 37947.62, 39946.24, 31515.99, 33937.78, 33507.31, 33507.31, 33507.31, 33507.31, 33507.31, 33507.31, 33507.31],
        'RESTOS A PAGAR TESOURO e DEMAIS': [60000.00, 58000.00, 56000.00, 54000.00, 52000.00, 50000.00, 48000.00, 46000.00, 44000.00, 42000.00, 40000.00, 38000.00],
        'FECOEP - RESTOS A PAGAR - FONTE 761': [47619.03, 35725.58, 25736.73, 24921.51, 23199.49, 22334.29, 23075.21, 23341.64, 24921.83, 25914.72, 25914.72, 25914.72]
    }

    # Create 2024 despesas (similar patterns but different values)
    despesas_2024 = {
        'REPASSE MUNICÍPIOS': [176939.18, 205865.61, 183800.92, 169749.63, 180234.34, 230287.98, 180435.72, 179580.35, 170128.42, 172435.10, 183250.34, 188665.34],
        'REPASSE FUNDEB': [236616.03, 307389.56, 225026.06, 218870.08, 256023.28, 264001.55, 196669.96, 232074.45, 204477.30, 213525.58, 254862.26, 277434.90],
        'SAÚDE 12%': [121132.04, 168221.12, 144561.12, 171016.04, 155580.79, 149641.27, 149641.27, 149641.27, 149641.27, 149641.27, 149641.27, 149641.27],
        'EDUCAÇÃO 5%': [7526.77, 28152.83, 20719.58, 42763.27, 46242.37, 66780.24, 66780.24, 66780.24, 66780.24, 66780.24, 66780.24, 66780.24],
        'PODERES': [144052.30, 151945.70, 133148.58, 135801.71, 136235.30, 133071.91, 133071.91, 133071.91, 133071.91, 133071.91, 133071.91, 262779.43],
        'PASEP': [14051.15, 16082.89, 14296.30, 12025.06, 13684.17, 13713.73, 13721.91, 10790.96, 12517.62, 11080.68, 11540.93, 13275.10],
        'PRECATÓRIOS': [132177.86, 67232.13, 16088.88, 8156.21, 8591.47, 8418.41, 297.40, 297.40, 297.40, 387.38, 387.38, 214265.98],
        'FOLHA': [365341.30, 373770.09, 366725.28, 390282.00, 402501.66, 382708.78, 378607.07, 381659.28, 379479.69, 378773.15, 379673.49, 404663.11],
        'CUSTEIO': [20511.38, 121661.03, 92421.00, 70476.48, 99894.13, 103500.00, 103500.00, 103500.00, 103500.00, 103500.00, 103500.00, 85500.00],
        'INVESTIMENTO + AUMENTO DE CAPITAL': [11384.58, 34152.86, 35951.62, 28364.39, 30544.00, 30156.58, 30156.58, 30156.58, 30156.58, 30156.58, 30156.58, 30156.58],
        'RESTOS A PAGAR TESOURO e DEMAIS': [164241.60, 111371.66, 67278.49, 41591.37, 27623.59, 64912.10, 64912.10, 64912.10, 64912.10, 64912.10, 0.00, 0.00],
        'FECOEP - RESTOS A PAGAR - FONTE 761': [42857.13, 32153.02, 23163.06, 22429.36, 20879.54, 20100.86, 20767.69, 21007.48, 22429.65, 23323.25, 23323.25, 23323.25]
    }

    # Add realistic seed data based on actual values
    if not Lancamento.query.first():
        tipo_entrada = TipoLancamento.query.filter_by(dsc_tipo_lancamento='Entrada').first()
        
        # Add 2025 receitas
        for origem_nome, valores in receitas_2025.items():
            origem = OrigemLancamento.query.filter_by(dsc_origem_lancamento=origem_nome).first()
            qualificador = encontrar_qualificador(origem_nome)
            if origem and qualificador:
                for month, valor in enumerate(valores, 1):
                    month_date = date(2025, month, 15)
                    session.add(Lancamento(
                        dat_lancamento=month_date,
                        seq_qualificador=qualificador.seq_qualificador,
                        val_lancamento=valor * 1000,  # Convert to thousands
                        cod_tipo_lancamento=tipo_entrada.cod_tipo_lancamento,
                        cod_origem_lancamento=origem.cod_origem_lancamento,
                        ind_origem='M',
                        cod_pessoa_inclusao=1
                    ))

        # Add 2024 receitas
        for origem_nome, valores in receitas_2024.items():
            origem = OrigemLancamento.query.filter_by(dsc_origem_lancamento=origem_nome).first()
            qualificador = encontrar_qualificador(origem_nome)
            if origem and qualificador:
                for month, valor in enumerate(valores, 1):
                    month_date = date(2024, month, 15)
                    session.add(Lancamento(
                        dat_lancamento=month_date,
                        seq_qualificador=qualificador.seq_qualificador,
                        val_lancamento=valor * 1000,  # Convert to thousands
                        cod_tipo_lancamento=tipo_entrada.cod_tipo_lancamento,
                        cod_origem_lancamento=origem.cod_origem_lancamento,
                        ind_origem='M',
                        cod_pessoa_inclusao=1
                    ))

        # Add saídas (despesas) baseadas nos órgãos de pagamento
        tipo_saida = TipoLancamento.query.filter_by(dsc_tipo_lancamento='Saída').first()
        if tipo_saida:
            # Add 2025 despesas como lançamentos de saída
            for orgao_nome, valores in despesas_2025.items():
                qualificador = encontrar_qualificador(orgao_nome)
                # Use a origem padrão para despesas (pode ser a primeira disponível)
                origem_padrao = OrigemLancamento.query.first()
                if qualificador and origem_padrao:
                    for month, valor in enumerate(valores, 1):
                        if valor > 0:  # Skip zero values
                            month_date = date(2025, month, 15)
                            session.add(Lancamento(
                                dat_lancamento=month_date,
                                seq_qualificador=qualificador.seq_qualificador,
                                val_lancamento=-valor * 1000,  # Negative for expenses
                                cod_tipo_lancamento=tipo_saida.cod_tipo_lancamento,
                                cod_origem_lancamento=origem_padrao.cod_origem_lancamento,
                                ind_origem='M',
                                cod_pessoa_inclusao=1
                            ))

            # Add 2024 despesas como lançamentos de saída
            for orgao_nome, valores in despesas_2024.items():
                qualificador = encontrar_qualificador(orgao_nome)
                origem_padrao = OrigemLancamento.query.first()
                if qualificador and origem_padrao:
                    for month, valor in enumerate(valores, 1):
                        if valor > 0:  # Skip zero values
                            month_date = date(2024, month, 15)
                            session.add(Lancamento(
                                dat_lancamento=month_date,
                                seq_qualificador=qualificador.seq_qualificador,
                                val_lancamento=-valor * 1000,  # Negative for expenses
                                cod_tipo_lancamento=tipo_saida.cod_tipo_lancamento,
                                cod_origem_lancamento=origem_padrao.cod_origem_lancamento,
                                ind_origem='M',
                                cod_pessoa_inclusao=1
                            ))

    # Add realistic pagamentos (despesas)
    if not Pagamento.query.first():
        # Add 2025 despesas
        for orgao_nome, valores in despesas_2025.items():
            orgao = Orgao.query.filter_by(nom_orgao=orgao_nome).first()
            if orgao:
                for month, valor in enumerate(valores, 1):
                    if valor > 0:  # Skip zero values
                        month_date = date(2025, month, 15)
                        session.add(Pagamento(
                            dat_pagamento=month_date,
                            cod_orgao=orgao.cod_orgao,
                            val_pagamento=valor * 1000,  # Convert to thousands
                            dsc_pagamento=f'Despesa {orgao_nome} - {calendar.month_name[month]} 2025'
                        ))

        # Add 2024 despesas
        for orgao_nome, valores in despesas_2024.items():
            orgao = Orgao.query.filter_by(nom_orgao=orgao_nome).first()
            if orgao:
                for month, valor in enumerate(valores, 1):
                    if valor > 0:  # Skip zero values
                        month_date = date(2024, month, 15)
                        session.add(Pagamento(
                            dat_pagamento=month_date,
                            cod_orgao=orgao.cod_orgao,
                            val_pagamento=valor * 1000,  # Convert to thousands
                            dsc_pagamento=f'Despesa {orgao_nome} - {calendar.month_name[month]} 2024'
                        ))

    # Add example mappings
    try:
        if not Mapeamento.query.first():
            # Mapeamentos de Receita
            icms_qual = encontrar_qualificador('ICMS')
            if icms_qual:
                session.add(Mapeamento(
                    seq_qualificador=icms_qual.seq_qualificador,
                    dsc_mapeamento='Mapeamento ICMS - Análise de Arrecadação',
                    txt_condicao='abc != CLASSIFICADOR(\'CAMPO\')',
                    ind_status='A'
                ))
            
            fpe_qual = encontrar_qualificador('FPE')
            if fpe_qual:
                session.add(Mapeamento(
                    seq_qualificador=fpe_qual.seq_qualificador,
                    dsc_mapeamento='Mapeamento FPE - Transferências Federais',
                    txt_condicao='abc != CLASSIFICADOR(\'CAMPO\')',
                    ind_status='A'
                ))
        
        # Mapeamentos de Despesa
        folha_qual = encontrar_qualificador('FOLHA')
        if folha_qual:
            session.add(Mapeamento(
                seq_qualificador=folha_qual.seq_qualificador,
                dsc_mapeamento='Mapeamento Folha de Pagamento',
                txt_condicao='abc != CLASSIFICADOR(\'CAMPO\')',
                ind_status='A'
            ))
        
        custeio_qual = encontrar_qualificador('CUSTEIO')
        if custeio_qual:
            session.add(Mapeamento(
                seq_qualificador=custeio_qual.seq_qualificador,
                dsc_mapeamento='Mapeamento Custeio Administrativo',
                txt_condicao='abc != CLASSIFICADOR(\'CAMPO\')',
                ind_status='A'
            ))
        
        # Mapeamento inativo de exemplo
        repasse_mun_qual = encontrar_qualificador('REPASSE MUNICÍPIOS')
        if repasse_mun_qual:
            session.add(Mapeamento(
                seq_qualificador=repasse_mun_qual.seq_qualificador,
                dsc_mapeamento='Mapeamento Repasse Municípios - Análise Suspensa',
                txt_condicao='abc != CLASSIFICADOR(\'CAMPO\')',
                ind_status='I'
            ))

    except Exception as e:
        print(f"Erro ao criar mapeamentos: {e}")
        pass  # Continue even if mappings fail

    # Cenário de exemplo com ajustes mensais
    if not Cenario.query.first():
        cenario_base = Cenario(nom_cenario='Base', dsc_cenario='Cenário inicial')
        session.add(cenario_base)
        session.flush()
        icms_qual = encontrar_qualificador('ICMS')
        folha_qual = encontrar_qualificador('FOLHA')
        ano_atual = date.today().year
        for mes in range(1, 13):
            if icms_qual:
                session.add(CenarioAjusteMensal(
                    seq_cenario=cenario_base.seq_cenario,
                    seq_qualificador=icms_qual.seq_qualificador,
                    ano=ano_atual,
                    mes=mes,
                    cod_tipo_ajuste='P',
                    val_ajuste=5,
                ))
            if folha_qual:
                session.add(CenarioAjusteMensal(
                    seq_cenario=cenario_base.seq_cenario,
                    seq_qualificador=folha_qual.seq_qualificador,
                    ano=ano_atual,
                    mes=mes,
                    cod_tipo_ajuste='P',
                    val_ajuste=-2,
                ))

    # Add realistic data for Conferencia table based on the image provided
    if not Conferencia.query.first():
        # Data based on the conference screen image
        conferencia_data = [
            {
                'data': date(2025, 6, 17),
                'saldo_anterior': 568262058.81,
                'liberacoes': 0.00,
                'conf_liberacoes': 0.00,
                'soma_anter_liberacoes': 568262058.81,
                'pagamentos': 0.00,
                'conf_pagamentos': 0.00,
                'saldo_final': 568262058.81
            },
            {
                'data': date(2025, 6, 11),
                'saldo_anterior': 537524274.27,
                'liberacoes': 103672302.26,
                'conf_liberacoes': 103672302.26,
                'soma_anter_liberacoes': 578196242.69,
                'pagamentos': 16322223.28,
                'conf_pagamentos': 16322223.28,
                'saldo_final': 565242020.81
            },
            {
                'data': date(2025, 6, 10),
                'saldo_anterior': 519605479.27,
                'liberacoes': 81824500.48,
                'conf_liberacoes': 81824500.48,
                'soma_anter_liberacoes': 537524274.27,
                'pagamentos': 34971506.42,
                'conf_pagamentos': 34971506.42,
                'saldo_final': 537524274.27
            },
            {
                'data': date(2025, 6, 9),
                'saldo_anterior': 503024713.99,
                'liberacoes': 13733378.04,
                'conf_liberacoes': 13733378.04,
                'soma_anter_liberacoes': 394277502.03,
                'pagamentos': 91375376.76,
                'conf_pagamentos': 91375376.76,
                'saldo_final': 384596331.28
            },
            {
                'data': date(2025, 6, 6),
                'saldo_anterior': 510024713.99,
                'liberacoes': 0.00,
                'conf_liberacoes': 0.00,
                'soma_anter_liberacoes': 381024713.99,
                'pagamentos': 0.00,
                'conf_pagamentos': 0.00,
                'saldo_final': 381024713.99
            },
            {
                'data': date(2025, 6, 3),
                'saldo_anterior': 511024713.99,
                'liberacoes': 0.00,
                'conf_liberacoes': 0.00,
                'soma_anter_liberacoes': 381024713.99,
                'pagamentos': 0.00,
                'conf_pagamentos': 0.00,
                'saldo_final': 381024713.99
            },
            {
                'data': date(2025, 5, 7),
                'saldo_anterior': 497706837.99,
                'liberacoes': 315481715.45,
                'conf_liberacoes': 222029719.45,
                'soma_anter_liberacoes': 640176142.26,
                'pagamentos': 271854879.64,
                'conf_pagamentos': 271854879.64,
                'saldo_final': 497528837.99
            },
            {
                'data': date(2025, 4, 4),
                'saldo_anterior': 616759.50,
                'liberacoes': 78331415.91,
                'conf_liberacoes': 78331415.91,
                'soma_anter_liberacoes': 640176176.35,
                'pagamentos': 62376142.28,
                'conf_pagamentos': 62376142.28,
                'saldo_final': 597528837.47
            },
            {
                'data': date(2025, 4, 3),
                'saldo_anterior': 542017684.77,
                'liberacoes': 131773250.00,
                'conf_liberacoes': 131773250.00,
                'soma_anter_liberacoes': 434301447.30,
                'pagamentos': 53317634.39,
                'conf_pagamentos': 53317634.39,
                'saldo_final': 410624476.94
            },
            {
                'data': date(2025, 4, 2),
                'saldo_anterior': 502093936.77,
                'liberacoes': 131738200.00,
                'conf_liberacoes': 131738200.00,
                'soma_anter_liberacoes': 436350547.30,
                'pagamentos': 179956820.39,
                'conf_pagamentos': 179956820.39,
                'saldo_final': 473053165.04
            },
            {
                'data': date(2025, 3, 2),
                'saldo_anterior': 524803174.32,
                'liberacoes': 105302341.10,
                'conf_liberacoes': 105302341.10,
                'soma_anter_liberacoes': 430050547.30,
                'pagamentos': 72470350.48,
                'conf_pagamentos': 72470350.48,
                'saldo_final': 553033165.04
            },
            {
                'data': date(2025, 3, 1),
                'saldo_anterior': 524803174.32,
                'liberacoes': 0.00,
                'conf_liberacoes': 0.00,
                'soma_anter_liberacoes': 524803174.32,
                'pagamentos': 0.00,
                'conf_pagamentos': 0.00,
                'saldo_final': 524803174.32
            },
            {
                'data': date(2025, 2, 1),
                'saldo_anterior': 524803174.32,
                'liberacoes': 0.00,
                'conf_liberacoes': 0.00,
                'soma_anter_liberacoes': 524803174.32,
                'pagamentos': 0.00,
                'conf_pagamentos': 0.00,
                'saldo_final': 524803174.32
            }
        ]
        
        for dados in conferencia_data:
            conferencia = Conferencia(
                dat_conferencia=dados['data'],
                val_saldo_anterior=dados['saldo_anterior'],
                val_liberacoes=dados['liberacoes'],
                val_conf_liberacoes=dados['conf_liberacoes'],
                val_soma_anter_liberacoes=dados['soma_anter_liberacoes'],
                val_pagamentos=dados['pagamentos'],
                val_conf_pagamentos=dados['conf_pagamentos'],
                val_saldo_final=dados['saldo_final']
            )
            session.add(conferencia)

    session.commit()

