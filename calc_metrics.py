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


def annualized_window_return(prices: pd.Series, years: int) -> float | None:
    """Retorno anualizado para a janela dos últimos N anos.
    Devolve None se o fundo não tem histórico suficiente (cobertura
    parcial inflaciona artificialmente o valor anualizado)."""
    prices = prices.dropna()
    if prices.empty:
        return None
    last_date = prices.index[-1]
    start_date = last_date - pd.DateOffset(years=years)
    # Exigir cobertura total da janela (com folga de 30 dias para
    # acomodar fundos que arrancaram a meio do mês).
    if prices.index[0] > start_date + pd.Timedelta(days=30):
        return None
    window = prices[prices.index >= start_date]
    if window.empty:
        return None
    cum = window.iloc[-1] / window.iloc[0] - 1
    return ((1 + cum) ** (1 / years) - 1) * 100


def calc_returns(prices: pd.Series) -> dict:
    """Calcula retornos para YTD, 1a, 3a, 5a, 10a, anualizado, desde início.
    YTD e 1a são cumulativos; 3a/5a/10a são anualizados."""
    prices = prices.dropna().sort_index()
    if prices.empty:
        return {}

    last_date = prices.index[-1]
    year_start = pd.Timestamp(last_date.year, 1, 1)

    ytd = cumulative_return(prices, year_start)
    r_1y = cumulative_return(prices, last_date - pd.DateOffset(years=1))
    r_3y = annualized_window_return(prices, 3)
    r_5y = annualized_window_return(prices, 5)
    r_10y = annualized_window_return(prices, 10)

    first = prices.iloc[0]
    r_since = (prices.iloc[-1] / first - 1) * 100 if first not in (0, None) and np.isfinite(first) else None

    # Retorno anualizado desde o início (CAGR sobre o histórico completo).
    # Usa o número exacto de anos entre a 1ª e a última cotação.
    ann = None
    years_span = None
    if r_since is not None and np.isfinite(r_since):
        days = (prices.index[-1] - prices.index[0]).days
        years_span = days / 365.25
        if years_span >= 0.5:   # <6 meses não faz sentido anualizar
            ann = ((1 + r_since / 100) ** (1 / years_span) - 1) * 100

    def _safe(v, dp=2):
        if v is None or not np.isfinite(v):
            return None
        return round(float(v), dp)

    return {
        "ytd": _safe(ytd),
        "1y": _safe(r_1y),
        "3y": _safe(r_3y),
        "5y": _safe(r_5y),
        "10y": _safe(r_10y),
        "since": _safe(r_since),
        "ann": _safe(ann),
        "ann_years": round(years_span, 1) if years_span else None,
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

    def _safe(v, dp=2):
        if v is None or not np.isfinite(v):
            return None
        return round(float(v), dp)

    return {
        "vol": _safe(vol),
        "sharpe": _safe(sharpe),
        "maxDD": _safe(max_dd),
        "var95": _safe(var95),
        "beta": _safe(beta),
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
    elif period == "10y":
        start = last - pd.DateOffset(years=10)
    else:  # "since" / fallback
        start = prices.index[0]

    window = prices[prices.index >= start]
    if window.empty:
        return {"labels": [], "data": []}

    base = window.iloc[0]
    if not np.isfinite(base) or base == 0:
        return {"labels": [], "data": []}
    normalized = (window / base - 1) * 100
    normalized = normalized.replace([np.inf, -np.inf], np.nan).dropna()

    step = max(1, len(normalized) // 1000)
    sampled = normalized.iloc[::step]

    return {
        "labels": [d.strftime("%Y-%m-%d") for d in sampled.index],
        "data": [round(float(v), 2) for v in sampled.values],
    }
