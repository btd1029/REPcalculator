"""スコア計算・コスパ比・乖離率を算出する。

スコアモデル:
    Score = Σ( w_i * normalize(f_i) )   ← 重み付き合計（0-1スケール）
    コスパ比 = Score / price_man          ← 高いほどお得
    乖離率 = price_man / theoretical_price_man - 1
              正→割高、負→割安
"""

from pathlib import Path
from typing import Optional

import yaml


def _load_config(config_path: str = "config.yaml") -> dict:
    with open(config_path, encoding="utf-8") as f:
        return yaml.safe_load(f)


def _normalize(value: float, vmin: float, vmax: float, invert: bool = False) -> float:
    """値を [0, 1] に正規化する。invert=True なら小さいほど高得点。"""
    if vmax == vmin:
        return 0.5
    norm = max(0.0, min(1.0, (value - vmin) / (vmax - vmin)))
    return 1.0 - norm if invert else norm


def score_property(prop: dict, config: dict) -> dict:
    """1物件のスコア・コスパ比・乖離率を計算して返す。"""
    weights = config["weights"]
    norm_cfg = config["normalization"]
    dir_scores = config["direction_score"]

    scores: dict[str, Optional[float]] = {}

    def n(key: float, invert: bool = False) -> Optional[float]:
        v = prop.get(key)
        if v is None:
            return None
        cfg = norm_cfg.get(key)
        if cfg is None:
            return None
        return _normalize(float(v), cfg["min"], cfg["max"], invert=invert)

    scores["walk_to_station"] = n("walk_to_station", invert=True)
    scores["age_years"] = n("age_years", invert=True)
    scores["area_m2"] = n("area_m2")
    scores["floor_level"] = n("floor_level")
    scores["supermarket_dist_m"] = n("supermarket_dist_m", invert=True)
    scores["hospital_dist_m"] = n("hospital_dist_m", invert=True)
    scores["school_dist_m"] = n("school_dist_m", invert=True)

    # 向き
    direction = prop.get("direction")
    scores["direction"] = dir_scores.get(direction) if direction else None

    # 手入力スコア（0-10 → 0-1）
    for key in ("management_score", "common_area_score", "view_score"):
        v = prop.get(key)
        scores[key] = float(v) / 10.0 if v is not None else None

    # 重み付き合計（nullはスキップし、残りの重みで正規化）
    total_weight = 0.0
    weighted_sum = 0.0
    for key, w in weights.items():
        s = scores.get(key)
        if s is not None:
            weighted_sum += w * s
            total_weight += w

    score = (weighted_sum / total_weight) if total_weight > 0 else None

    # コスパ比・乖離率
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
        "station_name": prop.get("station_name"),
        "address": prop.get("address"),
        "source_url": prop.get("source_url"),
        "memo": prop.get("memo", ""),
    }


def score_all(properties_dir: str = "properties", config_path: str = "config.yaml") -> list[dict]:
    """properties/ 以下の全YAMLを読み込み、スコア計算結果リストを返す（コスパ降順）。"""
    config = _load_config(config_path)
    results = []
    for path in Path(properties_dir).glob("*.yaml"):
        with open(path, encoding="utf-8") as f:
            prop = yaml.safe_load(f)
        result = score_property(prop, config)
        results.append(result)

    results.sort(key=lambda r: r["cospa"] if r["cospa"] is not None else -1, reverse=True)
    return results


if __name__ == "__main__":
    results = score_all()
    for i, r in enumerate(results, 1):
        print(
            f"{i:2d}. [{r['id']}] {r['name'][:20]:<20} "
            f"Score={r['score']}  Cospa={r['cospa']}  "
            f"Deviation={r['deviation']}  {r['price_man']}万円"
        )
