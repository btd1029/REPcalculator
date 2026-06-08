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

| 因子 | 取得方法 | 重み |
|------|----------|------|
| 専有面積 | SUUMO スクレイピング | 0.35 |
| スーパー距離 | Google Maps Places API | 0.135 |
| 駅徒歩分数 | SUUMO スクレイピング | 0.10 |
| ターミナル駅アクセス | 緯度経度から直線距離計算 | 0.10 |
| 病院距離 | Google Maps Places API | 0.085 |
| 築年数 | SUUMO スクレイピング | 0.08 |
| コンビニ距離 | Google Maps Places API | 0.05 |
| 階数 | SUUMO スクレイピング | 0.05 |
| 向き | SUUMO スクレイピング | 0.05 |
| リノベ済み | SUUMO スクレイピング | 0.05 |
| 宅配ボックス | SUUMO スクレイピング | 0.03 |
| 浴室乾燥機 | SUUMO スクレイピング | 0.02 |
| ウォークインクローゼット | SUUMO スクレイピング | 0.02 |
| **ペット可** | SUUMO スクレイピング | **ハードフィルター** |

> 築年数はステップスコア評価（〜10年: 1.0 / 〜20年: 0.75 / 〜30年: 0.50 / 〜44年: 0.25 / 45年超: 0.0）。ターミナル駅は `config.yaml` で設定し、全駅への直線距離平均でスコア化。

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

## WebUI の使い方

### セットアップ
1. GitHubリポジトリの Settings → Pages → Source を `claude/modest-brown-B9rEP` ブランチの `/docs` フォルダに設定
2. Settings → Secrets → Actions で `GITHUB_TOKEN` の書き込み権限を確認（デフォルトで有効）
3. `https://<username>.github.io/<repo>/` にアクセス

### 物件を登録する
1. SUUMOで気になる物件のスクリーンショットを撮る
2. WebUIを開き、設定パネルでClaude APIキーとGitHub PATを入力・保存
3. スクリーンショットをアップロード（ドラッグ&ドロップまたはCtrl+V）
4. 「抽出」ボタンを押すとClaude Visionが物件情報を読み取る
5. 確認フォームで内容を修正し「確定・保存」
6. GitHub Actionsが自動でスコアを計算し、ランキングページを更新（約1分）

### ランキングを見る
`https://<username>.github.io/<repo>/ranking.html` でコスパ順のランキングを確認できる。

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

各YAMLの `supermarket_dist_m` / `hospital_dist_m` / `convenience_store_dist_m` が埋まる。

### 4. 設備情報を確認・補完

`properties/<ID>.yaml` を開き、スクレイピングで取得できなかった設備フィールドを手入力：

```yaml
pet_allowed: true        # ペット可（必須項目）
renovation: false        # リノベ済み
delivery_box: true       # 宅配ボックス
bathroom_dryer: true     # 浴室乾燥機
walk_in_closet: false    # ウォークインクローゼット
memo: "南向き・角部屋"
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
  area_m2: 0.35            # 面積を最重視するなら増やす
  terminal_access: 0.10    # ターミナル駅アクセスの重み
  walk_to_station: 0.10
  ...

normalization:
  walk_to_station: {min: 1, max: 15}   # 1〜15分を0〜1にマッピング
  terminal_access: {min: 1000, max: 15000}  # 直線距離（m）

terminal_stations:
  - {name: "梅田", lat: 34.7024, lng: 135.4959}  # 大阪向けに差し替え例
  - {name: "難波", lat: 34.6686, lng: 135.5013}
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
