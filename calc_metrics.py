"""
Calculo de metricas a partir das cotacoes historicas.

Retornos:
- YTD, 1a, 3a, 5a (cumulativos)
- Anualizado (5a)

Risco:
- Volatilidade anualizada (std dos retornos diarios * sqrt(252))
- Sharpe ratio (assume risk-free rate = Euribor 12m ou 2.5% default)
- Max drawdown
- VaR 95% diario (percentil 5 dos retornos)
- Beta vs benchmark (MSCI World EUR por default)
"""
import numpy as np
import pandas as pd
from datetime import datetime, timedelta

RISK_FREE_RATE = 0.025  # 2.5% anual - ajustar para Euribor 12m real
TRADING_DAYS = 252


def cumulative_return(prices: pd.Series, start_date: pd.Timestamp) -> float | None:
    """Retorno cumulativo desde start_date até ao último valor."""
    prices = prices.dropna()
    if prices.empty:
        return None
    # primeira cotacao após start_date
    window = prices[prices.index >= start_date]
    if window.empty:
        return None
    start_price = window.iloc[0]
    end_price = prices.iloc[-1]
    return (end_price / start_price - 1) * 100


def calc_returns(prices: pd.Series) -> dict:
    """Calcula retornos para YTD, 1a, 3a, 5a, anualizado."""
    prices = prices.dropna().sort_index()
    if prices.empty:
        return {}

    last_date = prices.index[-1]
    year_start = pd.Timestamp(last_date.year, 1, 1)

    ytd = cumulative_return(prices, year_start)
    r_1y = cumulative_return(prices, last_date - pd.DateOffset(years=1))
    r_3y = cumulative_return(prices, last_date - pd.DateOffset(years=3))
    r_5y = cumulative_return(prices, last_date - pd.DateOffset(years=5))

    ann = None
    if r_5y is not None:
        ann = ((1 + r_5y / 100) ** (1 / 5) - 1) * 100

    return {
        "ytd": round(ytd, 2) if ytd is not None else None,
        "1y": round(r_1y, 2) if r_1y is not None else None,
        "3y": round(r_3y, 2) if r_3y is not None else None,
        "5y": round(r_5y, 2) if r_5y is not None else None,
        "ann": round(ann, 2) if ann is not None else None,
    }


def calc_risk(prices: pd.Series, benchmark: pd.Series | None = None) -> dict:
    """Calcula métricas de risco."""
    prices = prices.dropna().sort_index()
    if len(prices) < 30:
        return {}

    returns = prices.pct_change().dropna()

    # Volatilidade anualizada
    vol = returns.std() * np.sqrt(TRADING_DAYS) * 100

    # Sharpe
    excess = returns.mean() * TRADING_DAYS - RISK_FREE_RATE
    sharpe = excess / (returns.std() * np.sqrt(TRADING_DAYS)) if returns.std() > 0 else 0

    # Max drawdown
    cum = (1 + returns).cumprod()
    running_max = cum.cummax()
    drawdown = (cum - running_max) / running_max
    max_dd = drawdown.min() * 100

    # VaR 95% diario
    var95 = np.percentile(returns, 5) * 100

    # Beta vs benchmark
    beta = None
    if benchmark is not None and not benchmark.empty:
        bench_ret = benchmark.pct_change().dropna()
        aligned = pd.concat([returns, bench_ret], axis=1, join="inner").dropna()
        if len(aligned) > 30:
            cov = aligned.cov().iloc[0, 1]
            var_bench = aligned.iloc[:, 1].var()
            beta = cov / var_bench if var_bench > 0 else None

    return {
        "vol": round(vol, 2),
        "sharpe": round(sharpe, 2),
        "maxDD": round(max_dd, 2),
        "var95": round(var95, 2),
        "beta": round(beta, 2) if beta is not None else None,
    }


def build_chart_series(prices: pd.Series, period: str) -> dict:
    """
    Gera serie normalizada para o grafico (base 100 no inicio do periodo).
    Retorna {labels: [YYYY-MM-DD], data: [float]}
    """
    prices = prices.dropna().sort_index()
    if prices.empty:
        return {"labels": [], "data": []}

    last = prices.index[-1]
    if period == "ytd":
        start = pd.Timestamp(last.year, 1, 1)
    elif period == "1y":
        start = last - pd.DateOffset(years=1)
    elif period == "3y":
        start = last - pd.DateOffset(years=3)
    elif period == "5y":
        start = last - pd.DateOffset(years=5)
    else:
        start = prices.index[0]

    window = prices[prices.index >= start]
    if window.empty:
        return {"labels": [], "data": []}

    base = window.iloc[0]
    normalized = (window / base - 1) * 100

    # Downsample para o grafico (max ~250 pontos)
    step = max(1, len(normalized) // 250)
    sampled = normalized.iloc[::step]

    return {
        "labels": [d.strftime("%Y-%m-%d") for d in sampled.index],
        "data": [round(v, 2) for v in sampled.values],
    }
