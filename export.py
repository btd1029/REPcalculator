"""スコア結果をCSVに出力する。"""

import csv
from pathlib import Path

from scorer import score_all


COLUMNS = [
    "rank",
    "id",
    "name",
    "price_man",
    "theoretical_price_man",
    "score",
    "cospa",
    "deviation",
    "walk_to_station",
    "age_years",
    "area_m2",
    "station_name",
    "address",
    "source_url",
    "memo",
]


def export_csv(
    out_path: str = "output/result.csv",
    properties_dir: str = "properties",
    config_path: str = "config.yaml",
) -> Path:
    results = score_all(properties_dir, config_path)
    out = Path(out_path)
    out.parent.mkdir(parents=True, exist_ok=True)

    with open(out, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=COLUMNS, extrasaction="ignore")
        writer.writeheader()
        for rank, row in enumerate(results, 1):
            writer.writerow({"rank": rank, **row})

    print(f"CSV出力完了: {out}  ({len(results)} 件)")
    return out


if __name__ == "__main__":
    import sys

    out = sys.argv[1] if len(sys.argv) > 1 else "output/result.csv"
    export_csv(out)
