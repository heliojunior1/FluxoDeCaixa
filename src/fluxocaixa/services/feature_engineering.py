"""Feature engineering module for ML-based time series forecasting models."""

import numpy as np
import pandas as pd
from typing import Optional


def criar_features_serie_temporal(df: pd.DataFrame) -> pd.DataFrame:
    """
    Generates features from a time series DataFrame for ML model training.
    
    Args:
        df: DataFrame with columns 'data' (datetime) and 'valor' (float)
    
    Returns:
        DataFrame with original data plus engineered features:
        - mes: month (1-12)
        - mes_sin, mes_cos: cyclical month encoding
        - ano: year
        - trimestre: quarter (1-4)
        - tendencia: sequential position (trend)
        - lag_1 to lag_12: lagged values
        - media_movel_3, media_movel_6, media_movel_12: rolling means
        - std_movel_3: rolling standard deviation (3 months)
        - variacao_mensal: month-over-month percentage change
        - variacao_anual: year-over-year percentage change (lag 12)
    """
    df = df.copy()
    df = df.sort_values('data').reset_index(drop=True)
    
    # Ensure datetime
    df['data'] = pd.to_datetime(df['data'])
    
    # Calendar features
    df['mes'] = df['data'].dt.month
    df['ano'] = df['data'].dt.year
    df['trimestre'] = df['data'].dt.quarter
    
    # Cyclical encoding of month (helps ML models understand month circularity)
    df['mes_sin'] = np.sin(2 * np.pi * df['mes'] / 12)
    df['mes_cos'] = np.cos(2 * np.pi * df['mes'] / 12)
    
    # Trend (sequential position)
    df['tendencia'] = np.arange(len(df))
    
    # Lag features (previous months' values)
    for lag in range(1, 13):
        df[f'lag_{lag}'] = df['valor'].shift(lag)
    
    # Rolling statistics
    df['media_movel_3'] = df['valor'].rolling(window=3, min_periods=1).mean()
    df['media_movel_6'] = df['valor'].rolling(window=6, min_periods=1).mean()
    df['media_movel_12'] = df['valor'].rolling(window=12, min_periods=1).mean()
    df['std_movel_3'] = df['valor'].rolling(window=3, min_periods=1).std().fillna(0)
    
    # Percentage changes
    df['variacao_mensal'] = df['valor'].pct_change().fillna(0)
    df['variacao_anual'] = df['valor'].pct_change(periods=12).fillna(0)
    
    return df


def get_feature_columns() -> list:
    """Returns the list of feature column names used for training."""
    return [
        'mes', 'mes_sin', 'mes_cos', 'ano', 'trimestre', 'tendencia',
        'lag_1', 'lag_2', 'lag_3', 'lag_4', 'lag_5', 'lag_6',
        'lag_7', 'lag_8', 'lag_9', 'lag_10', 'lag_11', 'lag_12',
        'media_movel_3', 'media_movel_6', 'media_movel_12', 'std_movel_3',
        'variacao_mensal', 'variacao_anual',
    ]


