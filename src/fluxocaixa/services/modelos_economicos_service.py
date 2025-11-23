"""Service for economic forecasting models."""

from typing import List, Dict, Optional, Tuple
from datetime import date, datetime
from dateutil.relativedelta import relativedelta
import json
import numpy as np
import pandas as pd

# Statistical models
try:
    from statsmodels.tsa.holtwinters import ExponentialSmoothing
    from statsmodels.tsa.arima.model import ARIMA
    from statsmodels.tsa.statespace.sarimax import SARIMAX
    from sklearn.linear_model import LinearRegression
except ImportError as e:
    print(f"Warning: Statistical libraries not available: {e}")


from ..models import db, Lancamento, Qualificador
from sqlalchemy import func, extract, and_


# ==================== Helper Functions ====================

def obter_dados_historicos(
    seq_qualificador: int,
    data_inicio: date,
    data_fim: date,
    agregacao: str = 'mensal'  # 'mensal' ou 'diario'
) -> pd.DataFrame:
    """
    Obtém dados históricos de lançamentos para um qualificador.
    
    Args:
        seq_qualificador: ID do qualificador
        data_inicio: Data inicial do período
        data_fim: Data final do período
        agregacao: 'mensal' ou 'diario'
    
    Returns:
        DataFrame com colunas: data, valor
    """
    # Buscar lançamentos no período
    lancamentos = (
        Lancamento.query
        .filter(
            Lancamento.seq_qualificador == seq_qualificador,
            Lancamento.dat_lancamento >= data_inicio,
            Lancamento.dat_lancamento <= data_fim,
        )
        .all()
    )
    
    if not lancamentos:
        return pd.DataFrame(columns=['data', 'valor'])
    
    # Converter para DataFrame
    data = []
    for lanc in lancamentos:
        data.append({
            'data': lanc.dat_lancamento,
            'valor': float(lanc.val_lancamento)
        })
    
    df = pd.DataFrame(data)
    
    # Agregar se necessário
    if agregacao == 'mensal':
        df['ano_mes'] = df['data'].apply(lambda x: x.strftime('%Y-%m'))
        df_agregado = df.groupby('ano_mes')['valor'].sum().reset_index()
        df_agregado.columns = ['data', 'valor']
        df_agregado['data'] = pd.to_datetime(df_agregado['data'] + '-01')
        return df_agregado.sort_values('data')
    
    return df.sort_values('data')


def obter_dados_historicos_multiplos(
    seq_qualificadores: List[int],
    data_inicio: date,
    data_fim: date,
) -> Dict[int, pd.DataFrame]:
    """Obtém dados históricos para múltiplos qualificadores."""
    resultado = {}
    for seq_q in seq_qualificadores:
        resultado[seq_q] = obter_dados_historicos(seq_q, data_inicio, data_fim)
    return resultado


# ==================== Revenue Forecast Models ====================

def projetar_holt_winters(
    dados_historicos: pd.DataFrame,
    meses_projecao: int,
    config: Dict,
) -> pd.DataFrame:
    """
    Projeta valores usando Holt-Winters (Suavização Exponencial).
    
    Args:
        dados_historicos: DataFrame com colunas 'data' e 'valor'
        meses_projecao: Número de meses a projetar
        config: Dicionário com parâmetros:
            - seasonal_periods: Período sazonal (default: 12 para mensal)
            - trend: 'add' ou 'mul' (default: 'add')
            - seasonal: 'add' ou 'mul' (default: 'add')
    
    Returns:
        DataFrame com colunas: data, valor_projetado
    """
    if len(dados_historicos) < 24:  # Mínimo de 2 anos de dados
        raise ValueError("Holt-Winters requer pelo menos 24 meses de dados históricos")
    
    # Parâmetros
    seasonal_periods = config.get('seasonal_periods', 12)
    trend = config.get('trend', 'add')
    seasonal = config.get('seasonal', 'add')
    
    # Criar séries temporal
    series = dados_historicos.set_index('data')['valor']
    
    # Treinar modelo
    model = ExponentialSmoothing(
        series,
        seasonal_periods=seasonal_periods,
        trend=trend,
        seasonal=seasonal,
    )
    fitted_model = model.fit()
    
    # Fazer projeção
    forecast = fitted_model.forecast(steps=meses_projecao)
    
    # Criar DataFrame de resultado
    ultima_data = dados_historicos['data'].max()
    datas_futuras = [ultima_data + relativedelta(months=i+1) for i in range(meses_projecao)]
    
    resultado = pd.DataFrame({
        'data': datas_futuras,
        'valor_projetado': forecast.values
    })
    
    return resultado


