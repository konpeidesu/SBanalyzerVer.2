# 推論ロジック（画像＋関節角度モデル）

import cv2
import numpy as np
import mediapipe as mp
from keras.models import Model
import tempfile
import math
from io import BytesIO
from scipy.spatial.transform import Rotation as R

# MediaPipeのposeモデルの初期化
mp_pose = mp.solutions.pose

# OpenCVのバイナリ画像データをNumPy配列に変換
def bytes_to_cv2_image(image_bytes):
    np_array = np.frombuffer(image_bytes, np.uint8)
    image = cv2.imdecode(np_array, cv2.IMREAD_COLOR)
    return image

# 関節座標の抽出（world_landmarks: 33点, x/y/z）
def extract_pose_landmarks(image):
    mp_pose = mp.solutions.pose
    with mp_pose.Pose(static_image_mode=True) as pose:
        img_rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
        results = pose.process(img_rgb)
        if not results.pose_world_landmarks:
            raise ValueError("関節が検出できませんでした")
        # 33個のlandmarkオブジェクトリストを返す
        return results.pose_world_landmarks.landmark

# 板の角度（roll, pitch, yaw）を左右足首と腰（中央）から算出
def calculate_board_angles(landmarks_3d):
    """
    左右足首と腰（中央）から板の法線ベクトルを計算し、
    雪面（地面）法線（[0,0,1]）を基準としたroll, pitch, yawを返します。
    landmarks: [landmark0, landmark1, ...] (MediaPipeのlandmarkオブジェクト)
    戻り値: (roll, pitch, yaw) すべて単位は度（float）
      - roll: 板の左右の傾き（地面基準）
      - pitch: 板の前後の傾き（地面基準）
      - yaw: 板の進行方向の回転（地面基準）
    ランドマークが不正な場合は (np.nan, np.nan, np.nan) を返します。
    """
    try:
        # MediaPipe Pose: 左足首=27, 右足首=28, 左腰=23, 右腰=24
        l_ankle = landmarks_3d[27]
        r_ankle = landmarks_3d[28]
        l_hip = landmarks_3d[23]
        r_hip = landmarks_3d[24]
        # 腰の中心（左腰と右腰の中点）
        mid_hip = np.array([
            (l_hip.x + r_hip.x) / 2,
            (l_hip.y + r_hip.y) / 2,
            (l_hip.z + r_hip.z) / 2
        ])
        # 足首ベクトル（板の横方向）
        ankle_vec = np.array([
            r_ankle.x - l_ankle.x,
            r_ankle.y - l_ankle.y,
            r_ankle.z - l_ankle.z
        ])
        # 両足首の中点
        mid_ankle = np.array([
            (l_ankle.x + r_ankle.x) / 2,
            (l_ankle.y + r_ankle.y) / 2,
            (l_ankle.z + r_ankle.z) / 2
        ])
        # 板の進行方向ベクトル（腰→両足首の中点）
        forward_vec = mid_ankle - mid_hip
        # 板の法線ベクトル（右手系: forward_vec × ankle_vec）
        normal_vec = np.cross(forward_vec, ankle_vec)
        normal_vec = normal_vec / np.linalg.norm(normal_vec)
        # roll: 板の左右の傾き（地面基準, y成分）
        roll = -np.degrees(np.arcsin(normal_vec[1]))
        # pitch: 板の前後の傾き（地面基準, x成分）
        pitch = np.degrees(np.arcsin(normal_vec[0]))
        # yaw: 板の進行方向（forward_vec）と地面x軸のなす角
        yaw = np.degrees(np.arctan2(forward_vec[1], forward_vec[0]))
        return np.array([roll, pitch, yaw])
    except Exception:
        return np.array([np.nan, np.nan, np.nan])

# 推論処理（画像バイト、2モデル） → 成功確率、結果、角度、関節を返す
def run_inference(image_bytes, image_model: Model, pose_model: Model):
    # バイナリ画像 → OpenCV画像
    image = bytes_to_cv2_image(image_bytes)

    # 関節情報を取得（3D landmarksリスト）
    landmarks_3d = extract_pose_landmarks(image)
    if landmarks_3d is None:
        raise ValueError("関節が検出できませんでした")

    # flatten配列（x, y, z のみ）
    joint_array = []
    for lm in landmarks_3d:
        joint_array.extend([lm.x, lm.y, lm.z])
    # 板の角度を算出
    angles = calculate_board_angles(landmarks_3d)
    # ----- pose_model（関節＋角度モデル）推論 -----
    pose_input = np.concatenate([joint_array, angles]).reshape(1, -1)
    print(f"[DEBUG] pose_input shape: {pose_input.shape}")  # shape確認
    pose_score = pose_model.predict(pose_input)[0][0]  # 出力は1つの確率

    # ----- image_model（画像モデル）推論 -----
    # モデルに合わせて画像リサイズ
    resized = cv2.resize(image, (828, 1792))  # モデルに応じて調整
    img_input = resized / 255.0  # 正規化
    img_input = np.expand_dims(img_input, axis=0)
    image_score = image_model.predict(img_input)[0][0]

    # ----- アンサンブル（pose_board_modelを強く反映） -----
    final_score = float((pose_score * 0.4 + image_score * 0.6))  #重みづけ調整
    result = "成功" if final_score >= 0.65 else "失敗"

    # ----- 信頼度計算（3:一致度＋4:安定性） -----
    agree_conf = 1 - abs(pose_score - image_score)  # 0〜1, 差が小さいほど高
    if np.isnan(angles).any():
        pose_conf = 0.5  # NaNありは減点
    else:
        pose_conf = 1.0
    confidence = int((agree_conf * 0.7 + pose_conf * 0.3) * 100)

    # 返却値をすべてPythonの標準型に変換
    return final_score, result, [float(a) for a in angles.tolist()], [float(x) for x in joint_array], confidence


# --- JSX/Reactの誤混入部分を完全削除 ---

