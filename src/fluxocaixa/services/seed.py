from datetime import date, timedelta
from sqlalchemy import func, and_
import calendar
from ..models import (
    Mapeamento,
    Pagamento,
    Lancamento,
    Qualificador,
    Orgao,
    OrigemLancamento,
    TipoLancamento,

    Conferencia,
    AlertaGerado,
    SaldoConta,
    SimuladorCenario,
    CenarioReceita,
    CenarioDespesa,
    CenarioReceitaAjuste,
    CenarioDespesaAjuste,
    Loa,
)
from ..models.base import db
from ..models import ContaBancaria

def seed_data(session=None):
    """Populate the database with some basic records for testing."""
    session = session or db.session
    # Clear existing data to ensure a clean slate for new values
    try:
        session.query(Mapeamento).delete()
    except Exception:
        # Table might not exist yet
        pass
    try:
        session.query(Loa).delete()
    except Exception:
        pass
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
            OrigemLancamento(dsc_origem_lancamento='Manual', ind_status='A'),
            OrigemLancamento(dsc_origem_lancamento='Automático', ind_status='A'),
            OrigemLancamento(dsc_origem_lancamento='Importado', ind_status='A'),
        ])

    if not Orgao.query.first():
        session.add_all([
            Orgao(nom_orgao='Secretaria de Saúde'),
            Orgao(nom_orgao='Secretaria de Educação'),
            Orgao(nom_orgao='Secretaria de Fazenda'),
            Orgao(nom_orgao='Secretaria de Administração'),
            Orgao(nom_orgao='Secretaria de Infraestrutura'),
            Orgao(nom_orgao='Secretaria de Segurança Pública'),
            Orgao(nom_orgao='Universidade Estadual'),
            Orgao(nom_orgao='Assembleia Legislativa'),
            Orgao(nom_orgao='Tribunal de Contas'),
            Orgao(nom_orgao='Tribunal de Justiça'),
            Orgao(nom_orgao='Ministério Público'),
            Orgao(nom_orgao='Defensoria Pública'),
        ])

    # Populate Qualificadores (estrutura hierárquica)
    if not Qualificador.query.first():
        # Criar estrutura hierárquica baseada na imagem
 
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

    # Create 2023 data (historical patterns)
    receitas_2023 = {
        'IR': [72345.12, 160234.56, 95678.90, 108456.78, 76234.56, 98567.89, 88234.56, 82345.67, 78234.56, 79012.34, 47567.89, 77234.56],
        'IPVA': [86234.56, 40123.45, 49876.54, 56234.56, 65678.90, 61234.56, 67345.67, 49876.54, 40987.65, 33456.78, 21234.56, 17654.32],
        'ITCMD': [7654.32, 5678.90, 3765.43, 3612.34, 3678.90, 5234.56, 4234.56, 10234.56, 6678.90, 7234.56, 3812.34, 7345.67],
        'ICMS': [598765.43, 615678.90, 534567.89, 540234.56, 539876.54, 542345.67, 517234.56, 548765.43, 530234.56, 551234.56, 616789.01, 641234.56],
        'FECOEP': [34234.56, 30123.45, 29876.54, 32456.78, 32567.89, 30912.34, 30678.90, 32234.56, 32123.45, 32134.56, 36789.01, 40234.56],
        'FPE': [601234.56, 823456.78, 539876.54, 545678.90, 698765.43, 679876.54, 435678.90, 575234.56, 469876.54, 497654.32, 643456.78, 721234.56],
        'ROYALTIES': [6567.89, 7234.56, 8765.43, 7456.78, 7567.89, 2934.56, 4234.56, 11123.45, 6345.67, 5534.56, 6512.34, 7412.34],
        'APLICAÇÕES FINANCEIRAS': [5734.56, 5312.34, 4634.56, 3856.78, 3012.34, 3745.67, 2956.78, 2267.89, 1856.78, 7234.56, 6178.90, 3912.34],
        'DEMAIS RECEITAS': [220456.78, 255234.56, 103876.54, 165678.90, 105234.56, 69456.78, 62678.90, 68876.54, 52678.90, 61789.01, 53456.78, 133876.54]
    }

    # Create 2022 data (older historical patterns)
    receitas_2022 = {
        'IR': [66234.56, 147890.12, 88456.78, 100234.56, 70123.45, 91234.56, 81456.78, 76234.56, 72123.45, 73456.78, 43876.54, 71234.56],
        'IPVA': [79876.54, 37234.56, 46123.45, 52345.67, 60876.54, 56789.01, 62456.78, 46234.56, 37876.54, 30876.54, 19567.89, 16234.56],
        'ITCMD': [7012.34, 5234.56, 3456.78, 3312.34, 3387.65, 4812.34, 3912.34, 9456.78, 6145.67, 6678.90, 3512.34, 6789.01],
        'ICMS': [554321.09, 570987.65, 496234.56, 501876.54, 500987.65, 503456.78, 480123.45, 509876.54, 492345.67, 511876.54, 572345.67, 595678.90],
        'FECOEP': [31456.78, 27654.32, 27456.78, 29876.54, 29987.65, 28456.78, 28234.56, 29678.90, 29567.89, 29578.90, 33876.54, 37012.34],
        'FPE': [557234.56, 763456.78, 501234.56, 506789.01, 648234.56, 630987.65, 404567.89, 533876.54, 436234.56, 461876.54, 597234.56, 669876.54],
        'ROYALTIES': [6045.67, 6678.90, 8123.45, 6876.54, 6987.65, 2712.34, 3912.34, 10267.89, 5867.89, 5112.34, 6012.34, 6845.67],
        'APLICAÇÕES FINANCEIRAS': [5289.01, 4901.23, 4278.90, 3567.89, 2778.90, 3456.78, 2734.56, 2089.01, 1712.34, 6678.90, 5712.34, 3612.34],
        'DEMAIS RECEITAS': [204234.56, 236456.78, 96234.56, 153456.78, 97654.32, 64234.56, 58123.45, 63876.54, 48876.54, 57234.56, 49567.89, 124234.56]
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

    # Create 2023 despesas (historical patterns)
    despesas_2023 = {
        'REPASSE MUNICÍPIOS': [163876.54, 190567.89, 170234.56, 157234.56, 166876.54, 213456.78, 167123.45, 166234.56, 157567.89, 159876.54, 169876.54, 174567.89],
        'REPASSE FUNDEB': [219234.56, 284876.54, 208567.89, 202876.54, 237234.56, 244567.89, 182123.45, 214876.54, 189456.78, 197876.54, 236123.45, 257012.34],
        'SAÚDE 12%': [112234.56, 155876.54, 133876.54, 158345.67, 143876.54, 138567.89, 138567.89, 138567.89, 138567.89, 138567.89, 138567.89, 138567.89],
        'EDUCAÇÃO 5%': [6976.54, 26087.65, 19198.76, 39609.87, 42854.32, 61876.54, 61876.54, 61876.54, 61876.54, 61876.54, 61876.54, 61876.54],
        'PODERES': [133456.78, 140876.54, 123345.67, 125789.01, 126189.76, 123234.56, 123234.56, 123234.56, 123234.56, 123234.56, 123234.56, 243456.78],
        'PASEP': [13012.34, 14876.54, 13234.56, 11134.56, 12678.90, 12705.67, 12713.45, 9998.76, 11598.76, 10267.89, 10693.45, 12298.76],
        'PRECATÓRIOS': [122456.78, 62234.56, 14898.76, 7556.78, 7959.87, 7798.76, 275.67, 275.67, 275.67, 358.90, 358.90, 198456.78],
        'FOLHA': [338567.89, 346345.67, 339876.54, 361567.89, 372876.54, 354567.89, 350765.43, 353598.76, 351578.90, 350923.45, 351756.78, 374876.54],
        'CUSTEIO': [19012.34, 112678.90, 85654.32, 65234.56, 92567.89, 95876.54, 95876.54, 95876.54, 95876.54, 95876.54, 95876.54, 79234.56],
        'INVESTIMENTO + AUMENTO DE CAPITAL': [10543.21, 31629.63, 33283.17, 26263.17, 28279.30, 27920.70, 27920.70, 27920.70, 27920.70, 27920.70, 27920.70, 27920.70],
        'RESTOS A PAGAR TESOURO e DEMAIS': [152123.45, 103234.56, 62345.67, 38534.56, 25598.76, 60123.45, 60123.45, 60123.45, 60123.45, 60123.45, 0.00, 0.00],
        'FECOEP - RESTOS A PAGAR - FONTE 761': [39678.90, 29765.43, 21456.78, 20776.54, 19341.23, 18619.87, 19237.65, 19459.87, 20776.67, 21604.32, 21604.32, 21604.32]
    }

    # Create 2022 despesas (older historical patterns)
    despesas_2022 = {
        'REPASSE MUNICÍPIOS': [151876.54, 176789.01, 157876.54, 145876.54, 154765.43, 197876.54, 155012.34, 154123.45, 146234.56, 148234.56, 157456.78, 161876.54],
        'REPASSE FUNDEB': [203234.56, 264012.34, 193456.78, 188123.45, 220012.34, 226876.54, 168876.54, 199345.67, 175678.90, 183567.89, 218876.54, 238234.56],
        'SAÚDE 12%': [104012.34, 144567.89, 124234.56, 146876.54, 133456.78, 128567.89, 128567.89, 128567.89, 128567.89, 128567.89, 128567.89, 128567.89],
        'EDUCAÇÃO 5%': [6467.89, 24187.65, 17809.87, 36734.56, 39745.67, 57376.54, 57376.54, 57376.54, 57376.54, 57376.54, 57376.54, 57376.54],
        'PODERES': [123765.43, 130567.89, 114345.67, 116567.89, 116945.67, 114234.56, 114234.56, 114234.56, 114234.56, 114234.56, 114234.56, 225678.90],
        'PASEP': [12067.89, 13789.01, 12267.89, 10321.09, 11756.78, 11781.45, 11789.01, 9267.89, 10756.78, 9523.45, 9918.76, 11406.78],
        'PRECATÓRIOS': [113567.89, 57734.56, 13812.34, 7012.34, 7387.65, 7237.65, 255.67, 255.67, 255.67, 332.98, 332.98, 184012.34],
        'FOLHA': [314123.45, 321345.67, 315234.56, 335345.67, 345876.54, 328876.54, 325345.67, 327978.90, 326098.76, 325489.01, 326267.89, 347678.90],
        'CUSTEIO': [17634.56, 104534.56, 79456.78, 60512.34, 85876.54, 88956.78, 88956.78, 88956.78, 88956.78, 88956.78, 88956.78, 73512.34],
        'INVESTIMENTO + AUMENTO DE CAPITAL': [9776.54, 29329.63, 30876.54, 24367.89, 26234.56, 25901.23, 25901.23, 25901.23, 25901.23, 25901.23, 25901.23, 25901.23],
        'RESTOS A PAGAR TESOURO e DEMAIS': [141012.34, 95765.43, 57876.54, 35745.67, 23745.67, 55765.43, 55765.43, 55765.43, 55765.43, 55765.43, 0.00, 0.00],
        'FECOEP - RESTOS A PAGAR - FONTE 761': [36789.01, 27598.76, 19912.34, 19276.54, 17945.67, 17276.54, 17849.87, 18056.78, 19276.67, 20043.21, 20043.21, 20043.21]
    }

    # Map qualifiers to specific accounts for realistic data
    # 1: Conta Única (Tesouro), 2: Judicial, 3: Salario, 4: FPE, 5: Recursos Próprios
    qualificador_conta_map = {
        'ICMS': 1, 'IPVA': 1, 'ITCMD': 1, 'IR': 1, 'DEMAIS RECEITAS': 1,
        'FPE': 4,
        'ROYALTIES': 5, 'FECOEP': 5, 'APLICAÇÕES FINANCEIRAS': 5,
        'FOLHA': 3, 'PASEP': 3,
        'SAÚDE 12%': 1, 'EDUCAÇÃO 5%': 1, 'PODERES': 1, 'REPASSE MUNICÍPIOS': 1,
        'PRECATÓRIOS': 2,
        'CUSTEIO': 1, 'INVESTIMENTO + AUMENTO DE CAPITAL': 1,
        'RESTOS A PAGAR TESOURO e DEMAIS': 1, 'FECOEP - RESTOS A PAGAR - FONTE 761': 5
    }

    # Add realistic seed data based on actual values
    if not Lancamento.query.first():
        tipo_entrada = TipoLancamento.query.filter_by(dsc_tipo_lancamento='Entrada').first()
        origem_manual = OrigemLancamento.query.filter_by(dsc_origem_lancamento='Manual').first()
        
        # Add 2025 receitas
        for origem_nome, valores in receitas_2025.items():
            qualificador = encontrar_qualificador(origem_nome)
            if qualificador and origem_manual:
                # Determine account
                seq_conta = qualificador_conta_map.get(origem_nome, 1) # Default to Treasury
                
                for month, valor in enumerate(valores, 1):
                    month_date = date(2025, month, 15)
                    session.add(Lancamento(
                        dat_lancamento=month_date,
                        seq_qualificador=qualificador.seq_qualificador,
                        val_lancamento=valor * 1000,  # Convert to thousands
                        cod_tipo_lancamento=tipo_entrada.cod_tipo_lancamento,
                        cod_origem_lancamento=origem_manual.cod_origem_lancamento,
                        cod_pessoa_inclusao=1,
                        seq_conta=seq_conta
                    ))

        # Add 2024 receitas
        for origem_nome, valores in receitas_2024.items():
            qualificador = encontrar_qualificador(origem_nome)
            if qualificador and origem_manual:
                # Determine account
                seq_conta = qualificador_conta_map.get(origem_nome, 1) # Default to Treasury

                for month, valor in enumerate(valores, 1):
                    month_date = date(2024, month, 15)
                    session.add(Lancamento(
                        dat_lancamento=month_date,
                        seq_qualificador=qualificador.seq_qualificador,
                        val_lancamento=valor * 1000,  # Convert to thousands
                        cod_tipo_lancamento=tipo_entrada.cod_tipo_lancamento,
                        cod_origem_lancamento=origem_manual.cod_origem_lancamento,
                        cod_pessoa_inclusao=1,
                        seq_conta=seq_conta
                    ))

        # Add 2023 receitas
        for origem_nome, valores in receitas_2023.items():
            qualificador = encontrar_qualificador(origem_nome)
            if qualificador and origem_manual:
                seq_conta = qualificador_conta_map.get(origem_nome, 1)
                for month, valor in enumerate(valores, 1):
                    month_date = date(2023, month, 15)
                    session.add(Lancamento(
                        dat_lancamento=month_date,
                        seq_qualificador=qualificador.seq_qualificador,
                        val_lancamento=valor * 1000,
                        cod_tipo_lancamento=tipo_entrada.cod_tipo_lancamento,
                        cod_origem_lancamento=origem_manual.cod_origem_lancamento,
                        cod_pessoa_inclusao=1,
                        seq_conta=seq_conta
                    ))

        # Add 2022 receitas
        for origem_nome, valores in receitas_2022.items():
            qualificador = encontrar_qualificador(origem_nome)
            if qualificador and origem_manual:
                seq_conta = qualificador_conta_map.get(origem_nome, 1)
                for month, valor in enumerate(valores, 1):
                    month_date = date(2022, month, 15)
                    session.add(Lancamento(
                        dat_lancamento=month_date,
                        seq_qualificador=qualificador.seq_qualificador,
                        val_lancamento=valor * 1000,
                        cod_tipo_lancamento=tipo_entrada.cod_tipo_lancamento,
                        cod_origem_lancamento=origem_manual.cod_origem_lancamento,
                        cod_pessoa_inclusao=1,
                        seq_conta=seq_conta
                    ))

        # Add saídas (despesas) baseadas nos órgãos de pagamento
        tipo_saida = TipoLancamento.query.filter_by(dsc_tipo_lancamento='Saída').first()
        if tipo_saida and origem_manual:
            # Add 2025 despesas como lançamentos de saída
            for orgao_nome, valores in despesas_2025.items():
                qualificador = encontrar_qualificador(orgao_nome)
                if qualificador:
                    # Determine account
                    seq_conta = qualificador_conta_map.get(orgao_nome, 1) # Default to Treasury

                    for month, valor in enumerate(valores, 1):
                        if valor > 0:  # Skip zero values
                            month_date = date(2025, month, 15)
                            session.add(Lancamento(
                                dat_lancamento=month_date,
                                seq_qualificador=qualificador.seq_qualificador,
                                val_lancamento=-valor * 1000,  # Negative for expenses
                                cod_tipo_lancamento=tipo_saida.cod_tipo_lancamento,
                                cod_origem_lancamento=origem_manual.cod_origem_lancamento,
                                cod_pessoa_inclusao=1,
                                seq_conta=seq_conta
                            ))

            # Add 2024 despesas como lançamentos de saída
            for orgao_nome, valores in despesas_2024.items():
                qualificador = encontrar_qualificador(orgao_nome)
                if qualificador:
                    # Determine account
                    seq_conta = qualificador_conta_map.get(orgao_nome, 1) # Default to Treasury

                    for month, valor in enumerate(valores, 1):
                        if valor > 0:  # Skip zero values
                            month_date = date(2024, month, 15)
                            session.add(Lancamento(
                                dat_lancamento=month_date,
                                seq_qualificador=qualificador.seq_qualificador,
                                val_lancamento=-valor * 1000,  # Negative for expenses
                                cod_tipo_lancamento=tipo_saida.cod_tipo_lancamento,
                                cod_origem_lancamento=origem_manual.cod_origem_lancamento,
                                cod_pessoa_inclusao=1,
                                seq_conta=seq_conta
                            ))

            # Add 2023 despesas como lançamentos de saída
            for orgao_nome, valores in despesas_2023.items():
                qualificador = encontrar_qualificador(orgao_nome)
                if qualificador:
                    seq_conta = qualificador_conta_map.get(orgao_nome, 1)
                    for month, valor in enumerate(valores, 1):
                        if valor > 0:
                            month_date = date(2023, month, 15)
                            session.add(Lancamento(
                                dat_lancamento=month_date,
                                seq_qualificador=qualificador.seq_qualificador,
                                val_lancamento=-valor * 1000,
                                cod_tipo_lancamento=tipo_saida.cod_tipo_lancamento,
                                cod_origem_lancamento=origem_manual.cod_origem_lancamento,
                                cod_pessoa_inclusao=1,
                                seq_conta=seq_conta
                            ))

            # Add 2022 despesas como lançamentos de saída
            for orgao_nome, valores in despesas_2022.items():
                qualificador = encontrar_qualificador(orgao_nome)
                if qualificador:
                    seq_conta = qualificador_conta_map.get(orgao_nome, 1)
                    for month, valor in enumerate(valores, 1):
                        if valor > 0:
                            month_date = date(2022, month, 15)
                            session.add(Lancamento(
                                dat_lancamento=month_date,
                                seq_qualificador=qualificador.seq_qualificador,
                                val_lancamento=-valor * 1000,
                                cod_tipo_lancamento=tipo_saida.cod_tipo_lancamento,
                                cod_origem_lancamento=origem_manual.cod_origem_lancamento,
                                cod_pessoa_inclusao=1,
                                seq_conta=seq_conta
                            ))

    # Add realistic pagamentos (despesas) with proper organ and qualifier mapping
    if not Pagamento.query.first():
        # Mapeamento de despesas para órgãos e qualificadores reais
        despesa_para_orgao_e_qual = {
            'REPASSE MUNICÍPIOS': ('Secretaria de Fazenda', 'REPASSE MUNICÍPIOS'),
            'REPASSE FUNDEB': ('Secretaria de Educação', 'REPASSE FUNDEB'),
            'SAÚDE 12%': ('Secretaria de Saúde', 'SAÚDE 12%'),
            'EDUCAÇÃO 5%': ('Secretaria de Educação', 'EDUCAÇÃO 5%'),
            'PODERES': ('Assembleia Legislativa', 'PODERES'),
            'PASEP': ('Secretaria de Administração', 'PASEP'),
            'PRECATÓRIOS': ('Tribunal de Justiça', 'PRECATÓRIOS'),
            'FOLHA': ('Secretaria de Administração', 'FOLHA'),
            'CUSTEIO': ('Secretaria de Administração', 'CUSTEIO'),
            'INVESTIMENTO + AUMENTO DE CAPITAL': ('Secretaria de Infraestrutura', 'INVESTIMENTO + AUMENTO DE CAPITAL'),
            'RESTOS A PAGAR TESOURO e DEMAIS': ('Secretaria de Fazenda', 'RESTOS A PAGAR TESOURO e DEMAIS'),
            'FECOEP - RESTOS A PAGAR - FONTE 761': ('Secretaria de Fazenda', 'FECOEP - RESTOS A PAGAR - FONTE 761'),
            'DÍVIDAS': ('Secretaria de Fazenda', 'DÍVIDAS'),
        }
        
        # Add 2025 despesas
        for despesa_nome, valores in despesas_2025.items():
            if despesa_nome in despesa_para_orgao_e_qual:
                orgao_nome, qualificador_nome = despesa_para_orgao_e_qual[despesa_nome]
                orgao = Orgao.query.filter_by(nom_orgao=orgao_nome).first()
                qualificador = encontrar_qualificador(qualificador_nome)
                
                if orgao:
                    for month, valor in enumerate(valores, 1):
                        if valor > 0:  # Skip zero values
                            month_date = date(2025, month, 15)
                            session.add(Pagamento(
                                dat_pagamento=month_date,
                                cod_orgao=orgao.cod_orgao,
                                seq_qualificador=qualificador.seq_qualificador if qualificador else None,
                                val_pagamento=valor * 1000,  # Convert to thousands
                                dsc_pagamento=f'Despesa {despesa_nome} - {calendar.month_name[month]} 2025'
                            ))

        # Add 2024 despesas
        for despesa_nome, valores in despesas_2024.items():
            if despesa_nome in despesa_para_orgao_e_qual:
                orgao_nome, qualificador_nome = despesa_para_orgao_e_qual[despesa_nome]
                orgao = Orgao.query.filter_by(nom_orgao=orgao_nome).first()
                qualificador = encontrar_qualificador(qualificador_nome)
                
                if orgao:
                    for month, valor in enumerate(valores, 1):
                        if valor > 0:  # Skip zero values
                            month_date = date(2024, month, 15)
                            session.add(Pagamento(
                                dat_pagamento=month_date,
                                cod_orgao=orgao.cod_orgao,
                                seq_qualificador=qualificador.seq_qualificador if qualificador else None,
                                val_pagamento=valor * 1000,  # Convert to thousands
                                dsc_pagamento=f'Despesa {despesa_nome} - {calendar.month_name[month]} 2024'
                            ))

        # Add 2023 despesas
        for despesa_nome, valores in despesas_2023.items():
            if despesa_nome in despesa_para_orgao_e_qual:
                orgao_nome, qualificador_nome = despesa_para_orgao_e_qual[despesa_nome]
                orgao = Orgao.query.filter_by(nom_orgao=orgao_nome).first()
                qualificador = encontrar_qualificador(qualificador_nome)
                
                if orgao:
                    for month, valor in enumerate(valores, 1):
                        if valor > 0:
                            month_date = date(2023, month, 15)
                            session.add(Pagamento(
                                dat_pagamento=month_date,
                                cod_orgao=orgao.cod_orgao,
                                seq_qualificador=qualificador.seq_qualificador if qualificador else None,
                                val_pagamento=valor * 1000,
                                dsc_pagamento=f'Despesa {despesa_nome} - {calendar.month_name[month]} 2023'
                            ))

        # Add 2022 despesas
        for despesa_nome, valores in despesas_2022.items():
            if despesa_nome in despesa_para_orgao_e_qual:
                orgao_nome, qualificador_nome = despesa_para_orgao_e_qual[despesa_nome]
                orgao = Orgao.query.filter_by(nom_orgao=orgao_nome).first()
                qualificador = encontrar_qualificador(qualificador_nome)
                
                if orgao:
                    for month, valor in enumerate(valores, 1):
                        if valor > 0:
                            month_date = date(2022, month, 15)
                            session.add(Pagamento(
                                dat_pagamento=month_date,
                                cod_orgao=orgao.cod_orgao,
                                seq_qualificador=qualificador.seq_qualificador if qualificador else None,
                                val_pagamento=valor * 1000,
                                dsc_pagamento=f'Despesa {despesa_nome} - {calendar.month_name[month]} 2022'
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


    # Old Cenario seed data removed - now using Simulador only


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

    # Seed government bank accounts if none exist
    if not ContaBancaria.query.first():
        contas = [
            # Banco do Brasil - Conta Única do Tesouro
            ContaBancaria(cod_banco='001', num_agencia='0001', num_conta='123456-7', dsc_conta='Conta Única - Tesouro'),
            # Caixa Econômica Federal - Arrecadação ICMS
            ContaBancaria(cod_banco='104', num_agencia='4567', num_conta='00012345-0', dsc_conta='Conta Judicial'),
            # Bradesco - Convênios e Transferências
            ContaBancaria(cod_banco='237', num_agencia='1234', num_conta='98765-4', dsc_conta='Conta Salario'),
            # Itaú - Fundo de Participação dos Estados (FPE)
            ContaBancaria(cod_banco='341', num_agencia='3200', num_conta='556677-8', dsc_conta='Conta de FPE '),
            # Santander - Operações Financeiras
            ContaBancaria(cod_banco='033', num_agencia='9999', num_conta='112233-4', dsc_conta='Contas de Recursos Próprios Vinculados'),
        ]
        session.add_all(contas)
        session.commit()

    # Seed alertas gerados (para demonstração do sistema de alertas)
    if not AlertaGerado.query.first():
        alertas_demo = [
            # Alerta CRITICAL - Despesa de Pessoal
            AlertaGerado(
                dat_processamento=None,  # NULL = sempre visível
                dat_referencia=date.today(),
                mensagem='Limite prudencial (46.2%) atingido. Novas contratações requerem atenção do TCE.',
                categoria='DESPESA_PESSOAL',
                severidade='CRITICAL',
                valor_obtido=46.2,
                valor_esperado=46.0,
            ),
            # Alerta WARNING - Receita
            AlertaGerado(
                dat_processamento=None,  # NULL = sempre visível
                dat_referencia=date(2025, 12, 1),
                mensagem='Queda de arrecadação PPE prevista para Dezembro (-2%) devido à desaceleração econômica.',
                categoria='RECEITA',
                severidade='WARNING',
                valor_obtido=-2.0,
                valor_esperado=0.0,
            ),
            # Alerta INFO - Saldo
            AlertaGerado(
                dat_processamento=None,  # NULL = sempre visível
                dat_referencia=date.today(),
                mensagem='Superávit orçamentário de R$ 1.2M identificado. Considere investimentos estratégicos.',
                categoria='SALDO',
                severidade='INFO',
                valor_obtido=1200000.0,
                valor_esperado=0.0,
            ),
        ]
        session.add_all(alertas_demo)
        session.commit()

    # Seed daily account balances (SaldoConta)
    if not SaldoConta.query.first():
        contas = ContaBancaria.query.filter_by(ind_status='A').all()
        
        if contas:
            # Base initial balances for each account (as of Dec 31, 2021)
            saldos_base = {
                1: 200000000.00,  # Conta Única - Tesouro
                2: 150000000.00,  # Conta Judicial  
                3: 65000000.00,   # Conta Salário
                4: 120000000.00,  # Conta FPE
                5: 75000000.00,   # Recursos Próprios
            }
            
            # Generate daily balances from Jan 1, 2022 to today
            data_inicio = date(2022, 1, 1)
            data_fim = date.today()
            
            # For each account, generate daily balances
            for conta in contas:
                seq_conta = conta.seq_conta
                saldo_atual = saldos_base.get(seq_conta, 100000000.00)
                
                # Iterate through each day
                data_atual = data_inicio
                while data_atual <= data_fim:
                    # Get transactions for this account on this day
                    lancamentos_dia = session.query(Lancamento).filter(
                        and_(
                            Lancamento.seq_conta == seq_conta,
                            Lancamento.dat_lancamento == data_atual
                        )
                    ).all()
                    
                    # Apply transactions to balance
                    for lanc in lancamentos_dia:
                        saldo_atual += float(lanc.val_lancamento)
                    
                    # Create balance record
                    session.add(SaldoConta(
                        seq_conta=seq_conta,
                        dat_saldo=data_atual,
                        val_saldo=round(saldo_atual, 2),
                        cod_pessoa_inclusao=1
                    ))
                    
                    # Move to next day
                    data_atual += timedelta(days=1)
            
            session.commit()
            print(f"Seeded daily balances for {len(contas)} accounts from {data_inicio} to {data_fim}")

    # Seed SimuladorCenario (cenários de exemplo para o simulador)
    if not SimuladorCenario.query.first():
        ano_base = 2025
        meses_projecao = 12
        
        # Listas de qualificadores de receita e despesa (todos os nós folha)
        qualificadores_receita = [
            'ICMS', 'IPVA', 'ITCMD',  # Impostos
            'FPE',  # Transferências Federais
            'FECOEP', 'ROYALTIES', 'APLICAÇÕES FINANCEIRAS', 'IR', 'OUTRAS RECEITAS'  # Demais Receitas
        ]
        
        qualificadores_despesa = [
            'FOLHA', 'PASEP',  # Pessoal
            'DÍVIDAS', 'PRECATÓRIOS',  # Serviço da Dívida
            'CUSTEIO',  # Custeio
            'INVESTIMENTO + AUMENTO DE CAPITAL',  # Investimento
            'REPASSE MUNICÍPIOS', 'REPASSE FUNDEB', 'SAÚDE 12%', 'EDUCAÇÃO 5%', 'PODERES',  # Encargos Gerais
            'RESTOS A PAGAR TESOURO e DEMAIS', 'FECOEP - RESTOS A PAGAR - FONTE 761'  # Restos a Pagar
        ]
        
        # ========== CENÁRIO 1: CONSERVADOR (Manual/LOA) ==========
        cenario1 = SimuladorCenario(
            nom_cenario='Cenário Conservador',
            dsc_cenario='Projeção conservadora com receitas manuais e despesas baseadas na LDO',
            ano_base=ano_base,
            meses_projecao=meses_projecao,
            ind_status='A',
            cod_pessoa_inclusao=1
        )
        session.add(cenario1)
        session.flush()
        
        # Configurar receita manual para cenário 1
        cenario1_receita = CenarioReceita(
            seq_simulador_cenario=cenario1.seq_simulador_cenario,
            cod_tipo_cenario='MANUAL'
        )
        session.add(cenario1_receita)
        session.flush()
        
        # Configurar despesa LOA para cenário 1
        cenario1_despesa = CenarioDespesa(
            seq_simulador_cenario=cenario1.seq_simulador_cenario,
            cod_tipo_cenario='LOA'
        )
        session.add(cenario1_despesa)
        session.flush()
        
        # Adicionar ajustes conservadores para TODAS as receitas (crescimento gradual)
        ajustes_conservadores_receita = {
            'ICMS': 2.0,  # 2% constante
            'IPVA': 1.5,  # 1.5% constante
            'ITCMD': 1.0,  # 1% constante
            'FPE': 2.5,  # 2.5% constante
            'FECOEP': 1.8,  # 1.8% constante
            'ROYALTIES': 0.5,  # 0.5% constante (receita volátil)
            'APLICAÇÕES FINANCEIRAS': 3.0,  # 3% constante
            'IR': 1.2,  # 1.2% constante
            'OUTRAS RECEITAS': 1.0,  # 1% constante
        }
        
        for qual_nome, percentual in ajustes_conservadores_receita.items():
            qual = encontrar_qualificador(qual_nome)
            if qual:
                for mes in range(1, 13):
                    session.add(CenarioReceitaAjuste(
                        seq_cenario_receita=cenario1_receita.seq_cenario_receita,
                        seq_qualificador=qual.seq_qualificador,
                        ano=ano_base,
                        mes=mes,
                        cod_tipo_ajuste='P',
                        val_ajuste=percentual
                    ))
        
        # ========== CENÁRIO 2: REALISTA (Manual/Manual) ==========
        cenario2 = SimuladorCenario(
            nom_cenario='Cenário Realista',
            dsc_cenario='Projeção realista com ajustes manuais variáveis em receitas e despesas',
            ano_base=ano_base,
            meses_projecao=meses_projecao,
            ind_status='A',
            cod_pessoa_inclusao=1
        )
        session.add(cenario2)
        session.flush()
        
        # Configurar receita manual para cenário 2
        cenario2_receita = CenarioReceita(
            seq_simulador_cenario=cenario2.seq_simulador_cenario,
            cod_tipo_cenario='MANUAL'
        )
        session.add(cenario2_receita)
        session.flush()
        
        # Configurar despesa manual para cenário 2
        cenario2_despesa = CenarioDespesa(
            seq_simulador_cenario=cenario2.seq_simulador_cenario,
            cod_tipo_cenario='MANUAL'
        )
        session.add(cenario2_despesa)
        session.flush()
        
        # Ajustes REALISTAS para receitas (variações mensais)
        ajustes_realistas_receita = {
            # ICMS: alta no começo do ano, estabiliza meio do ano
            'ICMS': [3.0, 2.8, 2.5, 2.2, 2.0, 2.0, 2.0, 2.1, 2.2, 2.3, 2.5, 2.8],
            # IPVA: pico em jan-mar (pagamento anual), depois cai
            'IPVA': [5.0, 4.0, 3.0, 1.0, 0.5, 0.5, 0.5, 0.5, 0.5, 0.5, 1.0, 1.5],
            # ITCMD: variação moderada
            'ITCMD': [1.0, 1.2, 1.5, 1.3, 1.0, 1.2, 1.4, 1.6, 1.5, 1.3, 1.2, 1.5],
            # FPE: crescimento gradual conforme repasses federais
            'FPE': [1.5, 1.8, 2.0, 2.2, 2.5, 2.3, 2.1, 2.0, 1.8, 1.6, 1.5, 1.4],
            # FECOEP: variação sazonal
            'FECOEP': [2.0, 1.8, 1.5, 1.3, 1.5, 1.8, 2.0, 2.2, 2.0, 1.8, 2.0, 2.5],
            # Royalties: volátil (depende preço petróleo)
            'ROYALTIES': [-1.0, 0.5, 1.0, 0.0, -0.5, 1.5, 2.0, 1.0, 0.5, 1.5, 2.5, 2.0],
            # Aplicações Financeiras: acompanha SELIC
            'APLICAÇÕES FINANCEIRAS': [4.0, 4.2, 4.5, 4.3, 4.0, 3.8, 3.5, 3.3, 3.0, 3.2, 3.5, 3.8],
            # IR: pico em abril (declaração), menor em dezembro
            'IR': [1.0, 1.2, 1.5, 3.5, 2.0, 1.5, 1.2, 1.0, 1.0, 1.2, 1.5, 0.8],
            # Outras receitas: crescimento moderado
            'OUTRAS RECEITAS': [1.0, 1.1, 1.2, 1.3, 1.4, 1.5, 1.6, 1.5, 1.4, 1.3, 1.4, 1.5],
        }
        
        for qual_nome, percentuais_mensais in ajustes_realistas_receita.items():
            qual = encontrar_qualificador(qual_nome)
            if qual:
                for mes, percentual in enumerate(percentuais_mensais, 1):
                    session.add(CenarioReceitaAjuste(
                        seq_cenario_receita=cenario2_receita.seq_cenario_receita,
                        seq_qualificador=qual.seq_qualificador,
                        ano=ano_base,
                        mes=mes,
                        cod_tipo_ajuste='P',
                        val_ajuste=percentual
                    ))
        
        # Ajustes REALISTAS para despesas (variações mensais)
        ajustes_realistas_despesa = {
            # FOLHA: reajuste salarial gradual + 13º em dez
            'FOLHA': [1.5, 1.5, 1.5, 1.5, 1.8, 1.8, 1.8, 1.8, 1.8, 1.8, 1.8, 3.5],
            # PASEP: pago principalmente em julho
            'PASEP': [0.5, 0.5, 0.5, 0.5, 0.5, 0.5, 5.0, 0.5, 0.5, 0.5, 0.5, 0.5],
            # DÍVIDAS: pagamento constante (juros + principal)
            'DÍVIDAS': [2.0, 2.0, 2.0, 2.0, 2.0, 2.0, 2.0, 2.0, 2.0, 2.0, 2.0, 2.0],
            # PRECATÓRIOS: variável conforme judicial
            'PRECATÓRIOS': [1.0, 0.5, 0.5, 1.5, 1.0, 0.5, 0.5, 2.0, 1.5, 1.0, 0.5, 3.0],
            # CUSTEIO: maior no início do ano, reduz meio do ano
            'CUSTEIO': [3.0, 2.5, 2.0, 1.5, 1.2, 1.0, 1.0, 1.2, 1.5, 2.0, 2.5, 3.0],
            # INVESTIMENTO: maior execução segundo semestre
            'INVESTIMENTO + AUMENTO DE CAPITAL': [0.5, 0.8, 1.0, 1.2, 1.5, 2.0, 2.5, 3.0, 3.5, 4.0, 4.5, 5.0],
            # REPASSE MUNICÍPIOS: constante
            'REPASSE MUNICÍPIOS': [1.5, 1.5, 1.5, 1.5, 1.5, 1.5, 1.5, 1.5, 1.5, 1.5, 1.5, 1.5],
            # REPASSE FUNDEB: acompanha arrecadação
            'REPASSE FUNDEB': [2.0, 1.8, 1.6, 1.5, 1.5, 1.5, 1.5, 1.6, 1.7, 1.8, 2.0, 2.2],
            # SAÚDE 12%: vinculado à receita
            'SAÚDE 12%': [2.0, 2.0, 2.0, 2.0, 2.0, 2.0, 2.0, 2.0, 2.0, 2.0, 2.0, 2.0],
            # EDUCAÇÃO 5%: vinculado à receita
            'EDUCAÇÃO 5%': [2.0, 2.0, 2.0, 2.0, 2.0, 2.0, 2.0, 2.0, 2.0, 2.0, 2.0, 2.0],
            # PODERES: duodécimo regular
            'PODERES': [1.2, 1.2, 1.2, 1.2, 1.2, 1.2, 1.2, 1.2, 1.2, 1.2, 1.2, 1.2],
            # RESTOS A PAGAR: liquidação ao longo do ano
            'RESTOS A PAGAR TESOURO e DEMAIS': [5.0, 4.0, 3.0, 2.5, 2.0, 1.5, 1.0, 0.8, 0.6, 0.5, 0.3, 0.2],
            # FECOEP Restos: similar
            'FECOEP - RESTOS A PAGAR - FONTE 761': [4.0, 3.5, 3.0, 2.5, 2.0, 1.5, 1.2, 1.0, 0.8, 0.6, 0.4, 0.2],
        }
        
        for qual_nome, percentuais_mensais in ajustes_realistas_despesa.items():
            qual = encontrar_qualificador(qual_nome)
            if qual:
                for mes, percentual in enumerate(percentuais_mensais, 1):
                    session.add(CenarioDespesaAjuste(
                        seq_cenario_despesa=cenario2_despesa.seq_cenario_despesa,
                        seq_qualificador=qual.seq_qualificador,
                        ano=ano_base,
                        mes=mes,
                        cod_tipo_ajuste='P',
                        val_ajuste=percentual
                    ))
        
        session.commit()
        print(f"Seeded 2 complete simulador scenarios with adjustments for ALL qualifiers across 12 months")

    # ==================== Seed LOA (Lei Orçamentária Anual) ====================
    if not Loa.query.first():
        # LOA 2025 — Receitas (valores anuais em R$)
        loa_receitas_2025 = {
            'ICMS': 8_760_000_000.00,
            'IPVA': 598_000_000.00,
            'ITCMD': 102_600_000.00,
            'FPE': 9_120_000_000.00,
            'FECOEP': 456_605_520.00,
            'ROYALTIES': 120_500_000.00,
            'APLICAÇÕES FINANCEIRAS': 74_100_000.00,
            'IR': 720_000_000.00,
            'OUTRAS RECEITAS': 1_530_000_000.00,
        }

        # LOA 2025 — Despesas (valores anuais em R$)
        loa_despesas_2025 = {
            'FOLHA': 6_555_000_000.00,
            'PASEP': 296_000_000.00,
            'DÍVIDAS': 480_000_000.00,
            'PRECATÓRIOS': 81_500_000.00,
            'CUSTEIO': 1_238_000_000.00,
            'INVESTIMENTO + AUMENTO DE CAPITAL': 361_048_000.00,
            'REPASSE MUNICÍPIOS': 5_340_000_000.00,
            'REPASSE FUNDEB': 3_307_255_440.00,
            'SAÚDE 12%': 2_001_588_960.00,
            'EDUCAÇÃO 5%': 680_962_000.00,
            'PODERES': 2_610_000_000.00,
            'RESTOS A PAGAR TESOURO e DEMAIS': 588_000_000.00,
            'FECOEP - RESTOS A PAGAR - FONTE 761': 296_519_460.00,
        }

        # LOA 2024 — Receitas (valores levemente menores)
        loa_receitas_2024 = {
            'ICMS': 7_936_680_000.00,
            'IPVA': 539_652_000.00,
            'ITCMD': 87_183_600.00,
            'FPE': 8_304_120_000.00,
            'FECOEP': 429_456_000.00,
            'ROYALTIES': 88_553_400.00,
            'APLICAÇÕES FINANCEIRAS': 54_994_800.00,
            'IR': 665_000_000.00,
            'OUTRAS RECEITAS': 1_462_398_000.00,
        }

        # LOA 2024 — Despesas
        loa_despesas_2024 = {
            'FOLHA': 5_844_183_600.00,
            'PASEP': 156_780_480.00,
            'DÍVIDAS': 456_598_000.00,
            'PRECATÓRIOS': 456_597_780.00,
            'CUSTEIO': 1_111_464_000.00,
            'INVESTIMENTO + AUMENTO DE CAPITAL': 350_953_000.00,
            'REPASSE MUNICÍPIOS': 2_302_528_080.00,
            'REPASSE FUNDEB': 2_986_257_960.00,
            'SAÚDE 12%': 1_860_000_000.00,
            'EDUCAÇÃO 5%': 552_086_160.00,
            'PODERES': 1_762_395_960.00,
            'RESTOS A PAGAR TESOURO e DEMAIS': 736_668_240.00,
            'FECOEP - RESTOS A PAGAR - FONTE 761': 295_774_320.00,
        }

        for dados_dict in [loa_receitas_2025, loa_despesas_2025]:
            for nome, valor in dados_dict.items():
                qual = encontrar_qualificador(nome)
                if qual:
                    session.add(Loa(num_ano=2025, seq_qualificador=qual.seq_qualificador, val_loa=valor))

        for dados_dict in [loa_receitas_2024, loa_despesas_2024]:
            for nome, valor in dados_dict.items():
                qual = encontrar_qualificador(nome)
                if qual:
                    session.add(Loa(num_ano=2024, seq_qualificador=qual.seq_qualificador, val_loa=valor))

        # LOA 2023 — Receitas
        loa_receitas_2023 = {
            'ICMS': 7_189_920_000.00,
            'IPVA': 487_476_000.00,
            'ITCMD': 74_006_160.00,
            'FPE': 7_556_749_200.00,
            'FECOEP': 404_098_800.00,
            'ROYALTIES': 65_047_300.00,
            'APLICAÇÕES FINANCEIRAS': 40_796_760.00,
            'IR': 614_000_000.00,
            'OUTRAS RECEITAS': 1_397_530_800.00,
        }

        # LOA 2023 — Despesas
        loa_despesas_2023 = {
            'FOLHA': 5_290_986_000.00,
            'PASEP': 115_536_000.00,
            'DÍVIDAS': 434_068_100.00,
            'PRECATÓRIOS': 411_538_000.00,
            'CUSTEIO': 1_000_317_600.00,
            'INVESTIMENTO + AUMENTO DE CAPITAL': 326_385_790.00,
            'REPASSE MUNICÍPIOS': 2_094_300_720.00,
            'REPASSE FUNDEB': 2_701_213_200.00,
            'SAÚDE 12%': 1_730_400_000.00,
            'EDUCAÇÃO 5%': 496_877_540.00,
            'PODERES': 1_592_967_600.00,
            'RESTOS A PAGAR TESOURO e DEMAIS': 680_936_400.00,
            'FECOEP - RESTOS A PAGAR - FONTE 761': 274_069_920.00,
        }

        for dados_dict in [loa_receitas_2023, loa_despesas_2023]:
            for nome, valor in dados_dict.items():
                qual = encontrar_qualificador(nome)
                if qual:
                    session.add(Loa(num_ano=2023, seq_qualificador=qual.seq_qualificador, val_loa=valor))

        # LOA 2022 — Receitas
        loa_receitas_2022 = {
            'ICMS': 6_512_088_000.00,
            'IPVA': 440_566_200.00,
            'ITCMD': 62_905_236.00,
            'FPE': 6_878_141_580.00,
            'FECOEP': 380_252_880.00,
            'ROYALTIES': 47_784_550.00,
            'APLICAÇÕES FINANCEIRAS': 30_257_808.00,
            'IR': 567_000_000.00,
            'OUTRAS RECEITAS': 1_337_002_140.00,
        }

        # LOA 2022 — Despesas
        loa_despesas_2022 = {
            'FOLHA': 4_790_292_630.00,
            'PASEP': 85_096_128.00,
            'DÍVIDAS': 412_864_700.00,
            'PRECATÓRIOS': 370_384_200.00,
            'CUSTEIO': 900_285_840.00,
            'INVESTIMENTO + AUMENTO DE CAPITAL': 303_538_584.00,
            'REPASSE MUNICÍPIOS': 1_905_813_660.00,
            'REPASSE FUNDEB': 2_443_096_920.00,
            'SAÚDE 12%': 1_608_672_000.00,
            'EDUCAÇÃO 5%': 447_189_786.00,
            'PODERES': 1_441_076_280.00,
            'RESTOS A PAGAR TESOURO e DEMAIS': 630_066_720.00,
            'FECOEP - RESTOS A PAGAR - FONTE 761': 253_924_920.00,
        }

        for dados_dict in [loa_receitas_2022, loa_despesas_2022]:
            for nome, valor in dados_dict.items():
                qual = encontrar_qualificador(nome)
                if qual:
                    session.add(Loa(num_ano=2022, seq_qualificador=qual.seq_qualificador, val_loa=valor))

        session.commit()
        print("Seeded LOA data for 2022, 2023, 2024 and 2025")