def projetar_arima(
    dados_historicos: pd.DataFrame,
    meses_projecao: int,
    config: Dict,
) -> pd.DataFrame:
    """
    Projeta valores usando ARIMA (AutoRegressive Integrated Moving Average).
    
    Args:
        dados_historicos: DataFrame com colunas 'data' e 'valor'
        meses_projecao: Número de meses a projetar
        config: Dicionário com parâmetros:
            - p: ordem autoregressiva (default: 1)
            - d: ordem de diferenciação (default: 1)
            - q: ordem de média móvel (default: 1)
    
    Returns:
        DataFrame com colunas: data, valor_projetado
    """
    if len(dados_historicos) < 12:
        raise ValueError("ARIMA requer pelo menos 12 meses de dados históricos")
    
    # Parâmetros
    p = config.get('p', 1)
    d = config.get('d', 1)
    q = config.get('q', 1)
    
    # Criar série temporal
    series = dados_historicos.set_index('data')['valor']
    
    # Treinar modelo
    model = ARIMA(series, order=(p, d, q))
    fitted_model = model.fit()
    
    # Fazer projeção
    forecast = fitted_model.forecast(steps=meses_projecao)
    
    # Criar DataFrame de resultado
    ultima_data = dados_historicos['data'].max()
    datas_futuras = [ultima_data + relativedelta(months=i+1) for i in range(meses_projecao)]
    
    resultado = pd.DataFrame({
        'data': datas_futuras,
        'valor_projetado': forecast.values
    })
    
    return resultado


def projetar_sarima(
    dados_historicos: pd.DataFrame,
    meses_projecao: int,
    config: Dict,
) -> pd.DataFrame:
    """
    Projeta valores usando SARIMA (Seasonal ARIMA).
    
    Args:
        dados_historicos: DataFrame com colunas 'data' e 'valor'
        meses_projecao: Número de meses a projetar
        config: Dicionário com parâmetros:
            - p, d, q: ordens não-sazonais
            - P, D, Q, s: ordens sazonais (s = período sazonal, default 12)
    
    Returns:
        DataFrame com colunas: data, valor_projetado
    """
    if len(dados_historicos) < 24:
        raise ValueError("SARIMA requer pelo menos 24 meses de dados históricos")
    
    # Parâmetros
    p = config.get('p', 1)
    d = config.get('d', 1)
    q = config.get('q', 1)
    P = config.get('P', 1)
    D = config.get('D', 1)
    Q = config.get('Q', 1)
    s = config.get('s', 12)
    
    # Criar série temporal
    series = dados_historicos.set_index('data')['valor']
    
    # Treinar modelo
    model = SARIMAX(series, order=(p, d, q), seasonal_order=(P, D, Q, s))
    fitted_model = model.fit(disp=False)
    
    # Fazer projeção
    forecast = fitted_model.forecast(steps=meses_projecao)
    
    # Criar DataFrame de resultado
    ultima_data = dados_historicos['data'].max()
    datas_futuras = [ultima_data + relativedelta(months=i+1) for i in range(meses_projecao)]
    
    resultado = pd.DataFrame({
        'data': datas_futuras,
        'valor_projetado': forecast.values
    })
    
    return resultado


def projetar_regressao_multipla(
    meses_projecao: int,
    config: Dict,
) -> pd.DataFrame:
    """
    Projeta valores usando Regressão Linear Múltipla com parâmetros fornecidos pelo usuário.
    
    Fórmula: Receita = α + β₁(Variável₁) + β₂(Variável₂) + ... + βₙ(Variávelₙ)
    
    Args:
        meses_projecao: Número de meses a projetar
        config: Dicionário com:
            - alpha: intercepto (α)
            - parametros: List[Dict] com:
                - nome: nome da variável
                - coeficiente: valor do β
                - valores_projetados: List[float] com valores para cada mês
    
    Returns:
        DataFrame com colunas: data, valor_projetado
    """
    alpha = config.get('alpha', 0)
    parametros = config.get('parametros', [])
    
    if not parametros:
        raise ValueError("Regressão Linear requer pelo menos uma variável independente")
    
    # Calcular projeções mês a mês
    projecoes = []
    
    for mes in range(meses_projecao):
        # Receita = α + Σ(βᵢ × Variávelᵢ)
        valor = alpha
        
        for param in parametros:
            coef = param['coeficiente']
            valores = param.get('valores_projetados', [])
            
            if mes < len(valores):
                valor += coef * valores[mes]
            else:
                # Se não há valor projetado, usar o último disponível
                if valores:
                    valor += coef * valores[-1]
        
        projecoes.append(valor)
    
    # Criar DataFrame de resultado
    data_base = date.today().replace(day=1)
    datas_futuras = [data_base + relativedelta(months=i) for i in range(meses_projecao)]
    
    resultado = pd.DataFrame({
        'data': datas_futuras,
        'valor_projetado': projecoes
    })
    
    return resultado


