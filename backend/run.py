# Flaskアプリ起動用
# Flaskアプリを作成する関数をインポート
from app import create_app

# Flaskアプリのインスタンスを作成
app = create_app()

# Pythonファイルを直接実行したときにアプリを起動
if __name__ == "__main__":
    # デバッグモードで起動（エラー表示がわかりやすくなる）
    app.run(debug=False)
