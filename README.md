# REPcalculator

中古マンションのスコアリング・コスパランキングツール。

物件スペックと生活利便性を数値化し、**スコア÷価格（コスパ比）** と **売値÷理論価格（乖離率）** で物件を客観的に比較する。

---

## 仕組み

### スコアモデル

```
Score = Σ( w_i × normalize(f_i) )   # 重み付き合計（0〜1）
コスパ比 = Score ÷ price_man × 1000  # 高いほどお得
乖離率   = price_man ÷ theoretical_price_man − 1
           # 正→割高、負→割安
```

| 因子 | 取得方法 | デフォルト重み |
|------|----------|----------------|
| 駅徒歩分数 | SUUMO スクレイピング | 0.20 |
| 築年数 | SUUMO スクレイピング | 0.15 |
| 専有面積 | SUUMO スクレイピング | 0.15 |
| スーパー距離 | Google Maps Places API | 0.10 |
| 管理状況 | **手入力（内見後）** | 0.10 |
| 階数 | SUUMO スクレイピング | 0.05 |
| 向き | SUUMO スクレイピング | 0.05 |
| 病院距離 | Google Maps Places API | 0.05 |
| 小学校距離 | Google Maps Places API | 0.05 |
| 共用部グレード | **手入力（内見後）** | 0.05 |
| 眺望 | **手入力（内見後）** | 0.05 |

理論価格は国土交通省 不動産取引価格情報API（無料・認証不要）の周辺取引事例の単価中央値から算出。

---

## ディレクトリ構成

```
estate-scorer/
├── config.yaml          # 重み・正規化範囲・検索条件
├── requirements.txt
├── properties/          # 物件ごとのデータ（YAML）
│   └── sample_001.yaml  # 記入例
├── scrapers/
│   ├── suumo.py         # SUUMO スクレイピング
│   └── mlit.py          # 国土交通省 取引価格情報API
├── enrichers/
│   └── gmaps.py         # Google Maps Places API（施設距離）
├── scorer.py            # スコア計算・コスパ比・乖離率
├── export.py            # CSV出力
└── output/
    └── result.csv       # 出力先
```

---

## セットアップ

```bash
pip install -r requirements.txt
```

Google Maps Places API を使う場合は API キーを環境変数に設定：

```bash
export GMAPS_API_KEY="your_api_key_here"
```

---

## 使い方

### 1. 物件情報を自動取得（SUUMO）

```bash
python scrapers/suumo.py "https://suumo.jp/ms/chuko/tokyo/sc_shibuya/"
```

`properties/<ID>.yaml` が生成される。

### 2. 理論価格を算出（国土交通省API）

```bash
python scrapers/mlit.py properties/*.yaml
```

各YAMLの `theoretical_price_man` が埋まる。

### 3. 生活利便距離を取得（Google Maps）

```bash
python enrichers/gmaps.py properties/*.yaml
```

各YAMLの `supermarket_dist_m` / `hospital_dist_m` / `school_dist_m` が埋まる。

### 4. 内見後に手入力スコアを記入

`properties/<ID>.yaml` を開き、以下を 0〜10 で記入：

```yaml
management_score: 8    # 管理状況
common_area_score: 7   # 共用部グレード
view_score: 6          # 眺望
memo: "南向き・角部屋。管理人常駐"
```

### 5. コスパランキングをCSV出力

```bash
python export.py
# → output/result.csv
```

ターミナルでも確認できる：

```bash
python scorer.py
```

---

## 設定カスタマイズ（config.yaml）

重みや正規化範囲は `config.yaml` で変更できる。

```yaml
weights:
  walk_to_station: 0.20   # 駅距離を重視するなら増やす
  management_score: 0.10
  ...

normalization:
  walk_to_station: {min: 1, max: 20}  # 1分〜20分を0〜1にマッピング
  area_m2:         {min: 20, max: 120}
```

重みの合計が1.0でなくても自動で正規化されるため、値の比率だけ意識すればよい。

---

## CSV出力のカラム

| カラム | 説明 |
|--------|------|
| rank | コスパ比降順の順位 |
| score | 総合スコア（0〜1） |
| cospa | コスパ比（score÷price×1000） |
| deviation | 乖離率（正→割高、負→割安） |
| price_man | 売値（万円） |
| theoretical_price_man | 理論価格（万円） |
| walk_to_station | 駅徒歩分数 |
| age_years | 築年数 |
| area_m2 | 専有面積（㎡） |
