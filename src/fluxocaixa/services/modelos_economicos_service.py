"""Service for economic forecasting models."""

from typing import List, Dict, Optional, Tuple
from datetime import date, datetime
from dateutil.relativedelta import relativedelta
import json
import numpy as np
import pandas as pd
import warnings

# Suppress convergence warnings from statsmodels
warnings.filterwarnings('ignore', category=UserWarning)
warnings.filterwarnings('ignore', category=FutureWarning)

# Statistical models
HAS_STATSMODELS = False
HAS_SKLEARN = False

try:
    from statsmodels.tsa.holtwinters import ExponentialSmoothing
    from statsmodels.tsa.arima.model import ARIMA
    from statsmodels.tsa.statespace.sarimax import SARIMAX
    HAS_STATSMODELS = True
except ImportError as e:
    print(f"Warning: statsmodels not available: {e}")

try:
    from sklearn.linear_model import LinearRegression
    HAS_SKLEARN = True
except ImportError as e:
    print(f"Warning: sklearn not available: {e}")


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
    ano_base: int = None,
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
            - damped_trend: bool (default: False) - Amortecer tendência
            - use_boxcox: bool (default: False) - Transformação Box-Cox
        ano_base: Ano base para projeção (opcional)
    
    Returns:
        DataFrame com colunas: data, valor_projetado
    """
    if not HAS_STATSMODELS:
        raise ValueError("Biblioteca statsmodels não está instalada. Execute: pip install statsmodels")
    
    if len(dados_historicos) < 24:  # Mínimo de 2 anos de dados
        # Tentar com menos dados se houver pelo menos 12 meses
        if len(dados_historicos) >= 12:
            print("Aviso: Usando Holt-Winters com menos de 24 meses de dados")
        else:
            raise ValueError("Holt-Winters requer pelo menos 12 meses de dados históricos")
    
    # Parâmetros
    seasonal_periods = int(config.get('seasonal_periods', 12))
    trend = config.get('trend', 'add')
    seasonal = config.get('seasonal', 'add')
    damped_trend = config.get('damped_trend', False)
    use_boxcox = config.get('use_boxcox', False)
    
    # Garantir que o período sazonal não seja maior que os dados
    if seasonal_periods >= len(dados_historicos):
        seasonal_periods = len(dados_historicos) // 2
    
    # Criar série temporal
    df_sorted = dados_historicos.sort_values('data')
    series = df_sorted.set_index('data')['valor']
    
    # Garantir valores positivos para multiplicativo ou Box-Cox
    if seasonal == 'mul' or use_boxcox:
        min_val = series.min()
        if min_val <= 0:
            series = series - min_val + 1  # Ajustar para valores positivos
    
    try:
        # Treinar modelo
        model = ExponentialSmoothing(
            series,
            seasonal_periods=seasonal_periods,
            trend=trend,
            seasonal=seasonal,
            damped_trend=damped_trend,
            use_boxcox=use_boxcox,
        )
        fitted_model = model.fit(optimized=True)
        
        # Fazer projeção
        forecast = fitted_model.forecast(steps=meses_projecao)
        
    except Exception as e:
        # Fallback para modelo mais simples
        print(f"Erro no Holt-Winters complexo: {e}. Tentando versão simplificada.")
        model = ExponentialSmoothing(
            series,
            seasonal_periods=seasonal_periods,
            trend='add',
            seasonal='add',
        )
        fitted_model = model.fit()
        forecast = fitted_model.forecast(steps=meses_projecao)
    
    # Criar DataFrame de resultado
    if ano_base:
        # Usar ano base especificado
        datas_futuras = [date(ano_base, i+1, 1) for i in range(meses_projecao)]
    else:
        ultima_data = df_sorted['data'].max()
        datas_futuras = [ultima_data + relativedelta(months=i+1) for i in range(meses_projecao)]
    
    # Garantir valores não-negativos
    valores = forecast.values
    valores = np.maximum(valores, 0)
    
    resultado = pd.DataFrame({
        'data': datas_futuras,
        'valor_projetado': valores
    })
    
    return resultado


def projetar_arima(
    dados_historicos: pd.DataFrame,
    meses_projecao: int,
    config: Dict,
    ano_base: int = None,
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
            - auto_order: bool (default: False) - Seleção automática de ordem
        ano_base: Ano base para projeção (opcional)
    
    Returns:
        DataFrame com colunas: data, valor_projetado
    """
    if not HAS_STATSMODELS:
        raise ValueError("Biblioteca statsmodels não está instalada. Execute: pip install statsmodels")
    
    if len(dados_historicos) < 12:
        raise ValueError("ARIMA requer pelo menos 12 meses de dados históricos")
    
    # Parâmetros
    p = int(config.get('p', 1))
    d = int(config.get('d', 1))
    q = int(config.get('q', 1))
    auto_order = config.get('auto_order', False)
    
    # Criar série temporal
    df_sorted = dados_historicos.sort_values('data')
    series = df_sorted.set_index('data')['valor']
    
    try:
        if auto_order:
            # Tentar encontrar melhor ordem automaticamente
            best_aic = float('inf')
            best_order = (p, d, q)
            
            for p_try in range(0, 4):
                for d_try in range(0, 3):
                    for q_try in range(0, 4):
                        try:
                            model = ARIMA(series, order=(p_try, d_try, q_try))
                            fitted = model.fit()
                            if fitted.aic < best_aic:
                                best_aic = fitted.aic
                                best_order = (p_try, d_try, q_try)
                        except:
                            continue
            
            p, d, q = best_order
        
        # Treinar modelo
        model = ARIMA(series, order=(p, d, q))
        fitted_model = model.fit()
        
        # Fazer projeção
        forecast = fitted_model.forecast(steps=meses_projecao)
        
    except Exception as e:
        # Fallback para modelo mais simples
        print(f"Erro no ARIMA({p},{d},{q}): {e}. Tentando (1,1,1).")
        model = ARIMA(series, order=(1, 1, 1))
        fitted_model = model.fit()
        forecast = fitted_model.forecast(steps=meses_projecao)
    
    # Criar DataFrame de resultado
    if ano_base:
        datas_futuras = [date(ano_base, i+1, 1) for i in range(meses_projecao)]
    else:
        ultima_data = df_sorted['data'].max()
        datas_futuras = [ultima_data + relativedelta(months=i+1) for i in range(meses_projecao)]
    
    # Garantir valores não-negativos
    valores = forecast.values
    valores = np.maximum(valores, 0)
    
    resultado = pd.DataFrame({
        'data': datas_futuras,
        'valor_projetado': valores
    })
    
    return resultado


