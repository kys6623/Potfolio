from __future__ import annotations

from flask import Blueprint, current_app, flash, jsonify, redirect, render_template, request, url_for

from .db import delete_asset, fetch_assets, init_db, insert_asset, update_asset
from .real_estate_data import RealEstateLookupError, search_apartment_candidates
from .services import (
    create_cash_krw_asset,
    create_cash_usd_asset,
    create_gold_asset,
    create_real_estate_asset,
    create_stock_asset,
    evaluate_portfolio,
)

dashboard_bp = Blueprint("dashboard", __name__)


@dashboard_bp.before_app_request
def ensure_schema() -> None:
    """
    Ensure table exists before handling requests.
    Lightweight and safe thanks to IF NOT EXISTS.
    """
    init_db()


@dashboard_bp.route("/", methods=["GET"])
def dashboard():
    """
    Main dashboard:
    - Reads assets from DB
    - Evaluates current market value
    - Renders mobile-friendly dashboard
    """
    assets = fetch_assets()

    # Handle first-run / empty DB gracefully.
    if not assets:
        return render_template(
            "dashboard.html",
            portfolio={
                "assets": [],
                "usdkrw": 0,
                "gold_per_gram_krw": 0,
                "totals": {"risk": 0, "safe": 0, "cash": 0, "real_estate": 0, "all": 0},
                "ratios": {"risk": 0, "safe": 0, "cash": 0, "real_estate": 0},
            },
        )

    try:
        portfolio = evaluate_portfolio(assets)
    except Exception as exc:
        flash(f"시세 조회 중 오류가 발생했습니다: {exc}", "error")
        # Fallback with zeros, but still show saved assets.
        portfolio = {
            "assets": [{**asset, "unit_price_krw": 0, "value_krw": 0, "market_label": "N/A"} for asset in assets],
            "usdkrw": 0,
            "gold_per_gram_krw": 0,
            "totals": {"risk": 0, "safe": 0, "cash": 0, "real_estate": 0, "all": 0},
            "ratios": {"risk": 0, "safe": 0, "cash": 0, "real_estate": 0},
        }

    return render_template("dashboard.html", portfolio=portfolio)


@dashboard_bp.route("/assets", methods=["POST"])
def add_asset():
    """
    Asset create endpoint.
    One endpoint handles all asset forms by `asset_type`.
    """
    asset_type = request.form.get("asset_type", "").strip()

    try:
        if asset_type == "STOCK":
            payload = create_stock_asset(
                symbol=request.form.get("symbol", ""),
                quantity=float(request.form.get("quantity", "0")),
            )
        elif asset_type == "GOLD":
            payload = create_gold_asset(grams=float(request.form.get("grams", "0")))
        elif asset_type == "CASH_KRW":
            payload = create_cash_krw_asset(amount_krw=float(request.form.get("amount_krw", "0")))
        elif asset_type == "CASH_USD":
            payload = create_cash_usd_asset(amount_usd=float(request.form.get("amount_usd", "0")))
        elif asset_type == "REAL_ESTATE":
            manual_price_raw = request.form.get("manual_price_krw", "").strip()
            payload = create_real_estate_asset(
                apartment_name=request.form.get("apartment_name", ""),
                area_m2=float(request.form.get("area_m2", "0")),
                region_code=request.form.get("region_code", ""),
                manual_price_krw=float(manual_price_raw) if manual_price_raw else None,
            )
        else:
            raise ValueError("지원하지 않는 자산 유형입니다.")

        insert_asset(
            asset_type=payload["asset_type"],
            symbol=payload["symbol"],
            name=payload["name"],
            quantity=payload["quantity"],
            meta=payload.get("meta"),
        )
        flash("자산이 저장되었습니다.", "success")
    except ValueError as exc:
        flash(str(exc), "error")
    except Exception as exc:
        flash(f"저장 중 오류가 발생했습니다: {exc}", "error")

    return redirect(url_for("dashboard.dashboard"))


@dashboard_bp.route("/assets/<int:asset_id>/delete", methods=["POST"])
def remove_asset(asset_id: int):
    """
    Remove one asset entry.
    """
    delete_asset(asset_id)
    flash("자산이 삭제되었습니다.", "success")
    return redirect(url_for("dashboard.dashboard"))


@dashboard_bp.route("/assets/<int:asset_id>/update", methods=["POST"])
def edit_asset(asset_id: int):
    """
    Update quantity and note for an asset from modal form.
    """
    try:
        quantity = float(request.form.get("quantity", "0"))
        note = (request.form.get("note", "") or "").strip() or None
        if quantity <= 0:
            raise ValueError("수량/금액은 0보다 커야 합니다.")
        update_asset(asset_id=asset_id, quantity=quantity, note=note)
        flash("자산이 수정되었습니다.", "success")
    except ValueError as exc:
        flash(str(exc), "error")
    except Exception as exc:
        flash(f"수정 중 오류가 발생했습니다: {exc}", "error")
    return redirect(url_for("dashboard.dashboard"))


@dashboard_bp.route("/api/apartments/search", methods=["GET"])
def search_apartments_api():
    """
    Apartment search API for modal picker in UI.
    Requires region_code and query text.
    """
    region_code = request.args.get("region_code", "").strip()
    query = request.args.get("q", "").strip()
    api_key = str(current_app.config.get("MOLIT_API_KEY", "")).strip()

    try:
        items = search_apartment_candidates(
            api_key=api_key,
            region_code=region_code,
            query=query,
        )
        return jsonify({"ok": True, "items": items})
    except RealEstateLookupError as exc:
        return jsonify({"ok": False, "error": str(exc), "items": []}), 400
    except Exception as exc:
        return jsonify({"ok": False, "error": f"조회 중 오류: {exc}", "items": []}), 500
