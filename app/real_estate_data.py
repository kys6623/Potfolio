from __future__ import annotations

import datetime as dt
from typing import Any
from urllib.parse import unquote

import requests


class RealEstateLookupError(Exception):
    """Raised when real-estate trade lookup fails."""


# Major-city sigungu LAWD codes for name-only apartment search.
# (Used when region_code is not provided in the popup search.)
DEFAULT_SEARCH_REGION_CODES = [
    # Seoul
    "11110", "11140", "11170", "11200", "11215", "11230", "11260", "11290", "11305", "11320",
    "11350", "11380", "11410", "11440", "11470", "11500", "11530", "11545", "11560", "11590",
    "11620", "11650", "11680", "11710", "11740",
    # Busan
    "26110", "26140", "26170", "26200", "26230", "26260", "26290", "26320", "26350", "26380",
    "26410", "26440", "26470", "26500", "26530", "26710",
    # Daegu
    "27110", "27140", "27170", "27200", "27230", "27260", "27290", "27710",
    # Incheon
    "28110", "28140", "28177", "28185", "28200", "28237", "28245", "28260", "28710", "28720",
    # Gwangju
    "29110", "29140", "29155", "29170", "29200",
    # Daejeon
    "30110", "30140", "30170", "30200", "30230",
    # Ulsan
    "31110", "31140", "31170", "31200", "31710",
    # Sejong
    "36110",
    # Gyeonggi (major)
    "41111", "41113", "41115", "41117", "41131", "41133", "41135", "41150", "41171", "41173",
    "41190", "41210", "41220", "41250", "41271", "41273", "41281", "41285", "41287", "41290",
    "41310", "41360", "41370", "41390", "41410", "41430", "41450", "41461", "41463", "41465",
    "41480", "41500", "41550", "41570", "41590", "41610", "41630", "41650", "41670",
]

FAST_SEARCH_REGION_CODES = [
    # Seoul core + Gyeonggi large cities for quick first pass
    "11680", "11650", "11710", "11740", "11590", "11215", "11500",
    "41111", "41113", "41115", "41117", "41135", "41220", "41390", "41480",
]


def _service_key_candidates(api_key: str) -> list[str]:
    """
    data.go.kr keys can be copied as either encoded or decoded forms.
    Try both to reduce user setup friction.
    """
    raw = api_key.strip()
    decoded = unquote(raw)
    candidates = [raw]
    if decoded != raw:
        candidates.append(decoded)
    return candidates


def _month_candidates(count: int = 6) -> list[str]:
    """
    Build recent year-month candidates in yyyymm format.
    We query from current month backwards to maximize chance of match.
    """
    today = dt.date.today()
    candidates: list[str] = []
    year, month = today.year, today.month
    for _ in range(count):
        candidates.append(f"{year}{month:02d}")
        month -= 1
        if month == 0:
            month = 12
            year -= 1
    return candidates


def _to_float(value: Any) -> float:
    text = str(value).replace(",", "").strip()
    return float(text) if text else 0.0


def _parse_trade_price_krw(deal_amount_text: str) -> float:
    """
    국토부 API `dealAmount` format: e.g. "145,000" (만원 단위)
    Convert to KRW: 145,000 * 10,000 = 1,450,000,000
    """
    manwon = _to_float(deal_amount_text)
    return manwon * 10_000


def _normalize_apt_name(name: str) -> str:
    """
    Normalize apartment names for resilient matching.
    """
    cleaned = name.strip().replace(" ", "")
    cleaned = cleaned.replace("아파트", "")
    return cleaned


def _region_code_candidates(region_code: str) -> list[str]:
    """
    Return either user-provided region code or default nationwide scan set.
    """
    lawd_cd = region_code.strip()
    if lawd_cd:
        if len(lawd_cd) != 5 or not lawd_cd.isdigit():
            raise RealEstateLookupError("지역코드는 5자리 숫자여야 합니다. 예: 11680")
        return [lawd_cd]
    return DEFAULT_SEARCH_REGION_CODES


