# lecture2026

2026年度の講義資料です。現在は「AIツールのスラッシュコマンド比較」を収録しています。
Google Antigravity、Anthropic Claude Code、OpenAI Codex CLI の3つのAIコーディングエージェントについて、スラッシュコマンドの仕様、カスタムコマンドの作り方、アーキテクチャの違い、セキュリティ上のリスクを比較しています。

## ディレクトリ構成

```
lecture2026/
├── markdown/
│   ├── AIツールのスラッシュコマンド比較.md    # 元になったレポート（Markdown）
│   └── AIツールのスラッシュコマンド比較.pdf
└── latex/
    ├── slash_commands_comparison.tex         # 論文版（LuaLaTeX, ltjsarticle）
    ├── slash_commands_comparison.pdf
    ├── slash_commands_slides.tex             # スライド版（beamer, metropolis テーマ）
    ├── slash_commands_slides.pdf
    └── slash_commands_slides.pptx            # スライド版（PowerPoint）
```

| ファイル | 形式 | 内容 |
|---|---|---|
| `markdown/AIツールのスラッシュコマンド比較.md` | Markdown | 元のレポート（全8章、引用文献58件） |
| `latex/slash_commands_comparison.tex` | LaTeX 論文 | レポートを論文形式にしたもの。概要・キーワード付き、表4つ（14ページ） |
| `latex/slash_commands_slides.tex` | beamer | 講義用スライド（16:9、32ページ） |
| `latex/slash_commands_slides.pptx` | PowerPoint | beamer版をもとにしたスライド（16:9、30枚） |

## ビルド方法

LaTeX ファイルはすべて **LuaLaTeX** でコンパイルします（TeX Live 2026 で確認）。

```bash
cd latex
latexmk -lualatex slash_commands_comparison.tex   # 論文
latexmk -lualatex slash_commands_slides.tex       # スライド
```

中間ファイルを削除するには次を実行します。

```bash
latexmk -c
```

### 必要なパッケージ

- 論文：`luatexja`（`ltjsarticle`）、`booktabs`、`tabularx`、`enumitem`、`hyperref`、`xurl`
- スライド：`beamer`、`beamertheme-metropolis`、`luatexja-preset`（原ノ味フォント）

metropolis テーマは Fira フォントがなくても動作します（その場合は代替フォントで表示されます）。

## 引用文献の番号について

- 論文版と PowerPoint 版は、元のレポートと同じ番号（[1]〜[58]）を使っています。
- beamer 版は、スライド中で引用している28件だけを登場順に [1]〜[28] と振り直しています。

## 補足

- PowerPoint 版の日本語フォントは游ゴシック（Yu Gothic）を指定しています。
- スライド中のコマンド例の一部（MCP 連携コマンド名、`fix-issue.md` や TOML の中身）は説明用に作った例で、スライド上にもその旨を書いています。
