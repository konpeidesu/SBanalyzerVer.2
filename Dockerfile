# Amazon Linux 2023に近いPythonイメージを使用
FROM python:3.10-slim

# 作業ディレクトリ作成
WORKDIR /app

# 依存ファイルをコピー
COPY requirements.txt .

# ライブラリをインストール
RUN pip install --upgrade pip \
    && pip install -r requirements.txt

# アプリ本体をコピー
COPY . .

# 環境変数（Flaskを開発モードに）
ENV FLASK_APP=run.py
ENV FLASK_ENV=development

# ポート解放（Flaskデフォルト）
EXPOSE 5000

# Flask起動
CMD ["flask", "run", "--host=0.0.0.0"]
