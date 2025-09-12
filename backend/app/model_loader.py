# モデルのS3ダウンロードとキャッシュ

import os
import boto3
from dotenv import load_dotenv
from keras.models import load_model  # kerasでモデルを読み込む

# .envファイルの環境変数を読み込む（AWSキー、モデル名など）
load_dotenv()

# 環境変数から取得
AWS_ACCESS_KEY_ID = os.getenv("AWS_ACCESS_KEY_ID")
AWS_SECRET_ACCESS_KEY = os.getenv("AWS_SECRET_ACCESS_KEY")
BUCKET_NAME = os.getenv("S3_BUCKET_NAME")

IMAGE_MODEL_FILENAME = os.getenv("IMAGE_MODEL_FILENAME")      # NOLLIE_MODEL.h5
POSE_MODEL_FILENAME = os.getenv("POSE_MODEL_FILENAME")        # pose_board_model.keras

LOCAL_MODEL_DIR = os.path.join(os.path.dirname(__file__), '..', 'models')  # 保存先

# S3のクライアントを作成（認証情報がすべて揃っている場合のみ）
s3 = None
if AWS_ACCESS_KEY_ID and AWS_SECRET_ACCESS_KEY and BUCKET_NAME:
    s3 = boto3.client(
        's3',
        aws_access_key_id=AWS_ACCESS_KEY_ID,
        aws_secret_access_key=AWS_SECRET_ACCESS_KEY
    )

def download_model_if_not_exists(filename):
    """指定したファイルがmodels/に存在しなければS3からダウンロード"""
    local_path = os.path.join(LOCAL_MODEL_DIR, filename)
    
    if not os.path.exists(LOCAL_MODEL_DIR):
        os.makedirs(LOCAL_MODEL_DIR)
    
    if not os.path.exists(local_path):
        if s3 is not None:
            print(f"モデル {filename} をS3からダウンロード中...")
            s3.download_file(BUCKET_NAME, filename, local_path)
            print("ダウンロード完了")
        else:
            print(f"S3認証情報が未設定のため {filename} のダウンロードをスキップします。ローカルにファイルが必要です。")
    else:
        print(f"{filename} はすでに存在します。ダウンロードをスキップします。")

    return local_path

def load_models():
    """2つのモデルをローカルに用意し、メモリに読み込む"""
    # モデルファイルをS3から必要に応じて取得
    image_model_path = download_model_if_not_exists(IMAGE_MODEL_FILENAME)
    pose_model_path = download_model_if_not_exists(POSE_MODEL_FILENAME)

    # モデルを読み込んでメモリに展開
    image_model = load_model(image_model_path)
    pose_model = load_model(pose_model_path)

    return image_model, pose_model
