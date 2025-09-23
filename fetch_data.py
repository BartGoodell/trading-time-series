#!/usr/bin/env python3
"""
Fetch SPY daily OHLCV from Yahoo Finance and merge with macro series from FRED (via Nasdaq Data Link),
then engineer a few technical features and save tidy CSVs ready for modeling/backtesting.

Usage:
    python fetch_data.py --start 2015-01-01 --end 2025-01-01 --ticker SPY --out data
"""
import argparse
from datetime import datetime
import pandas as pd

# yfinance for price data
try:
    import yfinance as yf
except ImportError as e:
    raise SystemExit("Please `pip install yfinance nasdaqdatalink ta` before running.")

# nasdaqdatalink (Quandl) for macro data like Fed Funds
import nasdaqdatalink

# optional indicators (RSI, Bollinger, ATR) using 'ta' package
try:
    import ta
except ImportError:
    ta = None
    print("Warning: package `ta` not installed; skipping indicator features. Install with `pip install ta`.")

def fetch_prices(ticker: str, start: str, end: str, interval: str = "1d"):
    df = yf.download(ticker, start=start, end=end, interval=interval, auto_adjust=False, progress=False)
    if df.empty:
        raise RuntimeError(f"No price data returned for {ticker}.")
    df = df.rename(columns=str.lower)
    df.index = pd.to_datetime(df.index).tz_localize(None)
    df["ticker"] = ticker
    return df

def fetch_fed_funds(api_key: str | None = None):
    """Pull Effective Federal Funds Rate from FRED.
    Primary: FRED/FEDFUNDS (monthly). Alternative daily series: FRED/DFF (Daily Fed Funds).
    We prioritize FRED/DFF if available; otherwise fallback to FEDFUNDS monthly and forward-fill.
    """
    if api_key:
        nasdaqdatalink.ApiConfig.api_key = api_key
    # Try daily first
    try:
        dff = nasdaqdatalink.get("FRED/DFF")
        dff = dff.rename(columns={"Value": "fed_funds_daily"})
    except Exception:
        dff = None
    # Monthly series as fallback
    try:
        fed = nasdaqdatalink.get("FRED/FEDFUNDS")
        fed = fed.rename(columns={"Value": "fed_funds_monthly"})
    except Exception:
        fed = None

    if dff is None and fed is None:
        raise RuntimeError("Could not fetch Fed Funds from FRED. Check your internet/API setup.")

    out = None
    if dff is not None:
        out = dff
    if fed is not None:
        if out is None:
            out = fed
        else:
            out = out.join(fed, how="outer")
    out.index = pd.to_datetime(out.index)
    out = out.sort_index()
    # Build a single fed_funds column by preferring daily, then monthly
    out["fed_funds"] = out["fed_funds_daily"].combine_first(out["fed_funds_monthly"])
    # forward-fill for daily alignment later
    out["fed_funds"] = out["fed_funds"].ffill()
    return out[["fed_funds"]]

def add_indicators(df):
    if ta is None:
        return df
    # Bollinger Bands (20)
    bb = ta.volatility.BollingerBands(close=df["close"], window=20, window_dev=2)
    df["bb_mavg"] = bb.bollinger_mavg()
    df["bb_high"] = bb.bollinger_hband()
    df["bb_low"]  = bb.bollinger_lband()
    # RSI(14)
    df["rsi_14"] = ta.momentum.RSIIndicator(close=df["close"], window=14).rsi()
    # ATR(14)
    df["atr_14"] = ta.volatility.AverageTrueRange(high=df["high"], low=df["low"], close=df["close"], window=14).average_true_range()
    # Rolling returns & volatility
    df["ret_1d"] = df["close"].pct_change(1)
    df["ret_5d"] = df["close"].pct_change(5)
    df["vol_20d"] = df["ret_1d"].rolling(20).std() * (252 ** 0.5)
    return df

def main():
    p = argparse.ArgumentParser()
    p.add_argument("--start", default="2015-01-01")
    p.add_argument("--end", default=datetime.today().strftime("%Y-%m-%d"))
    p.add_argument("--ticker", default="SPY")
    p.add_argument("--out", default="data")
    p.add_argument("--quandl_key", default=None, help="Nasdaq Data Link (Quandl) API key for FRED data (optional).")
    args = p.parse_args()

    import os
    os.makedirs(args.out, exist_ok=True)

    prices = fetch_prices(args.ticker, args.start, args.end, "1d")
    prices = prices.sort_index()

    # Technical indicators
    prices = add_indicators(prices)

    # Macro
    try:
        fed = fetch_fed_funds(api_key=args.quandl_key)
    except Exception as e:
        print(f"Warning: Fed Funds not fetched ({e}); continuing without macro.")
        fed = None

    # Merge on date
    if fed is not None:
        merged = prices.join(fed, how="left")
        # forward-fill macro to business days
        merged["fed_funds"] = merged["fed_funds"].ffill()
    else:
        merged = prices

    # Tidy columns
    merged.reset_index(inplace=True)
    merged.rename(columns={"index": "date"}, inplace=True)
    merged["date"] = pd.to_datetime(merged["date"]).dt.date

    # Save
    prices.to_csv(f"{args.out}/{args.ticker}_prices.csv", index=False)
    merged.to_csv(f"{args.out}/{args.ticker}_with_features.csv", index=False)
    print(f"Saved:\\n- {args.out}/{args.ticker}_prices.csv\\n- {args.out}/{args.ticker}_with_features.csv")

if __name__ == "__main__":
    main()
