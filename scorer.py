"""スコア計算・コスパ比・乖離率を算出する。

スコアモデル:
    Score = Σ( w_i * f_i )   ← 重み付き合計（nullはスキップして残重みで正規化）
    コスパ比 = Score / price_man * 1000
    乖離率   = price_man / theoretical_price_man - 1
"""

import math
from pathlib import Path
from typing import Optional

import yaml


def _load_config(config_path: str = "config.yaml") -> dict:
    with open(config_path, encoding="utf-8") as f:
        return yaml.safe_load(f)


def _normalize(value: float, vmin: float, vmax: float, invert: bool = False) -> float:
    if vmax == vmin:
        return 0.5
    norm = max(0.0, min(1.0, (value - vmin) / (vmax - vmin)))
    return 1.0 - norm if invert else norm


def _age_step_score(age: float, steps: list[dict]) -> float:
    for step in steps:
        if age <= step["max_years"]:
            return step["score"]
    return 0.0


def _haversine_m(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
    R = 6_371_000
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lng2 - lng1)
    a = math.sin(dphi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2) ** 2
    return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))


def _terminal_access_score(prop: dict, terminals: list[dict], norm_cfg: dict) -> Optional[float]:
    lat = prop.get("lat")
    lng = prop.get("lng")
    if lat is None or lng is None or not terminals:
        return None
    dists = [_haversine_m(lat, lng, t["lat"], t["lng"]) for t in terminals]
    avg_dist = sum(dists) / len(dists)
    cfg = norm_cfg["terminal_access"]
    return _normalize(avg_dist, cfg["min"], cfg["max"], invert=True)


def passes_hard_filters(prop: dict, config: dict) -> bool:
    filters = config.get("hard_filters", {})
    for key, required in filters.items():
        val = prop.get(key)
        if val is None:
            return False
        if required is True and val is not True:
            return False
    return True


def score_property(prop: dict, config: dict) -> dict:
    weights = config["weights"]
    norm_cfg = config["normalization"]
    dir_scores = config["direction_score"]
    age_steps = config.get("age_step_scores", [])
    terminals = config.get("terminal_stations", [])

    scores: dict[str, Optional[float]] = {}

    def n(key: str, invert: bool = False) -> Optional[float]:
        v = prop.get(key)
        if v is None:
            return None
        cfg = norm_cfg.get(key)
        if cfg is None:
            return None
        return _normalize(float(v), cfg["min"], cfg["max"], invert=invert)

    scores["walk_to_station"] = n("walk_to_station", invert=True)
    scores["area_m2"] = n("area_m2")
    scores["floor_level"] = n("floor_level")
    scores["supermarket_dist_m"] = n("supermarket_dist_m", invert=True)
    scores["hospital_dist_m"] = n("hospital_dist_m", invert=True)
    scores["convenience_store_dist_m"] = n("convenience_store_dist_m", invert=True)

    # ターミナル駅アクセス（全駅直線距離の平均）
    scores["terminal_access"] = _terminal_access_score(prop, terminals, norm_cfg)

    # 築年数（ステップスコア）
    age = prop.get("age_years")
    scores["age_years"] = _age_step_score(float(age), age_steps) if age is not None else None

    # 向き
    direction = prop.get("direction")
    scores["direction"] = dir_scores.get(direction) if direction else None

    # boolean設備因子（True=1.0, False/None=0.0）
    for key in ("renovation", "delivery_box", "bathroom_dryer", "walk_in_closet"):
        v = prop.get(key)
        scores[key] = 1.0 if v is True else 0.0 if v is False else None

    # 重み付き合計（nullはスキップ）
    total_weight = 0.0
    weighted_sum = 0.0
    for key, w in weights.items():
        s = scores.get(key)
        if s is not None:
            weighted_sum += w * s
            total_weight += w

    score = (weighted_sum / total_weight) if total_weight > 0 else None

    price = prop.get("price_man")
    theoretical = prop.get("theoretical_price_man")

    cospa = (score / price * 1000) if (score is not None and price) else None
    deviation = (
        round(price / theoretical - 1, 4)
        if (price and theoretical)
        else None
    )

    return {
        "id": prop.get("id", ""),
        "name": prop.get("name", ""),
        "price_man": price,
        "theoretical_price_man": theoretical,
        "score": round(score, 4) if score is not None else None,
        "cospa": round(cospa, 6) if cospa is not None else None,
        "deviation": deviation,
        "walk_to_station": prop.get("walk_to_station"),
        "age_years": prop.get("age_years"),
        "area_m2": prop.get("area_m2"),
        "pet_allowed": prop.get("pet_allowed"),
        "station_name": prop.get("station_name"),
        "address": prop.get("address"),
        "source_url": prop.get("source_url"),
        "memo": prop.get("memo", ""),
    }


def score_all(properties_dir: str = "properties", config_path: str = "config.yaml") -> list[dict]:
    config = _load_config(config_path)
    results = []
    skipped = 0
    for path in Path(properties_dir).glob("*.yaml"):
        with open(path, encoding="utf-8") as f:
            prop = yaml.safe_load(f)
        if not passes_hard_filters(prop, config):
            skipped += 1
            continue
        result = score_property(prop, config)
        results.append(result)

    results.sort(key=lambda r: r["cospa"] if r["cospa"] is not None else -1, reverse=True)
    if skipped:
        print(f"[FILTER] {skipped} 件をハードフィルターで除外")
    return results


if __name__ == "__main__":
    results = score_all()
    for i, r in enumerate(results, 1):
        print(
            f"{i:2d}. [{r['id']}] {r['name'][:20]:<20} "
            f"Score={r['score']}  Cospa={r['cospa']}  "
            f"Deviation={r['deviation']}  {r['price_man']}万円"
        )
