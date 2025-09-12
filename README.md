# Snowboard Trick Analyzer - Webアプリ開発仕様まとめ

## 📌 プロジェクト概要
**目的**：スノーボードのトリック「ノーリー」の飛ぶ直前の画像を使い、成功 or 失敗を確率付きで判定し、さらに改善アドバイスを日本語のコーチ風に表示する。

**対象ユーザー**：自分自身（個人用ツール）

**主な利用シーン**：トリックの映像を切り出した.png画像をアップロード → 成功判定と改善点を知る

---

## 🧠 機能仕様

### 🔹 フロントエンド（ユーザー目線）
- .png画像ファイルを1枚ずつアップロード
- 成功確率（例：84%）と判定（成功 / 失敗）を表示
- 日本語の改善アドバイス（コーチ風）を表示

### 🔹 バックエンド（システム処理）
- Flask APIで画像を受信
- OpenCVで画像処理
- MediaPipeで関節座標を取得
- 回転行列から板の角度（ヨー・ピッチ・ロール）を算出
- 以下の2つのモデルを使用し、アンサンブルで推論：
    - .h5：画像のみの学習モデル（NOLLIE_MODEL.h5）
    - .keras：関節座標＋板角度のモデル（pose_board_model.keras）
- 成功確率（0～1）を返す
- 成功/失敗を分類（閾値0.5）
- ChatGPT APIを用いて改善アドバイスを日本語で生成

---

## 🧰 技術スタック
| カテゴリ         | 使用技術                                   |
|------------------|--------------------------------------------|
| フロントエンド   | React（1画面SPA）                         |
| バックエンド     | Flask（APIサーバー）                       |
| モデル           | .h5, .keras（S3からDL）                    |
| AI補助           | OpenAI ChatGPT API（アドバイス生成）        |
| モデル取得       | boto3（AWS S3から初回のみDL）              |
| 開発環境         | VSCode（WSL＋Dockerで本番模倣）            |

---

## 📁 ディレクトリ構成（予定）
```
project-root/
├── backend/
│   ├── app/
│   │   ├── __init__.py
│   │   ├── routes.py            # FlaskルーティングとAPI処理
│   │   ├── model_loader.py      # モデルのS3ダウンロードとキャッシュ
│   │   ├── inference.py         # 推論ロジック（画像＋関節角度モデル）
│   │   └── gpt_advice.py        # ChatGPT APIでのアドバイス生成
│   ├── requirements.txt
│   ├── .env
│   └── run.py
├── frontend/
│   ├── src/
│   │   ├── components/
│   │   ├── App.jsx
│   │   └── index.jsx
│   ├── public/
│   ├── .env
│   └── package.json
├── docker-compose.yml
└── README.md
```

---

## 🔐 環境変数（.env）
```env
# ChatGPT用
OPENAI_API_KEY=sk-xxxxxx

# S3用
AWS_ACCESS_KEY_ID=xxxxxx
AWS_SECRET_ACCESS_KEY=xxxxxx
S3_BUCKET_NAME=sb--storage

# モデルファイル名
IMAGE_MODEL_FILENAME=NOLLIE_MODEL.h5
POSE_MODEL_FILENAME=pose_board_model.keras
```

---

## 📦 使用ライブラリ（主要）
- 画像処理：OpenCV
- 関節座標検出：MediaPipe
- 数値処理：numpy, pandas
- Webサーバー：Flask, flask-cors, Werkzeug
- クラウド連携：boto3
- ChatGPT API：openai
- 環境管理：python-dotenv

---

## 🧪 API仕様（Flask）
### 🔸 POST /predict
- 内容：画像をアップロードし、成功確率・判定・アドバイスを返す
- リクエスト形式：multipart/form-data
- レスポンス（例）：
```json
{
  "success": true,
  "score": 0.84,
  "result": "成功",
  "advice": "飛ぶ直前にもっと前足に荷重すると良いぞ！"
}
```

---

## 🧊 アンサンブルモデルについて
- 使用モデルは2つで固定
    - NOLLIE_MODEL.h5: 画像モデル（CNN）
    - pose_board_model.keras: 姿勢＋角度モデル（MLPなど）
- 両者の出力（成功確率）を平均 or 加重平均で統合して最終判定
- 今後のモデル追加・変更は予定なし（今は固定構成）

---

## 🐳 Docker対応（今後設計）
- Dockerfile / docker-compose.yml で構築予定
- Flaskサーバー、React開発サーバーを別サービスに分ける
- WSL + Docker で Amazon Linux 2023 を再現

---

## ✅ 決定済み事項まとめ
| 項目           | 内容                                   |
|----------------|----------------------------------------|
| モデルファイル | .h5, .keras（S3からDL）                |
| バケット名     | sb--storage                            |
| 学習モデルDL   | 初回のみDL、以降ローカル利用           |
| API設計        | /predict のみで完結                    |
| 認証           | 不要（ログイン機能なし）               |
| ChatGPT出力    | 日本語、コーチ風アドバイス             |

---

## ✨ 今後やること（工程）
- Flask APIとS3モデルDL実装（バックエンドの心臓部）
- ReactのUIテンプレート作成（画像アップ→表示）
- Docker環境整備（WSLで本番模倣環境）
- ChatGPT連携調整（トークン・プロンプト設計）

---

## 🗒️ 補足
- .venvを使った仮想環境管理を推奨
- requirements.txtで依存を明示し、再現性を担保
- モデルのキャッシュ保存場所は backend/models/ を予定
