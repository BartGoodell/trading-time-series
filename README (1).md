
# Trading Time Series Starter (SPY + Macro)

This starter pulls **SPY** daily OHLCV from Yahoo Finance and merges it with **Fed Funds Rate** (FRED) via Nasdaq Data Link. It then engineers a few technical features (Bollinger Bands, RSI, ATR, returns, vol) and saves tidy CSVs you can use for modeling and backtesting.

## Quickstart

```bash
# (optional) create and activate a venv
python -m venv .venv && source .venv/bin/activate  # on Windows: .venv\Scripts\activate

pip install -r requirements.txt

# Optional: set your Nasdaq Data Link (Quandl) key so FRED fetch is smooth
export NDL_API_KEY=YOUR_KEY  # Windows PowerShell: $env:NDL_API_KEY="YOUR_KEY"
```

Run the fetcher:

```bash
python fetch_data.py --start 2015-01-01 --end 2025-01-01 --ticker SPY --out data --quandl_key $NDL_API_KEY
```

Outputs:
- `data/SPY_prices.csv`
- `data/SPY_with_features.csv`

## What’s included
- **Price data** from Yahoo Finance using `yfinance`.
- **Macro feature**: Effective Fed Funds Rate (FRED/DFF daily preferred; FRED/FEDFUNDS monthly fallback, forward-filled).
- **Technical indicators** (via `ta`):
  - Bollinger Bands (20, ±2)
  - RSI(14)
  - ATR(14)
  - 1d/5d returns, 20d annualized volatility

## Next steps (ideas)
- Train ARIMA/Prophet/LSTM baselines on `close` using the engineered features as exogenous variables.
- Backtest a simple **Bollinger+Volume** strategy.
- Add economic calendar events (FOMC/CPI) as features.
- Visualize SHAP values for an XGBoost model trained on features.

## Notes
- If FRED data can’t be fetched (no key or offline), the script still produces price-based features.
- Timezone-naive daily bars; adjust as needed for intraday research.
