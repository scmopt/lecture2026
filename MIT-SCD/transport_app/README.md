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
```

`requirements.txt` で HiGHS が入ります。CBC も使う場合は `python -m amplpy.modules install cbc` を実行してください。
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

## Vercel へのデプロイ

フロントエンドとバックエンドを **1つの Vercel プロジェクト** としてデプロイします。
フロントエンドは `/api/...` を同じドメインに問い合わせるので、別々のプロジェクトにすると API に届きません。

- `frontend/` を Vite でビルドし、`frontend/dist` を静的ファイルとして配信する
- `/api/*` へのリクエストは `vercel.json` の rewrites で Python 関数 `api/index.py` に転送され、`backend/main.py` の FastAPI アプリが処理する
- Python の依存パッケージは `requirements.txt`（`backend/requirements.txt` を参照）からインストールされる。AMPL のソルバー（`ampl_module_highs`）は `pypi.ampl.com` から入る

### 手順

1. Vercel で **Add New → Project** からこのリポジトリを読み込む
2. **Root Directory** を `MIT-SCD/transport_app` にする
3. Framework Preset とビルド設定は `vercel.json` の内容が使われるので、そのまま **Deploy** する

すでにフロントエンドとバックエンドを別々のプロジェクトにしている場合は、片方の Root Directory を `MIT-SCD/transport_app` に変えて使い、もう片方は削除してください。

### 注意

- Vercel 上で使えるソルバーは HiGHS だけです（Gurobi はライセンスが必要なため入れていません）
- ライセンスを設定しない AMPL には問題サイズの制限があります（目安は変数・制約が数百個まで）。変数の数は顧客数 × サプライヤー数なので、大きなデータを解く場合は無料の [AMPL Community Edition](https://ampl.com/ce) のライセンスを用意してください
- 地図クリックで追加したノードや編集した表はブラウザの中だけにあり、サーバーには保存されません

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
├── vercel.json            # Vercel の設定（ビルド・関数・rewrites）
├── requirements.txt       # Vercel 用（backend/requirements.txt を参照）
├── api/
│   └── index.py           # Vercel の Python 関数（FastAPI アプリを読み込む）
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
