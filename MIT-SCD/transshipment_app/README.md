# 積換問題 Web アプリ

`02Transshipment_Problem_Python_Exercise_ja.py` の積換問題を、ブラウザで操作できるようにしたアプリです。

- **backend/**: FastAPI と AMPL（amplpy）で最適化を行う
- **frontend/**: React + TypeScript + Vite で作った画面（地図は Leaflet、表は AG Grid）

## できること

- 顧客・倉庫・サプライヤーのデータを CSV で読み込む、表で直接編集する、CSV でダウンロードする
- 地図をクリックしてノード（顧客 / 倉庫 / サプライヤー）を追加する、マーカーをドラッグして移動する
- 区間別（サプライヤー→倉庫、倉庫→顧客）の距離あたり輸送コスト、距離の単位（km / mi）、ソルバーを変更する
- 倉庫の容量制約（Task 1）をトグルで ON/OFF して比較する
- 需要の未充足を許し、1単位あたりのペナルティを設定する
- 2段階の最適フロー（S→W: オレンジ、W→C: ブルー）を地図と表で確認し、CSV でダウンロードする

## 準備

Python 3.10 以上と Node.js 20 以上が必要です。

```bash
cd transshipment_app/backend
pip install -r requirements.txt
```

```bash
cd transshipment_app/frontend
npm install
```

## 起動方法

### A. ビルドして1つのサーバーで動かす

```bash
cd transshipment_app/frontend
npm run build
cd ../backend
uvicorn main:app
```

ブラウザで http://localhost:8000 を開きます。

### B. 開発モード（フロントエンドを書き換えながら確認する）

ターミナルを2つ使います。

```bash
cd transshipment_app/backend
uvicorn main:app --reload
```

```bash
cd transshipment_app/frontend
npm run dev
```

ブラウザで http://localhost:5173 を開きます。`/api` へのアクセスは自動で FastAPI に転送されます。

## Vercel へのデプロイ

1. Vercel で **Add New → Project** からこのリポジトリを読み込む
2. **Root Directory** を `MIT-SCD/transshipment_app` にする
3. `vercel.json` の設定がそのまま使われるので **Deploy** する
