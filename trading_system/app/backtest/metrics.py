import numpy as np
import pandas as pd


def performance_metrics(equity_curve: pd.Series, benchmark: pd.Series | None = None, turnover: float = 0.0, trades: int = 0, wins: int = 0) -> dict[str, float]:
    returns = equity_curve.pct_change().fillna(0.0)
    total_years = max((equity_curve.index[-1] - equity_curve.index[0]).days / 365.25, 1 / 365.25)
    cagr = (equity_curve.iloc[-1] / equity_curve.iloc[0]) ** (1 / total_years) - 1
    running_max = equity_curve.cummax()
    drawdown = equity_curve / running_max - 1
    mdd = float(drawdown.min())
    sharpe = float(np.sqrt(252) * returns.mean() / returns.std(ddof=0)) if returns.std(ddof=0) else 0.0
    downside = returns[returns < 0].std(ddof=0)
    sortino = float(np.sqrt(252) * returns.mean() / downside) if downside else 0.0
    calmar = float(cagr / abs(mdd)) if mdd else 0.0
    information = 0.0
    if benchmark is not None and not benchmark.empty:
        aligned = benchmark.reindex(equity_curve.index).ffill().pct_change().fillna(0.0)
        active = returns - aligned
        information = float(np.sqrt(252) * active.mean() / active.std(ddof=0)) if active.std(ddof=0) else 0.0
    return {
        "CAGR": float(cagr),
        "MDD": mdd,
        "Sharpe Ratio": sharpe,
        "Sortino Ratio": sortino,
        "Calmar Ratio": calmar,
        "Information Ratio": information,
        "Turnover": float(turnover),
        "Win Rate": float(wins / trades) if trades else 0.0,
        "Trades": float(trades),
    }


def annual_monthly_report(equity_curve: pd.Series) -> dict[str, dict[str, float]]:
    returns = equity_curve.pct_change().fillna(0.0)
    annual = returns.groupby(returns.index.year).apply(lambda x: (1 + x).prod() - 1).to_dict()
    monthly = returns.groupby([returns.index.year, returns.index.month]).apply(lambda x: (1 + x).prod() - 1).to_dict()
    return {
        "annual_returns": {str(k): float(v) for k, v in annual.items()},
        "monthly_returns": {f"{k[0]}-{k[1]:02d}": float(v) for k, v in monthly.items()},
    }
