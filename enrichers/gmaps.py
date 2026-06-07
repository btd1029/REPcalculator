"""Google Maps Places API で生活利便施設までの距離を取得する。

必要な環境変数:
    GMAPS_API_KEY: Google Maps Places API キー
    （config.yaml の google_maps.api_key でも指定可）
"""

import math
import os
from typing import Optional

import requests
import yaml


PLACES_URL = "https://maps.googleapis.com/maps/api/place/nearbysearch/json"


def _haversine_m(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
    """2点間の直線距離（メートル）をハーバーサイン公式で計算する。"""
    R = 6_371_000
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lng2 - lng1)
    a = math.sin(dphi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2) ** 2
    return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))


def nearest_place_dist(
    lat: float,
    lng: float,
    place_type: str,
    api_key: str,
    radius_m: int = 2000,
) -> Optional[float]:
    """指定カテゴリの最寄り施設までの直線距離（m）を返す。

    Args:
        place_type: Google Places のタイプ（例: 'supermarket', 'hospital', 'school'）
    """
    params = {
        "location": f"{lat},{lng}",
        "radius": radius_m,
        "type": place_type,
        "key": api_key,
    }
    resp = requests.get(PLACES_URL, params=params, timeout=15)
    resp.raise_for_status()
    results = resp.json().get("results", [])

    if not results:
        return None

    min_dist = float("inf")
    for place in results:
        loc = place["geometry"]["location"]
        d = _haversine_m(lat, lng, loc["lat"], loc["lng"])
        if d < min_dist:
            min_dist = d

    return round(min_dist, 1)


def enrich_property_file(yaml_path: str, api_key: Optional[str] = None) -> dict:
    """YAMLファイルを読み込み、生活利便距離を計算して上書き保存する。"""
    key = api_key or os.environ.get("GMAPS_API_KEY", "")
    if not key:
        raise ValueError("GMAPS_API_KEY が未設定です。環境変数または config.yaml で設定してください。")

    with open(yaml_path, encoding="utf-8") as f:
        prop = yaml.safe_load(f)

    lat = prop.get("lat")
    lng = prop.get("lng")
    if lat is None or lng is None:
        print(f"[SKIP] {yaml_path}: lat/lng が未設定")
        return prop

    for field, place_type in [
        ("supermarket_dist_m", "supermarket"),
        ("hospital_dist_m", "hospital"),
        ("school_dist_m", "primary_school"),
    ]:
        dist = nearest_place_dist(lat, lng, place_type, key)
        prop[field] = dist
        print(f"[GMAPS] {yaml_path}: {field} = {dist} m")

    with open(yaml_path, "w", encoding="utf-8") as f:
        yaml.dump(prop, f, allow_unicode=True, sort_keys=False)

    return prop


if __name__ == "__main__":
    import sys

    for path in sys.argv[1:]:
        enrich_property_file(path)