def projetar_sarima(
    dados_historicos: pd.DataFrame,
    meses_projecao: int,
    config: Dict,
    ano_base: int = None,
) -> pd.DataFrame:
    """
    Projeta valores usando SARIMA (Seasonal ARIMA).
    
    Args:
        dados_historicos: DataFrame com colunas 'data' e 'valor'
        meses_projecao: Número de meses a projetar
        config: Dicionário com parâmetros:
            - p, d, q: ordens não-sazonais
            - P, D, Q, s: ordens sazonais (s = período sazonal, default 12)
            - enforce_stationarity: bool (default: True)
            - enforce_invertibility: bool (default: True)
        ano_base: Ano base para projeção (opcional)
    
    Returns:
        DataFrame com colunas: data, valor_projetado
    """
    if not HAS_STATSMODELS:
        raise ValueError("Biblioteca statsmodels não está instalada. Execute: pip install statsmodels")
    
    if len(dados_historicos) < 24:
        # Tentar com menos dados se houver pelo menos 12 meses
        if len(dados_historicos) >= 12:
            print("Aviso: Usando SARIMA com menos de 24 meses de dados")
        else:
            raise ValueError("SARIMA requer pelo menos 12 meses de dados históricos")
    
    # Parâmetros não-sazonais
    p = int(config.get('p', 1))
    d = int(config.get('d', 1))
    q = int(config.get('q', 1))
    
    # Parâmetros sazonais
    P = int(config.get('P', 1))
    D = int(config.get('D', 1))
    Q = int(config.get('Q', 1))
    s = int(config.get('s', 12))
    
    enforce_stationarity = config.get('enforce_stationarity', False)
    enforce_invertibility = config.get('enforce_invertibility', False)
    
    # Criar série temporal
    df_sorted = dados_historicos.sort_values('data')
    series = df_sorted.set_index('data')['valor']
    
    try:
        # Treinar modelo SARIMA
        model = SARIMAX(
            series,
            order=(p, d, q),
            seasonal_order=(P, D, Q, s),
            enforce_stationarity=enforce_stationarity,
            enforce_invertibility=enforce_invertibility,
        )
        fitted_model = model.fit(disp=False, maxiter=200)
        
        # Fazer projeção
        forecast = fitted_model.forecast(steps=meses_projecao)
        
    except Exception as e:
        # Fallback para modelo mais simples
        print(f"Erro no SARIMA: {e}. Tentando ARIMA simples.")
        try:
            model = ARIMA(series, order=(1, 1, 1))
            fitted_model = model.fit()
            forecast = fitted_model.forecast(steps=meses_projecao)
        except Exception as e2:
            print(f"Erro no ARIMA fallback: {e2}. Usando média móvel.")
            # Fallback final: média dos últimos 12 meses
            media = series.tail(12).mean()
            forecast = pd.Series([media] * meses_projecao)
    
    # Criar DataFrame de resultado
    if ano_base:
        datas_futuras = [date(ano_base, i+1, 1) for i in range(meses_projecao)]
    else:
        ultima_data = df_sorted['data'].max()
        datas_futuras = [ultima_data + relativedelta(months=i+1) for i in range(meses_projecao)]
    
    # Garantir valores não-negativos
    valores = forecast.values if hasattr(forecast, 'values') else list(forecast)
    valores = np.maximum(valores, 0)
    
    resultado = pd.DataFrame({
        'data': datas_futuras,
        'valor_projetado': valores
    })
    
    return resultado


