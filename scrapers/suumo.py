"""SUUMO 中古マンション一覧ページのスクレイパー。

使用ライブラリ: requests, beautifulsoup4, pyyaml
利用規約に注意: スクレイピングはSUUMOの利用規約に反する場合があります。
個人利用・調査目的の範囲で節度あるリクエスト間隔を守ってください。
"""

import re
import time
from pathlib import Path
from typing import Optional

import requests
import yaml
from bs4 import BeautifulSoup


HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/124.0 Safari/537.36"
    )
}


def _parse_price_man(text: str) -> Optional[float]:
    """'5,800万円' → 5800.0"""
    m = re.search(r"([\d,]+)万円", text)
    return float(m.group(1).replace(",", "")) if m else None


def _parse_area_m2(text: str) -> Optional[float]:
    m = re.search(r"([\d.]+)m²", text)
    return float(m.group(1)) if m else None


def _parse_walk_min(text: str) -> Optional[int]:
    m = re.search(r"徒歩(\d+)分", text)
    return int(m.group(1)) if m else None


def _parse_age_years(text: str) -> Optional[int]:
    m = re.search(r"築(\d+)年", text)
    return int(m.group(1)) if m else None


def scrape_list_page(url: str, delay_sec: float = 2.0) -> list[dict]:
    """SUUMOの検索結果一覧ページから物件情報リストを取得する。

    Returns:
        物件データの辞書リスト（properties/ に保存できる形式）
    """
    time.sleep(delay_sec)
    resp = requests.get(url, headers=HEADERS, timeout=20)
    resp.raise_for_status()
    soup = BeautifulSoup(resp.text, "html.parser")

    properties = []
    for card in soup.select(".cassetteitem"):
        try:
            prop = _parse_card(card)
            if prop:
                properties.append(prop)
        except Exception as e:
            print(f"[WARN] カードのパース失敗: {e}")

    return properties


def _parse_card(card) -> Optional[dict]:
    name_tag = card.select_one(".cassetteitem_content-title")
    price_tag = card.select_one(".cassetteitem_other-emphasis")
    area_tag = card.select_one(".cassetteitem_menseki")
    station_tags = card.select(".cassetteitem_detail-col1")
    floor_tag = card.select_one(".cassetteitem_detail-col3")
    direction_tag = card.select_one(".cassetteitem_detail-col2")
    link_tag = card.select_one("a.js-cassette_link")

    if not name_tag or not price_tag:
        return None

    prop: dict = {
        "name": name_tag.get_text(strip=True),
        "price_man": _parse_price_man(price_tag.get_text()),
        "area_m2": _parse_area_m2(area_tag.get_text() if area_tag else ""),
        "direction": direction_tag.get_text(strip=True) if direction_tag else None,
        "source_url": "https://suumo.jp" + link_tag["href"] if link_tag else None,
        # 以下は詳細ページ取得や追加パースで補完
        "walk_to_station": None,
        "station_name": None,
        "age_years": None,
        "floor_level": None,
        "total_floors": None,
        "address": None,
        "lat": None,
        "lng": None,
        "supermarket_dist_m": None,
        "hospital_dist_m": None,
        "convenience_store_dist_m": None,
        "theoretical_price_man": None,
        "memo": "",
    }

    for tag in station_tags:
        text = tag.get_text()
        if "徒歩" in text:
            prop["walk_to_station"] = _parse_walk_min(text)
        if "分" in text and prop.get("station_name") is None:
            m = re.search(r"「(.+?)」", text)
            if m:
                prop["station_name"] = m.group(1)

    if floor_tag:
        text = floor_tag.get_text()
        m = re.search(r"(\d+)階/(\d+)階建", text)
        if m:
            prop["floor_level"] = int(m.group(1))
            prop["total_floors"] = int(m.group(2))
        prop["age_years"] = _parse_age_years(text)

    return prop


def save_property(prop: dict, out_dir: str = "properties") -> Path:
    """物件データをYAMLファイルに保存する。ファイル名はURLのハッシュから生成。"""
    import hashlib

    key = prop.get("source_url") or prop.get("name", "unknown")
    prop_id = hashlib.md5(key.encode()).hexdigest()[:8]
    prop["id"] = prop_id

    path = Path(out_dir) / f"{prop_id}.yaml"
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        yaml.dump(prop, f, allow_unicode=True, sort_keys=False)

    return path


if __name__ == "__main__":
    import sys

    url = sys.argv[1] if len(sys.argv) > 1 else (
        "https://suumo.jp/ms/chuko/tokyo/sc_shibuya/"
    )
    props = scrape_list_page(url)
    print(f"{len(props)} 件取得")
    for p in props:
        path = save_property(p)
        print(f"  → {path}")