# ==================== Expense Forecast Models ====================

def projetar_loa(
    meses_projecao: int,
    config: Dict,
) -> pd.DataFrame:
    """
    Projeta despesas usando valores da LOA (Lei Orçamentária Anual).
    
    Args:
        meses_projecao: Número de meses a projetar
        config: Dicionário com:
            - valores_mensais: List[float] com valores para cada mês
            - distribuicao: 'uniforme' ou 'especifica'
            - valor_anual: float (se distribuição uniforme)
    
    Returns:
        DataFrame com colunas: data, valor_projetado
    """
    distribuicao = config.get('distribuicao', 'uniforme')
    
    if distribuicao == 'uniforme':
        # Distribuir valor anual uniformemente
        valor_anual = config.get('valor_anual', 0)
        valor_mensal = valor_anual / 12
        projecoes = [valor_mensal] * meses_projecao
    else:
        # Usar valores específicos fornecidos
        valores_mensais = config.get('valores_mensais', [])
        projecoes = []
        
        for mes in range(meses_projecao):
            if mes < len(valores_mensais):
                projecoes.append(valores_mensais[mes])
            else:
                # Repetir padrão se necessário
                projecoes.append(valores_mensais[mes % len(valores_mensais)] if valores_mensais else 0)
    
    # Criar DataFrame de resultado
    data_base = date.today().replace(day=1)
    datas_futuras = [data_base + relativedelta(months=i) for i in range(meses_projecao)]
    
    resultado = pd.DataFrame({
        'data': datas_futuras,
        'valor_projetado': projecoes
    })
    
    return resultado


def projetar_media_historica(
    dados_historicos: pd.DataFrame,
    meses_projecao: int,
    config: Dict,
) -> pd.DataFrame:
    """
    Projeta despesas usando média histórica ajustada.
    
    Args:
        dados_historicos: DataFrame com colunas 'data' e 'valor'
        meses_projecao: Número de meses a projetar
        config: Dicionário com:
            - periodo_meses: quantos meses usar para média (default: 12)
            - fator_ajuste: multiplicador para ajuste (default: 1.0)
            - considerar_sazonalidade: bool (default: True)
    
    Returns:
        DataFrame com colunas: data, valor_projetado
    """
    periodo_meses = config.get('periodo_meses', 12)
    fator_ajuste = config.get('fator_ajuste', 1.0)
    considerar_sazonalidade = config.get('considerar_sazonalidade', True)
    
    if len(dados_historicos) == 0:
        raise ValueError("Não há dados históricos disponíveis")
    
    # Usar últimos N meses
    df_recente = dados_historicos.tail(periodo_meses)
    
    if considerar_sazonalidade and len(dados_historicos) >= 12:
        # Calcular média por mês do ano (sazonalidade)
        dados_historicos['mes'] = pd.to_datetime(dados_historicos['data']).dt.month
        media_por_mes = dados_historicos.groupby('mes')['valor'].mean().to_dict()
        
        # Projetar com padrão sazonal
        data_base = dados_historicos['data'].max()
        projecoes = []
        
        for i in range(meses_projecao):
            data_futura = data_base + relativedelta(months=i+1)
            mes = data_futura.month
            valor = media_por_mes.get(mes, df_recente['valor'].mean()) * fator_ajuste
            projecoes.append(valor)
    else:
        # Média simples
        media = df_recente['valor'].mean() * fator_ajuste
        projecoes = [media] * meses_projecao
    
    # Criar DataFrame de resultado
    ultima_data = dados_historicos['data'].max()
    datas_futuras = [ultima_data + relativedelta(months=i+1) for i in range(meses_projecao)]
    
    resultado = pd.DataFrame({
        'data': datas_futuras,
        'valor_projetado': projecoes
    })
    
    return resultado