def lookup_apartment_trade_price(
    api_key: str,
    region_code: str,
    apartment_name: str,
    area_m2: float,
    search_months: int = 24,
) -> dict[str, Any]:
    """
    Lookup most recent matching apartment trade from MOLIT open API.

    Important constraints:
    - Requires valid API key.
    - Requires 5-digit regional code (`LAWD_CD`, e.g. 강남구 11680).
    - Returns best match by apartment name + nearest area (m2).
    """
    if not api_key:
        raise RealEstateLookupError("MOLIT_API_KEY가 설정되지 않아 실거래가 자동 조회를 사용할 수 없습니다.")

    lawd_cd = region_code.strip()
    if len(lawd_cd) != 5 or not lawd_cd.isdigit():
        raise RealEstateLookupError("지역코드는 5자리 숫자여야 합니다. 예: 11680")

    apt_name = apartment_name.strip()
    if not apt_name:
        raise RealEstateLookupError("아파트명을 입력해 주세요.")
    apt_key = _normalize_apt_name(apt_name)

    endpoints = [
        "https://apis.data.go.kr/1613000/RTMSDataSvcAptTradeDev/getRTMSDataSvcAptTradeDev",
        # Some accounts/services may expose non-Dev endpoint instead.
        "https://apis.data.go.kr/1613000/RTMSDataSvcAptTrade/getRTMSDataSvcAptTrade",
    ]

    best_match: dict[str, Any] | None = None
    best_score = float("inf")

    last_auth_error = ""
    page_size = 999

    for endpoint in endpoints:
        for service_key in _service_key_candidates(api_key):
            for deal_ymd in _month_candidates(count=search_months):
                max_pages = 10
                for page_no in range(1, max_pages + 1):
                    params = {
                        "serviceKey": service_key,
                        "LAWD_CD": lawd_cd,
                        "DEAL_YMD": deal_ymd,
                        "numOfRows": page_size,
                        "pageNo": page_no,
                        "_type": "json",
                    }
                    try:
                        response = requests.get(endpoint, params=params, timeout=8)
                    except requests.RequestException:
                        break

                    if response.status_code == 401:
                        last_auth_error = (
                            "인증 실패(401): API 키가 유효하지 않거나, 해당 서비스 활용신청/승인이 완료되지 않았을 수 있습니다."
                        )
                        break

                    try:
                        response.raise_for_status()
                        payload = response.json()
                    except requests.RequestException:
                        break
                    except ValueError:
                        break

                    header = payload.get("response", {}).get("header", {})
                    result_code = str(header.get("resultCode", ""))
                    result_msg = str(header.get("resultMsg", ""))
                    if result_code and result_code not in {"00", "000"}:
                        if result_code in {"30", "99"}:
                            last_auth_error = f"국토부 API 인증/권한 오류 ({result_code}): {result_msg}"
                        break

                    body = payload.get("response", {}).get("body", {})
                    total_count = int(body.get("totalCount", 0) or 0)
                    try:
                        items = body.get("items", {}).get("item", [])
                    except Exception:
                        break
                    if isinstance(items, dict):
                        items = [items]

                    for item in items:
                        candidate_name = str(item.get("aptNm", "")).strip()
                        candidate_key = _normalize_apt_name(candidate_name)
                        if apt_key not in candidate_key and candidate_key not in apt_key:
                            continue

                        candidate_area = _to_float(item.get("excluUseAr", 0))
                        area_score = abs(candidate_area - area_m2)
                        if area_score < best_score:
                            best_score = area_score
                            best_match = item

                    # Early break if area is almost identical.
                    if best_match and best_score <= 0.2:
                        break

                    # Stop paging when we've read enough pages.
                    if total_count <= page_no * page_size or not items:
                        break

                if best_match and best_score <= 0.2:
                    break

            if best_match:
                break
        if best_match:
            break

    if not best_match:
        if last_auth_error:
            raise RealEstateLookupError(last_auth_error)
        raise RealEstateLookupError("최근 기간에서 조건에 맞는 실거래 데이터를 찾지 못했습니다.")

    deal_price_krw = _parse_trade_price_krw(str(best_match.get("dealAmount", "0")))
    if deal_price_krw <= 0:
        raise RealEstateLookupError("조회된 거래가가 유효하지 않습니다.")

    return {
        "apartment_name": str(best_match.get("aptNm", apt_name)).strip() or apt_name,
        "area_m2": _to_float(best_match.get("excluUseAr", area_m2)),
        "deal_price_krw": deal_price_krw,
        "deal_date": f"{best_match.get('dealYear', '')}-{best_match.get('dealMonth', '')}-{best_match.get('dealDay', '')}",
        "jibun": str(best_match.get("jibun", "")).strip(),
        "region_code": lawd_cd,
    }


