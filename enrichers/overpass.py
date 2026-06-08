"""Overpass API（OpenStreetMap）で生活利便施設までの距離を取得する。

認証不要・無料。リクエスト間隔を1秒以上空けること（利用規約）。
API仕様: https://overpass-api.de/
"""

import math
import time
from pathlib import Path
from typing import Optional

import requests
import yaml


OVERPASS_URL = "https://overpass-api.de/api/interpreter"

# 施設フィールド → Overpassクエリ条件のマッピング
FACILITY_QUERIES = {
    "supermarket_dist_m": '["shop"~"supermarket|grocery"]',
    "hospital_dist_m":    '["amenity"~"hospital|clinic"]',
    "convenience_store_dist_m": '["shop"="convenience"]',
}


def _haversine_m(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
    R = 6_371_000
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lng2 - lng1)
    a = math.sin(dphi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2) ** 2
    return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))


def nearest_facility_dist(
    lat: float,
    lng: float,
    osm_filter: str,
    radius_m: int = 1000,
    timeout: int = 10,
) -> Optional[float]:
    """Overpass APIで最寄り施設までの直線距離（m）を返す。

    Args:
        osm_filter: Overpassのタグフィルタ（例: '["shop"="supermarket"]'）
        radius_m: 検索半径（m）
    """
    query = (
        f"[out:json][timeout:{timeout}];"
        f"("
        f'node{osm_filter}(around:{radius_m},{lat},{lng});'
        f'way{osm_filter}(around:{radius_m},{lat},{lng});'
        f");"
        f"out center;"
    )
    resp = requests.post(OVERPASS_URL, data={"data": query}, timeout=timeout + 5)
    resp.raise_for_status()
    elements = resp.json().get("elements", [])

    if not elements:
        return None

    min_dist = float("inf")
    for el in elements:
        # wayはcenter座標を使う
        if el["type"] == "way":
            c = el.get("center", {})
            elat, elng = c.get("lat"), c.get("lon")
        else:
            elat, elng = el.get("lat"), el.get("lon")
        if elat is None or elng is None:
            continue
        d = _haversine_m(lat, lng, elat, elng)
        if d < min_dist:
            min_dist = d

    return round(min_dist, 1) if min_dist < float("inf") else None


def enrich_property_file(yaml_path: str, radius_m: int = 1000) -> dict:
    """YAMLファイルを読み込み、生活利便距離を計算して上書き保存する。

    Google Maps APIキー不要。
    """
    with open(yaml_path, encoding="utf-8") as f:
        prop = yaml.safe_load(f)

    lat = prop.get("lat")
    lng = prop.get("lng")
    if lat is None or lng is None:
        print(f"[SKIP] {yaml_path}: lat/lng が未設定")
        return prop

    for field, osm_filter in FACILITY_QUERIES.items():
        dist = nearest_facility_dist(lat, lng, osm_filter, radius_m=radius_m)
        prop[field] = dist
        print(f"[OVERPASS] {yaml_path}: {field} = {dist} m")
        time.sleep(1.0)  # Overpass利用規約: 1秒以上の間隔

    with open(yaml_path, "w", encoding="utf-8") as f:
        yaml.dump(prop, f, allow_unicode=True, sort_keys=False)

    return prop


if __name__ == "__main__":
    import sys

    paths = sys.argv[1:]
    if not paths:
        print("使い方: python enrichers/overpass.py properties/*.yaml")
        sys.exit(1)
    for path in paths:
        enrich_property_file(path)
