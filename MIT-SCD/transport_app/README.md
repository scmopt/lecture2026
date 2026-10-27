# 輸送問題 Web アプリ

`01Transportation_Problem_ja.py` の輸送問題を、ブラウザで操作できるようにしたアプリです。

- **backend/**: FastAPI と AMPL（amplpy）で最適化を行う
- **frontend/**: React + TypeScript + Vite で作った画面（地図は Leaflet、表は AG Grid）

## できること

- 顧客・サプライヤーのデータを CSV で読み込む、表で直接編集する、CSV でダウンロードする
- 地図をクリックしてノードを追加する、マーカーをドラッグして移動する
- 距離あたり輸送コスト、距離の単位（km / mi）、ソルバーを変更する
- 需要の未充足を許し、1単位あたりのペナルティを設定する（総供給量が足りないとき用）
- 最適なフローを地図と表で確認し、CSV でダウンロードする

## 準備

Python 3.10 以上と Node.js 20 以上が必要です。

```bash
cd transport_app/backend
pip install -r requirements.txt
python -m amplpy.modules install highs cbc
```

Gurobi を使う場合は `python -m amplpy.modules install gurobi` も実行し、ライセンスを設定してください。
画面のソルバー一覧には、インストール済みのものだけが表示されます。

```bash
cd transport_app/frontend
npm install
```

## 起動方法

### A. ビルドして1つのサーバーで動かす

```bash
cd transport_app/frontend
npm run build
cd ../backend
uvicorn main:app
```

ブラウザで http://localhost:8000 を開きます。

### B. 開発モード（フロントエンドを書き換えながら確認する）

ターミナルを2つ使います。

```bash
cd transport_app/backend
uvicorn main:app --reload
```

```bash
cd transport_app/frontend
npm run dev
```

ブラウザで http://localhost:5173 を開きます。`/api` へのアクセスは自動で FastAPI に転送されます。

## API

| メソッド | パス | 内容 |
| --- | --- | --- |
| GET | `/api/solvers` | 利用可能なソルバーの一覧 |
| GET | `/api/sample` | サンプルデータ（`backend/data/*.csv`） |
| POST | `/api/solve` | 輸送問題を解く |

API の詳細は、バックエンド起動中に http://localhost:8000/docs で確認できます。

## ファイル構成

```
transport_app/
├── backend/
│   ├── main.py            # FastAPI のエンドポイント
│   ├── transport_core.py  # 距離計算・AMPL モデル・求解
│   ├── requirements.txt
│   └── data/              # サンプル CSV
└── frontend/
    ├── src/
    │   ├── App.tsx              # 画面全体（パラメータ・結果・タブ）
    │   ├── api.ts               # バックエンドとの通信
    │   ├── csv.ts               # CSV の読み込み・ダウンロード
    │   ├── types.ts
    │   └── components/
    │       ├── MapView.tsx      # 地図（ノードとフロー）
    │       ├── NodeTable.tsx    # 顧客・サプライヤーの編集表
    │       └── ResultTable.tsx  # 最適フローの表
    ├── package.json
    └── vite.config.ts
```
