from __future__ import annotations

import json
from typing import Any

from flask import current_app

from .market_data import (
    get_gold_price_per_gram_usd,
    get_stock_quote,
    get_usdkrw_rate,
)
from .real_estate_data import RealEstateLookupError, lookup_apartment_trade_price


def create_stock_asset(symbol: str, quantity: float) -> dict[str, Any]:
    """
    Build normalized stock asset payload.
    Auto-fills stock name from yfinance based on ticker.
    """
    cleaned_symbol = symbol.strip().upper()
    if not cleaned_symbol:
        raise ValueError("주식 티커를 입력해 주세요.")
    if quantity <= 0:
        raise ValueError("주식 수량은 0보다 커야 합니다.")

    name, _quote = get_stock_quote(cleaned_symbol)
    return {
        "asset_type": "STOCK",
        "symbol": cleaned_symbol,
        "name": name,
        "quantity": quantity,
    }


def create_gold_asset(grams: float) -> dict[str, Any]:
    """
    Build normalized gold asset payload (stored as grams).
    """
    if grams <= 0:
        raise ValueError("금 중량은 0보다 커야 합니다.")
    return {
        "asset_type": "GOLD",
        "symbol": "GC=F",
        "name": "Gold (g)",
        "quantity": grams,
    }


def create_cash_krw_asset(amount_krw: float) -> dict[str, Any]:
    """
    Build normalized KRW cash payload.
    """
    if amount_krw <= 0:
        raise ValueError("현금 금액은 0보다 커야 합니다.")
    return {
        "asset_type": "CASH_KRW",
        "symbol": "KRW",
        "name": "Cash (KRW)",
        "quantity": amount_krw,
    }


def create_cash_usd_asset(amount_usd: float) -> dict[str, Any]:
    """
    Build normalized USD cash payload.
    """
    if amount_usd <= 0:
        raise ValueError("달러 금액은 0보다 커야 합니다.")
    return {
        "asset_type": "CASH_USD",
        "symbol": "USD",
        "name": "Cash (USD)",
        "quantity": amount_usd,
    }


def create_real_estate_asset(
    apartment_name: str,
    area_m2: float,
    region_code: str,
    manual_price_krw: float | None = None,
) -> dict[str, Any]:
    """
    Build normalized real-estate payload.
    - Tries MOLIT API lookup first (when key is configured).
    - Falls back to manual_price_krw when API is unavailable/no match.
    """
    cleaned_name = apartment_name.strip()
    if not cleaned_name:
        raise ValueError("아파트명을 입력해 주세요.")
    if area_m2 <= 0:
        raise ValueError("전용면적은 0보다 커야 합니다.")
    cleaned_region_code = region_code.strip()
    if not cleaned_region_code:
        raise ValueError("실거래가 자동조회를 위해 지역코드(5자리)를 입력해 주세요. 예: 11680")

    api_key = str(current_app.config.get("MOLIT_API_KEY", "")).strip()
    if not api_key:
        raise ValueError("MOLIT_API_KEY가 설정되지 않았습니다. 터미널에서 환경변수를 먼저 설정해 주세요.")

    estimated_price = 0.0
    market_label = ""
    matched_name = cleaned_name
    lookup_error_detail = ""

    try:
        result = lookup_apartment_trade_price(
            api_key=api_key,
            region_code=cleaned_region_code,
            apartment_name=cleaned_name,
            area_m2=area_m2,
        )
        estimated_price = float(result["deal_price_krw"])
        matched_name = result["apartment_name"]
        market_label = f"실거래가 {result['deal_date']} · {result['jibun']}"
    except RealEstateLookupError as exc:
        lookup_error_detail = str(exc)

    if estimated_price <= 0:
        if manual_price_krw is None or manual_price_krw <= 0:
            if lookup_error_detail:
                raise ValueError(
                    f"실거래가 자동조회 실패: {lookup_error_detail} / 수동 실거래가(원)를 입력해 주세요."
                )
            raise ValueError("실거래가 자동조회에 실패했습니다. 수동 실거래가(원)를 입력해 주세요.")
        estimated_price = manual_price_krw
        market_label = "사용자 입력 실거래가"
        if lookup_error_detail:
            market_label += f" (자동조회 실패: {lookup_error_detail})"

    return {
        "asset_type": "REAL_ESTATE",
        "symbol": cleaned_region_code or "APT",
        "name": f"{matched_name} ({area_m2:.2f}m2)",
        # For real-estate assets, quantity keeps appraised value (KRW).
        "quantity": estimated_price,
        "meta": json.dumps(
            {
                "apartment_name": matched_name,
                "area_m2": area_m2,
                "estimated_price_krw": estimated_price,
                "market_label": market_label,
                "region_code": cleaned_region_code,
            },
            ensure_ascii=False,
        ),
    }