def search_apartment_candidates(
    api_key: str,
    region_code: str,
    query: str,
    search_months: int = 24,
    limit: int = 20,
) -> list[dict[str, Any]]:
    """
    Search apartment candidates by name for selection UI.
    Returns deduplicated list with representative latest deal info.
    """
    if not api_key:
        raise RealEstateLookupError("MOLIT_API_KEY가 설정되지 않았습니다.")

    has_region_filter = bool(region_code.strip())
    region_candidates = _region_code_candidates(region_code)

    query_text = query.strip()
    if len(query_text) < 2:
        raise RealEstateLookupError("아파트명은 2글자 이상 입력해 주세요.")
    query_key = _normalize_apt_name(query_text)

    endpoints = [
        "https://apis.data.go.kr/1613000/RTMSDataSvcAptTrade/getRTMSDataSvcAptTrade",
        "https://apis.data.go.kr/1613000/RTMSDataSvcAptTradeDev/getRTMSDataSvcAptTradeDev",
    ]
    matches: dict[str, dict[str, Any]] = {}

    # Search stages: no-region mode starts fast and expands only if needed.
    if has_region_filter:
        stages = [
            {"regions": region_candidates, "months": min(search_months, 24), "max_pages": 6, "timeout": 6},
        ]
    else:
        stages = [
            {"regions": FAST_SEARCH_REGION_CODES, "months": 4, "max_pages": 2, "timeout": 4},
            {"regions": FAST_SEARCH_REGION_CODES, "months": 8, "max_pages": 3, "timeout": 5},
            {"regions": region_candidates, "months": 6, "max_pages": 2, "timeout": 4},
            {"regions": region_candidates, "months": min(search_months, 12), "max_pages": 3, "timeout": 5},
        ]

    for stage in stages:
        for endpoint in endpoints:
            for service_key in _service_key_candidates(api_key):
                for lawd_cd in stage["regions"]:
                    for deal_ymd in _month_candidates(count=stage["months"]):
                        for page_no in range(1, stage["max_pages"] + 1):
                            params = {
                                "serviceKey": service_key,
                                "LAWD_CD": lawd_cd,
                                "DEAL_YMD": deal_ymd,
                                "numOfRows": 999,
                                "pageNo": page_no,
                                "_type": "json",
                            }
                            try:
                                response = requests.get(endpoint, params=params, timeout=stage["timeout"])
                                response.raise_for_status()
                                payload = response.json()
                            except Exception:
                                break

                            body = payload.get("response", {}).get("body", {})
                            total_count = int(body.get("totalCount", 0) or 0)
                            items = body.get("items", {}).get("item", [])
                            if isinstance(items, dict):
                                items = [items]
                            if not items:
                                break

                            for item in items:
                                apt_name = str(item.get("aptNm", "")).strip()
                                apt_key = _normalize_apt_name(apt_name)
                                if not apt_name or query_key not in apt_key:
                                    continue

                                area = _to_float(item.get("excluUseAr", 0))
                                deal_price = _parse_trade_price_krw(str(item.get("dealAmount", "0")))
                                deal_date = f"{item.get('dealYear', '')}-{item.get('dealMonth', '')}-{item.get('dealDay', '')}"
                                item_region_code = str(item.get("sggCd", lawd_cd)).strip() or lawd_cd
                                dedup_key = f"{item_region_code}|{apt_name}|{item.get('jibun', '')}|{round(area, 2)}"
                                existing = matches.get(dedup_key)
                                if existing is None or deal_date > existing["deal_date"]:
                                    matches[dedup_key] = {
                                        "apartment_name": apt_name,
                                        "area_m2": area,
                                        "deal_price_krw": deal_price,
                                        "deal_date": deal_date,
                                        "jibun": str(item.get("jibun", "")).strip(),
                                        "region_code": item_region_code,
                                    }

                            if total_count <= page_no * 999:
                                break

                            if len(matches) >= limit * 3:
                                break

                        if len(matches) >= limit * 3:
                            break
                    if len(matches) >= limit * 3:
                        break
                if len(matches) >= limit * 3:
                    break
            if len(matches) >= limit * 3:
                break
        # If we have enough candidates from a fast stage, stop expanding.
        if len(matches) >= limit:
            break

    # Sort by latest deal date, then by deal price desc.
    results = sorted(
        matches.values(),
        key=lambda x: (x["deal_date"], x["deal_price_krw"]),
        reverse=True,
    )
    return results[:limit]
