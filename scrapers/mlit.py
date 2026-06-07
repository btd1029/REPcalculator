"""国土交通省 不動産取引価格情報API を使って周辺取引事例を取得し、理論価格を算出する。

API仕様: https://www.land.mlit.go.jp/webland/api.html
無料・認証不要。
"""

import datetime
import statistics
from typing import Optional

import requests
import yaml


BASE_URL = "https://www.land.mlit.go.jp/webland/api/TradeListSearch"


def _year_quarter_range(years_back: int) -> tuple[str, str]:
    """直近 years_back 年分の (from, to) を '20231' 形式で返す。"""
    now = datetime.date.today()
    to_year = now.year
    to_quarter = (now.month - 1) // 3 + 1
    from_year = to_year - years_back
    from_quarter = to_quarter
    return f"{from_year}{from_quarter}", f"{to_year}{to_quarter}"


def fetch_nearby_trades(
    lat: float,
    lng: float,
    radius_km: float = 0.5,
    years_back: int = 2,
    trade_type: str = "01",
) -> list[dict]:
    """周辺取引事例を取得する。

    Args:
        lat, lng: 物件の緯度・経度
        radius_km: 検索半径（km）
        years_back: 直近何年分を取得するか
        trade_type: 01=中古マンション
    Returns:
        取引事例のリスト（APIレスポンスの "data" フィールド）
    """
    from_q, to_q = _year_quarter_range(years_back)

    # APIは緯度経度ボックスで検索する
    delta = radius_km / 111.0  # 約1度=111km
    params = {
        "year": to_q[:4],
        "season": to_q[4:],
        "fromYear": from_q[:4],
        "fromSeason": from_q[4:],
        "toYear": to_q[:4],
        "toSeason": to_q[4:],
        "swLat": lat - delta,
        "swLng": lng - delta,
        "neLat": lat + delta,
        "neLng": lng + delta,
        "type": trade_type,
    }

    resp = requests.get(BASE_URL, params=params, timeout=20)
    resp.raise_for_status()
    data = resp.json()
    return data.get("data", [])


def calc_theoretical_price(
    trades: list[dict],
    area_m2: float,
) -> Optional[float]:
    """取引事例の単価中央値から理論価格（万円）を算出する。

    Args:
        trades: fetch_nearby_trades() の戻り値
        area_m2: 対象物件の専有面積
    Returns:
        理論価格（万円）、事例がなければ None
    """
    unit_prices = []
    for t in trades:
        try:
            price = float(t.get("TradePrice", 0))      # 円
            area = float(t.get("Area", 0))              # m²
            if price > 0 and area > 0:
                unit_prices.append(price / area)        # 円/m²
        except (ValueError, TypeError):
            continue

    if not unit_prices:
        return None

    median_unit = statistics.median(unit_prices)       # 円/m²
    theoretical_yen = median_unit * area_m2
    return round(theoretical_yen / 10000, 1)           # → 万円


def enrich_property_file(yaml_path: str, years_back: int = 2) -> dict:
    """YAMLファイルを読み込み、理論価格を計算して上書き保存する。"""
    with open(yaml_path, encoding="utf-8") as f:
        prop = yaml.safe_load(f)

    lat = prop.get("lat")
    lng = prop.get("lng")
    area = prop.get("area_m2")

    if lat is None or lng is None or area is None:
        print(f"[SKIP] {yaml_path}: lat/lng/area_m2 が未設定")
        return prop

    trades = fetch_nearby_trades(lat, lng, years_back=years_back)
    theoretical = calc_theoretical_price(trades, area)
    prop["theoretical_price_man"] = theoretical
    print(f"[MLIT] {yaml_path}: 取引事例 {len(trades)} 件, 理論価格 {theoretical} 万円")

    with open(yaml_path, "w", encoding="utf-8") as f:
        yaml.dump(prop, f, allow_unicode=True, sort_keys=False)

    return prop


if __name__ == "__main__":
    import sys

    for path in sys.argv[1:]:
        enrich_property_file(path)
