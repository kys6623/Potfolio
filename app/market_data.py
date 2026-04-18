from __future__ import annotations

from dataclasses import dataclass

import yfinance as yf


@dataclass
class Quote:
    price: float
    currency: str


def _candidate_symbols(symbol: str) -> list[str]:
    """
    Build ticker candidates for KR/US symbols.
    Example: 005930 -> [005930.KS, 005930.KQ, 005930]
    """
    cleaned = symbol.strip().upper()
    if cleaned.isdigit() and len(cleaned) == 6:
        return [f"{cleaned}.KS", f"{cleaned}.KQ", cleaned]
    return [cleaned]


def _safe_last_price(ticker: yf.Ticker) -> float:
    """
    Best-effort price extraction from yfinance.
    The API can be inconsistent depending on market/session status,
    so we try multiple sources in fallback order.
    """
    fast_info = None
    try:
        fast_info = getattr(ticker, "fast_info", None)
    except Exception:
        fast_info = None
    if fast_info:
        for key in ("lastPrice", "regularMarketPrice", "previousClose"):
            try:
                value = fast_info.get(key)
                if value:
                    return float(value)
            except Exception:
                continue

    # Fallback: use recent daily candle close.
    try:
        hist = ticker.history(period="5d")
        if not hist.empty:
            return float(hist["Close"].dropna().iloc[-1])
    except Exception:
        pass

    raise ValueError("Price data unavailable")


def get_stock_quote(symbol: str) -> tuple[str, Quote]:
    """
    Return (display_name, quote) for a stock ticker.
    """
    last_error = ""
    for candidate in _candidate_symbols(symbol):
        ticker = yf.Ticker(candidate)
        try:
            price = _safe_last_price(ticker)
        except Exception as exc:
            last_error = str(exc)
            continue

        info = {}
        try:
            info = ticker.info or {}
        except Exception:
            info = {}

        display_name = info.get("longName") or info.get("shortName") or candidate
        currency = info.get("currency", "KRW" if candidate.endswith((".KS", ".KQ")) else "USD")
        return display_name, Quote(price=price, currency=currency)

    raise ValueError(f"주식 시세 조회 실패: {symbol} ({last_error or '지원되지 않는 티커'})")


def get_usdkrw_rate() -> float:
    """
    USD/KRW exchange rate using Yahoo symbol KRW=X.
    Note: KRW=X returns KRW per 1 USD.
    """
    ticker = yf.Ticker("KRW=X")
    return _safe_last_price(ticker)


def get_gold_price_per_gram_usd() -> float:
    """
    Approximate gold spot price per gram in USD from GC=F futures.
    GC=F quote is USD per troy ounce, so convert with:
    1 troy ounce = 31.1034768 grams.
    """
    ticker = yf.Ticker("GC=F")
    usd_per_oz = _safe_last_price(ticker)
    return usd_per_oz / 31.1034768