def criar_features_futuras(
    df_historico_com_features: pd.DataFrame,
    meses_projecao: int,
    ano_base: Optional[int] = None,
) -> pd.DataFrame:
    """
    Creates feature rows for future months, using recursive prediction approach.
    
    This generates the initial future feature set. During prediction, lag values
    will be updated recursively as each month is predicted.
    
    Args:
        df_historico_com_features: Historical data with features already computed
        meses_projecao: Number of months to project
        ano_base: Base year for projection (default: next year after last data point)
    
    Returns:
        DataFrame with feature columns for future months
    """
    from datetime import date
    
    df = df_historico_com_features.copy()
    ultimos_valores = df['valor'].values  # Full historical values for lags
    ultimo_idx = df['tendencia'].max()
    
    if ano_base is None:
        ultima_data = df['data'].max()
        ano_base = ultima_data.year + 1
    
    futures = []
    
    for i in range(meses_projecao):
        mes = (i % 12) + 1
        ano = ano_base + (i // 12)
        
        row = {
            'data': pd.Timestamp(date(ano, mes, 1)),
            'mes': mes,
            'mes_sin': np.sin(2 * np.pi * mes / 12),
            'mes_cos': np.cos(2 * np.pi * mes / 12),
            'ano': ano,
            'trimestre': (mes - 1) // 3 + 1,
            'tendencia': ultimo_idx + 1 + i,
        }
        
        # Lag features from historical data
        n_hist = len(ultimos_valores)
        for lag in range(1, 13):
            idx = n_hist - lag + i  # Offset by future position
            if idx >= 0 and idx < n_hist:
                row[f'lag_{lag}'] = ultimos_valores[idx] if (i - lag + 1) <= 0 else 0
            else:
                row[f'lag_{lag}'] = 0
        
        # For initial future rows, use last known rolling stats
        if len(df) >= 3:
            row['media_movel_3'] = float(df['valor'].tail(3).mean())
        else:
            row['media_movel_3'] = float(df['valor'].mean())
            
        if len(df) >= 6:
            row['media_movel_6'] = float(df['valor'].tail(6).mean())
        else:
            row['media_movel_6'] = float(df['valor'].mean())
            
        if len(df) >= 12:
            row['media_movel_12'] = float(df['valor'].tail(12).mean())
        else:
            row['media_movel_12'] = float(df['valor'].mean())
        
        row['std_movel_3'] = float(df['valor'].tail(3).std()) if len(df) >= 3 else 0
        row['variacao_mensal'] = 0
        row['variacao_anual'] = 0
        
        futures.append(row)
    
    return pd.DataFrame(futures)


def preparar_dados_treino(df_com_features: pd.DataFrame):
    """
    Prepares training data by dropping rows with NaN in lag columns
    and splitting into X (features) and y (target).
    
    Args:
        df_com_features: DataFrame with features from criar_features_serie_temporal()
    
    Returns:
        Tuple (X, y) where X is features DataFrame and y is target Series
    """
    feature_cols = get_feature_columns()
    
    # Drop rows where lag features are NaN (first 12 rows typically)
    df_train = df_com_features.dropna(subset=[c for c in feature_cols if c in df_com_features.columns])
    
    # Ensure all feature columns exist
    for col in feature_cols:
        if col not in df_train.columns:
            df_train[col] = 0
    
    X = df_train[feature_cols].copy()
    y = df_train['valor'].copy()
    
    # Replace any remaining infinities or NaN
    X = X.replace([np.inf, -np.inf], 0).fillna(0)
    
    return X, y


def atualizar_lags_recursivo(
    row_futuro: dict,
    valores_previstos: list,
    valores_historicos: np.ndarray,
    indice_futuro: int,
) -> dict:
    """
    Updates lag features for recursive prediction.
    
    When predicting month N+k, lag_1 should be the prediction for month N+k-1,
    lag_2 should be the prediction for N+k-2, etc.
    
    Args:
        row_futuro: Feature row dict for the future month being predicted
        valores_previstos: List of already predicted values (for months 0 to k-1)
        valores_historicos: Array of historical 'valor' values
        indice_futuro: Current future index (0-based)
    
    Returns:
        Updated row dict with correct lag values
    """
    row = row_futuro.copy()
    n_hist = len(valores_historicos)
    n_prev = len(valores_previstos)
    
    for lag in range(1, 13):
        offset = indice_futuro - lag + 1
        if offset >= 0 and offset < n_prev:
            # Use previously predicted value
            row[f'lag_{lag}'] = valores_previstos[offset]
        else:
            # Use historical value
            hist_idx = n_hist + offset - 1
            if 0 <= hist_idx < n_hist:
                row[f'lag_{lag}'] = valores_historicos[hist_idx]
            else:
                row[f'lag_{lag}'] = 0
    
    # Update rolling statistics using mix of historical and predicted
    all_values = list(valores_historicos) + list(valores_previstos)
    if len(all_values) >= 3:
        row['media_movel_3'] = np.mean(all_values[-3:])
    if len(all_values) >= 6:
        row['media_movel_6'] = np.mean(all_values[-6:])
    if len(all_values) >= 12:
        row['media_movel_12'] = np.mean(all_values[-12:])
    if len(all_values) >= 3:
        row['std_movel_3'] = np.std(all_values[-3:])
    
    # Update percentage changes
    if len(all_values) >= 2 and all_values[-2] != 0:
        row['variacao_mensal'] = (all_values[-1] - all_values[-2]) / abs(all_values[-2])
    else:
        row['variacao_mensal'] = 0
    
    if len(all_values) >= 13 and all_values[-13] != 0:
        row['variacao_anual'] = (all_values[-1] - all_values[-13]) / abs(all_values[-13])
    else:
        row['variacao_anual'] = 0
    
    return row
