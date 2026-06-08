"""スコア結果をdocs/ranking.htmlに出力する。"""

import html
from datetime import datetime
from pathlib import Path

from scorer import score_all


def _fmt(val, fmt=None, default="—"):
    if val is None:
        return default
    if fmt:
        return fmt.format(val)
    return str(val)


def _deviation_style(dev):
    if dev is None:
        return ""
    if dev < -0.05:
        return "background-color:#e6f4ea;"  # green tint (割安)
    if dev > 0.05:
        return "background-color:#fce8e6;"  # red tint (割高)
    return ""


def _bool_mark(val):
    if val is True:
        return "✓"
    if val is False:
        return "✗"
    return "—"


def render():
    properties = score_all()
    # sort by cospa descending by default
    properties = sorted(properties, key=lambda p: (p.get("cospa") or 0), reverse=True)

    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    rows_html = ""
    for rank, prop in enumerate(properties, start=1):
        dev = prop.get("deviation")
        dev_str = f"{dev*100:+.1f}%" if dev is not None else "—"
        name = html.escape(prop.get("name") or "")
        source_url = prop.get("source_url") or ""
        if source_url:
            name_cell = f'<a href="{html.escape(source_url)}" target="_blank">{name}</a>'
        else:
            name_cell = name

        row_style = _deviation_style(dev)

        rows_html += f"""
        <tr style="{row_style}" data-cospa="{prop.get('cospa') or 0}"
            data-score="{prop.get('score') or 0}"
            data-price="{prop.get('price_man') or 0}"
            data-deviation="{dev if dev is not None else 0}"
            data-walk="{prop.get('walk_to_station') or 0}"
            data-age="{prop.get('age_years') or 0}"
            data-area="{prop.get('area_m2') or 0}"
            data-rank="{rank}">
          <td>{rank}</td>
          <td>{name_cell}</td>
          <td>{_fmt(prop.get('price_man'), '{:.0f}')}</td>
          <td>{_fmt(prop.get('score'), '{:.3f}')}</td>
          <td>{_fmt(prop.get('cospa'), '{:.2f}')}</td>
          <td>{dev_str}</td>
          <td>{_fmt(prop.get('walk_to_station'))}</td>
          <td>{_fmt(prop.get('age_years'))}</td>
          <td>{_fmt(prop.get('area_m2'))}</td>
          <td>{html.escape(prop.get('station_name') or '—')}</td>
          <td>{_bool_mark(prop.get('pet_allowed'))}</td>
          <td>{html.escape(prop.get('memo') or '')}</td>
        </tr>"""

    page = f"""<!DOCTYPE html>
<html lang="ja">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>物件コスパランキング</title>
  <style>
    *, *::before, *::after {{ box-sizing: border-box; }}
    body {{
      font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
      background: #fff;
      color: #222;
      margin: 0;
      padding: 16px;
    }}
    h1 {{
      font-size: 1.4rem;
      color: #1a73e8;
      margin-bottom: 4px;
    }}
    .subtitle {{ color: #666; font-size: 0.85rem; margin-bottom: 16px; }}
    table {{
      width: 100%;
      border-collapse: collapse;
      font-size: 0.9rem;
    }}
    th {{
      background: #1a73e8;
      color: #fff;
      padding: 8px 10px;
      text-align: left;
      cursor: pointer;
      user-select: none;
      white-space: nowrap;
    }}
    th:hover {{ background: #1558b0; }}
    th.sorted-asc::after {{ content: " ▲"; }}
    th.sorted-desc::after {{ content: " ▼"; }}
    td {{
      padding: 7px 10px;
      border-bottom: 1px solid #e0e0e0;
    }}
    tr:hover td {{ filter: brightness(0.96); }}
    a {{ color: #1a73e8; text-decoration: none; }}
    a:hover {{ text-decoration: underline; }}
    footer {{
      margin-top: 20px;
      font-size: 0.8rem;
      color: #999;
    }}
    @media (max-width: 700px) {{
      table {{ font-size: 0.75rem; }}
      td, th {{ padding: 5px 6px; }}
    }}
  </style>
</head>
<body>
  <h1>物件コスパランキング</h1>
  <p class="subtitle">コスパ比（スコア÷価格×1000）の高い順。緑＝割安、赤＝割高。</p>
  <table id="rankingTable">
    <thead>
      <tr>
        <th data-col="rank">順位</th>
        <th data-col="name">物件名</th>
        <th data-col="price">価格（万円）</th>
        <th data-col="score">スコア</th>
        <th data-col="cospa">コスパ比</th>
        <th data-col="deviation">乖離率</th>
        <th data-col="walk">駅徒歩（分）</th>
        <th data-col="age">築年数</th>
        <th data-col="area">面積（㎡）</th>
        <th data-col="station">最寄り駅</th>
        <th data-col="pet">ペット可</th>
        <th data-col="memo">メモ</th>
      </tr>
    </thead>
    <tbody>
      {rows_html}
    </tbody>
  </table>
  <footer>最終更新: {timestamp}</footer>
  <script>
    (function() {{
      const table = document.getElementById('rankingTable');
      const tbody = table.querySelector('tbody');
      const colMap = {{
        rank: 'rank', name: null, price: 'price', score: 'score',
        cospa: 'cospa', deviation: 'deviation', walk: 'walk',
        age: 'age', area: 'area', station: null, pet: null, memo: null
      }};
      let sortCol = 'cospa';
      let sortAsc = false;

      function updateHeaders() {{
        table.querySelectorAll('th').forEach(th => {{
          th.classList.remove('sorted-asc', 'sorted-desc');
          if (th.dataset.col === sortCol) {{
            th.classList.add(sortAsc ? 'sorted-asc' : 'sorted-desc');
          }}
        }});
      }}

      function sortTable(col) {{
        const attr = colMap[col];
        if (!attr) return;
        if (sortCol === col) sortAsc = !sortAsc;
        else {{ sortCol = col; sortAsc = false; }}
        const rows = Array.from(tbody.querySelectorAll('tr'));
        rows.sort((a, b) => {{
          const av = parseFloat(a.dataset[attr]) || 0;
          const bv = parseFloat(b.dataset[attr]) || 0;
          return sortAsc ? av - bv : bv - av;
        }});
        rows.forEach(r => tbody.appendChild(r));
        updateHeaders();
      }}

      table.querySelectorAll('th').forEach(th => {{
        th.addEventListener('click', () => sortTable(th.dataset.col));
      }});

      updateHeaders();
    }})();
  </script>
</body>
</html>
"""

    out = Path("docs/ranking.html")
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(page, encoding="utf-8")
    print(f"Written {out} ({len(properties)} properties, {timestamp})")


if __name__ == "__main__":
    render()
