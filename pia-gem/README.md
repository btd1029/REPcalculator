# PIAアシスタント（Gemini Gem ＋ GAS転記ツール）

自社プライバシー評価質問票 v1.8 に沿って PIA/DPIA の下書きを生成する Gemini Gem と、
その出力を Google Sheets テンプレへ自動転記する Google Apps Script 一式。

## 中身

| ファイル | 内容 |
|---|---|
| `PIA_Gem_instructions.md` | Gem「PIAアシスタント」のセットアップガイド（名前・ナレッジ添付手順・システム指示全文・運用メモ） |
| `gas/Code.gs` | 転記ツール本体（メニュー／名前付き範囲セットアップ／検証／自動複製・命名／可変行挿入／残存検算／転記ログ） |
| `gas/Dialog.html` | JSON貼付ダイアログUI |
| `gas/README_セットアップ手順.md` | GASの設置手順と毎回の使い方 |

## 使う流れ

1. Gemini で Gem を作成（`PIA_Gem_instructions.md` の手順）。ナレッジに質問票 v1.8 と過去PIAを添付。
2. マスターテンプレ（Sheets）に `gas/` のスクリプトを設置し、`CONFIG` を実レイアウトに合わせて調整。
3. Gem でPIAを生成 → 出力末尾の `<PIA_JSON>…</PIA_JSON>` をコピー → テンプレのメニュー「PIA転記」で貼って転記。

## 前提・制約

- Gem と GAS は直接連携できないため、橋渡しは人のコピペ1回。
- Gem は Google Sheets へ直接書き込めないため、転記は GAS が担当。
- 過去PIA は NotebookLM ではなく Gem のナレッジに添付する運用（Gem から NotebookLM は自動参照できない）。
- 生成物は下書き。最終判断・承認・署名は人間が行う。
