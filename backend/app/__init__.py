# Flaskアプリ初期化

from flask import Flask
from flask_cors import CORS  # Reactからのアクセスを許可するため
from dotenv import load_dotenv  # .envファイルを読み込む
import os

def create_app():
    # .envファイルの環境変数を読み込む
    load_dotenv()

    # Flaskアプリを作成
    app = Flask(__name__)

    # CORS（クロスオリジン）設定：Reactなど他のドメインからのアクセスを許可
    CORS(app)

    # ルーティング（APIのURL設定）を読み込む
    from .routes import main as main_blueprint
    app.register_blueprint(main_blueprint)

    return app  # 作成したアプリを返す