def evaluate_portfolio(assets: list[dict[str, Any]]) -> dict[str, Any]:
    """
    Evaluate all saved assets using near real-time market data.

    Base currency for dashboard output is KRW.
    Category mapping:
    - STOCK   -> 위험자산
    - GOLD    -> 안전자산
    - CASH_*  -> 현금성 자산
    - REAL_ESTATE -> 부동산
    """
    usdkrw = get_usdkrw_rate()
    gold_per_gram_usd = get_gold_price_per_gram_usd()
    gold_per_gram_krw = gold_per_gram_usd * usdkrw

    risk_total = 0.0
    safe_total = 0.0
    cash_total = 0.0
    real_estate_total = 0.0
    evaluated_assets: list[dict[str, Any]] = []

    for asset in assets:
        asset_type = asset["asset_type"]
        quantity = float(asset["quantity"])
        unit_price_krw = 0.0
        market_label = ""

        if asset_type == "STOCK":
            _, quote = get_stock_quote(asset["symbol"])
            # If stock is quoted in USD, convert to KRW for unified dashboard.
            if quote.currency.upper() == "USD":
                unit_price_krw = quote.price * usdkrw
                market_label = f"{quote.price:,.2f} USD"
            else:
                unit_price_krw = quote.price
                market_label = f"{quote.price:,.2f} {quote.currency}"
            value_krw = quantity * unit_price_krw
            risk_total += value_krw

        elif asset_type == "GOLD":
            unit_price_krw = gold_per_gram_krw
            market_label = f"{gold_per_gram_usd:,.2f} USD/g"
            value_krw = quantity * unit_price_krw
            safe_total += value_krw

        elif asset_type == "CASH_USD":
            # USD cash is converted to KRW for total valuation.
            unit_price_krw = usdkrw
            market_label = f"1 USD = {usdkrw:,.2f} KRW"
            value_krw = quantity * unit_price_krw
            cash_total += value_krw

        elif asset_type == "REAL_ESTATE":
            # Real-estate quantity stores the latest known appraised KRW.
            unit_price_krw = quantity
            value_krw = quantity
            real_estate_total += value_krw
            market_label = "실거래가 기준"

            meta_text = asset.get("meta") or ""
            if meta_text:
                try:
                    meta = json.loads(meta_text)
                    market_label = meta.get("market_label", market_label)
                except Exception:
                    pass

        else:  # CASH_KRW
            unit_price_krw = 1.0
            market_label = "KRW"
            value_krw = quantity
            cash_total += value_krw

        evaluated_assets.append(
            {
                **asset,
                "unit_price_krw": unit_price_krw,
                "value_krw": value_krw,
                "market_label": market_label,
            }
        )

    total_assets = risk_total + safe_total + cash_total
    total_assets += real_estate_total

    def pct(value: float) -> float:
        return (value / total_assets * 100) if total_assets > 0 else 0.0

    return {
        "assets": evaluated_assets,
        "usdkrw": usdkrw,
        "gold_per_gram_krw": gold_per_gram_krw,
        "totals": {
            "risk": risk_total,
            "safe": safe_total,
            "cash": cash_total,
            "real_estate": real_estate_total,
            "all": total_assets,
        },
        "ratios": {
            "risk": pct(risk_total),
            "safe": pct(safe_total),
            "cash": pct(cash_total),
            "real_estate": pct(real_estate_total),
        },
    }