def projetar_regressao_multipla(
    meses_projecao: int,
    config: Dict,
    ano_base: int = None,
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
        ano_base: Ano base para projeção (opcional)
    
    Returns:
        DataFrame com colunas: data, valor_projetado
    """
    try:
        alpha = float(config.get('alpha', 0) or 0)
    except (ValueError, TypeError):
        alpha = 0
    
    parametros = config.get('parametros', [])
    
    # Se não há parâmetros mas há alpha, retornar alpha para todos os meses
    if not parametros and alpha == 0:
        raise ValueError("Regressão Linear requer intercepto ou pelo menos uma variável independente")
    
    # Calcular projeções mês a mês
    projecoes = []
    
    for mes in range(meses_projecao):
        # Receita = α + Σ(βᵢ × Variávelᵢ)
        valor = alpha
        
        for param in parametros:
            try:
                coef = float(param.get('coeficiente', 0) or 0)
            except (ValueError, TypeError):
                coef = 0
            
            valores = param.get('valores_projetados', [])
            
            if mes < len(valores):
                try:
                    val = float(valores[mes] or 0)
                except (ValueError, TypeError):
                    val = 0
                valor += coef * val
            else:
                # Se não há valor projetado, usar o último disponível
                if valores:
                    try:
                        val = float(valores[-1] or 0)
                    except (ValueError, TypeError):
                        val = 0
                    valor += coef * val
        
        # Garantir valor não-negativo
        projecoes.append(max(valor, 0))
    
    # Criar DataFrame de resultado
    if ano_base:
        datas_futuras = [date(ano_base, i+1, 1) for i in range(meses_projecao)]
    else:
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
    ano_base: int = None,
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
        ano_base: Ano base para projeção (opcional)
    
    Returns:
        DataFrame com colunas: data, valor_projetado
    """
    try:
        periodo_meses = int(config.get('periodo_meses', 12) or 12)
    except (ValueError, TypeError):
        periodo_meses = 12
    
    try:
        fator_ajuste = float(config.get('fator_ajuste', 1.0) or 1.0)
    except (ValueError, TypeError):
        fator_ajuste = 1.0
    
    considerar_sazonalidade = config.get('considerar_sazonalidade', True)
    
    if len(dados_historicos) == 0:
        raise ValueError("Não há dados históricos disponíveis")
    
    # Fazer cópia para não modificar original
    df = dados_historicos.copy()
    
    # Usar últimos N meses
    df_recente = df.tail(periodo_meses)
    
    if considerar_sazonalidade and len(df) >= 12:
        # Calcular média por mês do ano (sazonalidade)
        df['mes'] = pd.to_datetime(df['data']).dt.month
        media_por_mes = df.groupby('mes')['valor'].mean().to_dict()
        
        # Projetar com padrão sazonal
        data_base = df['data'].max()
        projecoes = []
        
        for i in range(meses_projecao):
            if ano_base:
                mes = (i % 12) + 1
            else:
                data_futura = data_base + relativedelta(months=i+1)
                mes = data_futura.month
            valor = media_por_mes.get(mes, df_recente['valor'].mean()) * fator_ajuste
            projecoes.append(max(valor, 0))
    else:
        # Média simples
        media = df_recente['valor'].mean() * fator_ajuste
        projecoes = [max(media, 0)] * meses_projecao
    
    # Criar DataFrame de resultado
    if ano_base:
        datas_futuras = [date(ano_base, i+1, 1) for i in range(meses_projecao)]
    else:
        ultima_data = df['data'].max()
        datas_futuras = [ultima_data + relativedelta(months=i+1) for i in range(meses_projecao)]
    
    resultado = pd.DataFrame({
        'data': datas_futuras,
        'valor_projetado': projecoes
    })
    
    return resultado


# ==================== Aggregated Historical Data ====================

def obter_dados_historicos_agregados(
    seq_qualificadores: List[int],
    data_inicio: date,
    data_fim: date,
    agregacao: str = 'mensal'
) -> pd.DataFrame:
    """
    Obtém dados históricos agregados de múltiplos qualificadores.
    
    Args:
        seq_qualificadores: Lista de IDs de qualificadores
        data_inicio: Data inicial do período
        data_fim: Data final do período
        agregacao: 'mensal' ou 'diario'
    
    Returns:
        DataFrame com colunas: data, valor (agregado de todos os qualificadores)
    """
    if not seq_qualificadores:
        return pd.DataFrame(columns=['data', 'valor'])
    
    # Buscar lançamentos de todos os qualificadores
    lancamentos = (
        Lancamento.query
        .filter(
            Lancamento.seq_qualificador.in_(seq_qualificadores),
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
            'valor': float(lanc.val_lancamento),
            'seq_qualificador': lanc.seq_qualificador
        })
    
    df = pd.DataFrame(data)
    
    # Agregar por data (soma de todos os qualificadores)
    if agregacao == 'mensal':
        df['ano_mes'] = df['data'].apply(lambda x: x.strftime('%Y-%m'))
        df_agregado = df.groupby('ano_mes')['valor'].sum().reset_index()
        df_agregado.columns = ['data', 'valor']
        df_agregado['data'] = pd.to_datetime(df_agregado['data'] + '-01')
        return df_agregado.sort_values('data')
    
    # Diário
    df_agregado = df.groupby('data')['valor'].sum().reset_index()
    return df_agregado.sort_values('data')


def obter_dados_historicos_por_qualificador(
    seq_qualificadores: List[int],
    data_inicio: date,
    data_fim: date,
) -> Dict[int, pd.DataFrame]:
    """
    Obtém dados históricos separados por qualificador.
    
    Args:
        seq_qualificadores: Lista de IDs de qualificadores
        data_inicio: Data inicial do período
        data_fim: Data final do período
    
    Returns:
        Dicionário com seq_qualificador como chave e DataFrame como valor
    """
    resultado = {}
    for seq_q in seq_qualificadores:
        resultado[seq_q] = obter_dados_historicos(seq_q, data_inicio, data_fim)
    return resultado
