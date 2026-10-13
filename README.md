# lecture2026

2026年度の講義資料・研究ノートおよび数理最適化・AIツール活用の教材リポジトリです。
主に「\LaTeX 基礎講座」「主要AI開発エージェントのスラッシュコマンド比較」「Timefold と数理最適化ソルバー（AMPL / Gurobi）による配車配送計画問題（MDVRPTW）」「線形計画・組合せ最適化問題データセット」を収録しています。

---

## ディレクトリ構成

```
lecture2026/
├── beamer/         # 初学者向け LaTeX 入門講義スライド
├── latex/          # AIツールのスラッシュコマンド比較（論文版・スライド版）
├── markdown/       # AIツールのスラッシュコマンド比較（レポート原本）
├── timefold/       # 配車配送計画問題（MDVRPTW）の Timefold vs AMPL/Gurobi 比較検証
├── datasets/       # 数理最適化モデリング問題データセット（LP・MIP）
└── json_files/     # 組合せ最適化・スケジューリング問題の標準インスタンス群
```

---

## コンテンツ詳細

### 1. 初学者向け \LaTeX 入門スライド (`beamer/`)
LaTeX を初めて学ぶ受講生向けに、文書構造から数式、表・図、相互参照、文献管理、エラー対処までを網羅した解説スライドです。

| ファイル | 形式 | 内容 |
|---|---|---|
| `latex_basics.tex` | beamer | Lua\LaTeX 用スライドソース（Metropolis テーマ、16:9 ワイド画面、全31頁） |
| `latex_basics.pdf` | PDF | コンパイル済みスライド |

**主な内容:**
- \LaTeX の特徴と Word（WYSIWYG）との違い・執筆ワークフロー
- 文書の基本構造（プリアンブル、`jlreq`/`ltjsarticle`、見出し、特殊文字）
- 本文整形ルール（改行と段落、文字装飾、箇条書き環境）
- 数式記述（`amsmath`、上下添字、分数、積分、極限、`align` 等号揃え、行列）
- 表・図の挿入（`booktabs` による学術標準表、`graphicx`、`float`）
- 相互参照（`\label` / `\ref`）と参考文献引用（`\cite`）
- 独自マクロ定義（`\newcommand`）とよくあるエラーのデバッグ法

---

### 2. AIツールのスラッシュコマンド比較 (`latex/`, `markdown/`)
主要AIコーディングエージェント（Google Antigravity、Anthropic Claude Code、OpenAI Codex CLI）におけるスラッシュコマンドの仕様、カスタムコマンド設計、アーキテクチャの違い、およびプロンプトインジェクション等のセキュリティリスクを徹底比較した研究資料です。

| ファイル | 形式 | 内容 |
|---|---|---|
| `markdown/AIツールのスラッシュコマンド比較.md` | Markdown | 元レポート（全8章、引用文献58件） |
| `markdown/AIツールのスラッシュコマンド比較.pdf` | PDF | Markdown から生成した PDF レポート |
| `latex/slash_commands_comparison.tex` | LaTeX 論文 | 論文形式（`ltjsarticle`、概要・キーワード・比較表4点・14頁） |
| `latex/slash_commands_comparison.pdf` | PDF | 論文版 PDF |
| `latex/slash_commands_slides.tex` | beamer | 講義用プレゼンスライド（16:9、32頁） |
| `latex/slash_commands_slides.pdf` | PDF | beamer 版 PDF |
| `latex/slash_commands_slides.pptx` | PowerPoint | beamer 版をベースにしたプレゼン資料（16:9、30枚） |

---

### 3. Timefold vs 数理最適化（AMPL）配車配送計画 (`timefold/`)
Timefold Quickstarts の「複数デポ・時間枠付き車両ルーティング問題（MDVRPTW）」を題材に、ヒューリスティクス（Timefold）と混合整数計画法（AMPL + Gurobi / HiGHS）による求解性能を詳細に比較検証したプロジェクトです。

- **`timefold/vrp/`**: 単一デポ / 複数デポ VRP の定式化モデル、ベンチマークスクリプト、スライド資料・論文
- **`timefold/vrp2/`**: フィラデルフィアの 55 訪問先・6 車両・複数デポ MDVRPTW 実験
  - `mdvrptw.mod`: 2添字アーク定式化＋車両割当変数＋タイトな時間伝播 big-M モデル
  - `solve_mdvrptw.py`: データ読込、最小カットによる SEC（部分巡回除去）切除平面法、Gurobi/HiGHS 求解スクリプト
  - `results/`: Timefold 解と Gurobi の比較結果（ルート可視化画像、走行時間短縮ログ）

---

### 4. 最適化モデリングデータセット (`datasets/`, `json_files/`)

#### `datasets/`（数理計画モデリング教科書の問題群）
- **`lectures_in_lp_modeling/`**: 線形計画モデリング講義の問題記述（生産計画、配合問題など）
- **`model_building_in_mathematical_programming/`**: H.P. Williams 著の古典的最適化モデル群（Food Manufacture, Mining, Refinery 等）
- **`introduction_to_linear_optimization/`**: D. Bertsimas 著の線形計画法標準問題群

#### `json_files/`（代表的 OR 問題の標準インスタンス）
- `vehicle-routing`（配車配送計画）
- `employee-scheduling`（従業員シフトスケジューリング）
- `facility-location`（施設配置問題）
- `task-assigning`（タスク割当問題）
- `school-timetabling` / `meeting-scheduling`（時間割・会議調整）
- その他多数（フライトクルー、保全計画、トーナメント日程など）

---

## ビルド・実行手順

### LaTeX 文書のコンパイル
LaTeX 文書（論文・スライド）はすべて **LuaLaTeX** でコンパイルします（TeX Live 2020 以降推奨）。日本語フォントには原ノ味フォント（`haranoaji`）を使用しています。

#### 初学者向けスライド (`beamer/`) のコンパイル
```bash
cd beamer
latexmk -lualatex latex_basics.tex
```

#### スラッシュコマンド比較論文・スライド (`latex/`) のコンパイル
```bash
cd latex
latexmk -lualatex slash_commands_comparison.tex   # 論文
latexmk -lualatex slash_commands_slides.tex       # スライド
```

#### 中間ファイルのクリーンアップ
```bash
latexmk -c
```

### Python スクリプトの実行環境
Python 環境の管理には `uv` を使用し、ローカルの `.venv` 仮想環境を作成して実行します。

```bash
# 仮想環境の作成と有効化
uv venv .venv
source .venv/bin/activate

# 必要なパッケージのインストール例（AMPL / 数理最適化）
uv pip install amplpy pandas matplotlib
```

---

## 補足事項・運用メモ

- **Beamer のフォント設定**: スライド（`metropolis` テーマ）では、サンセリフ体においてロゴの負のカーニングによる文字重なりを防ぐため、`\LaTeX` / `\TeX` はプレーン表記で出力されるよう調整されています。
- **引用文献の番号付け**:
  - スラッシュコマンド比較の論文版と PowerPoint 版は全58件の通し番号（[1]〜[58]）を採用。
  - beamer 版はスライド内で引用する28件を登場順に番号付けしています。
