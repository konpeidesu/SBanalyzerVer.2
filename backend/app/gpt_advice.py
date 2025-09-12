# ChatGPT APIでのアドバイス生成

import os
import openai
from dotenv import load_dotenv

# .envファイルの読み込み（APIキーなど）
load_dotenv()

# OpenAI APIキーを設定
openai.api_key = os.getenv("OPENAI_API_KEY")

def generate_advice(score: float, result: str, angles: list, joints: list, factors: dict, factor_defs: dict) -> str:
    """
    ChatGPT APIを使用して、日本語でスノーボードの改善アドバイスを生成する関数
    個別スコアとその定義もプロンプトに含める
    """

    # 入力データを整形
    yaw, pitch, roll = angles
    score_percent = round(score * 100, 1)

    # 個別スコアを日本語で列挙
    factors_str = "\n".join([f"- {k}: {v}" for k, v in factors.items()])
    # スコア定義を日本語で列挙
    factor_defs_str = "\n".join([f"- {k}: {v}" for k, v in factor_defs.items()])

    # プロンプト（GPTに送る文章）
    prompt = f"""
以下はスノーボードの「ノーリー」トリックの結果です：
【情報】
- 成功確率: {score_percent}%
- 判定: {result}
- 板の角度:
    - ヨー角（進行方向のズレ）: {yaw:.2f}°
    - ピッチ角（前後の傾き）: {pitch:.2f}°
    - ロール角（横の傾き）: {roll:.2f}°
- 関節の情報（MediaPipe形式、簡略化）: {joints[:8]}...
【個別スコア】
{factors_str}
【スコアの定義】
{factor_defs_str}
【指示】
-これらの情報をもとに、プロのスノーボードコーチのように、「どうすればノーリーの成功率を上げられるか」について、一言で具体的な日本語のアドバイスをください。
-口調は親しみやすく、やさしくコーチングする感じで。
-文字数は120文字以内でお願いします。
-1行に1アドバイスで、箇条書き形式でお願いします。
-アドバイスは合計で3つまでにしてください。
-以下のようなアドバイスは避けてください：
  - 曖昧な表現（例：「もっと頑張りましょう」など）
  - 過度に精神論的な言葉（例：「気持ちで飛び切ろう！」など）
  -テール側の足を蹴り上げるようなアドバイスは避けてください（ノーリーはテールを使わないため）。
-特に以下の点に注意してアドバイスしてください：
    -ノーズ側のかかとを使った急ブレーキが大事なので、ロール角が大きいほど高評価です。
    -目線は足元を見ていると空中姿勢が悪く転倒する可能性が高くなるので、回転の進行方向を見るようにしてください。
    -両腕は回転の進行方向と逆方向に回らないようにしてください。角速度が減少して十分に回転しない可能性が高くなります。なので両腕は身体にできるだけ近づけることが好ましいです
    -上半身の位置はノーズ側のかかとよりも前に出してください。上半身が後ろに下がると板からの十分な反発（弾性エネルギー）を得ることができません。なのでピッチ角は大きいほど高評価です。
    -空中時の体の軸はできる限り真っすぐが良いので、腰が曲がっていないか注意してください。
"""

    # OpenAI Chat APIの呼び出し
    try:
        client = openai.OpenAI()
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "あなたはスノーボードのプロコーチです。"},
                {"role": "user", "content": prompt}
            ],
            max_tokens=150,
            temperature=0.8
        )
        advice = response.choices[0].message.content.strip()
        return advice
    except Exception as e:
        return f"アドバイスの生成中にエラーが発生しました: {str(e)}"
