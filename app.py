import streamlit as st
import cv2
import numpy as np
from PIL import Image

st.title("🏠 リフォームイメージ作成アプリ")
st.write("部屋の写真をアップロードして、床材や壁紙を合成してみましょう。")

uploaded_file = st.file_uploader("部屋の写真をアップロード", type=["jpg", "jpeg", "png"])

if uploaded_file is not None:
    image = Image.open(uploaded_file)
    img_np = np.array(image)
    h, w, _ = img_np.shape

    st.subheader("1. 床（または壁）の位置を指定")
    st.write("スライダーを動かして、赤い枠線を床の四角形（4つの角）に合わせてください。")

    col1, col2 = st.columns(2)
    with col1:
        x1 = st.slider("左上 X", 0, w, int(w * 0.25))
        y1 = st.slider("左上 Y", 0, h, int(h * 0.60))
        x2 = st.slider("左下 X", 0, w, int(w * 0.05))
        y2 = st.slider("左下 Y", 0, h, int(h * 0.95))
    with col2:
        x3 = st.slider("右上 X", 0, w, int(w * 0.75))
        y3 = st.slider("右上 Y", 0, h, int(h * 0.60))
        x4 = st.slider("右下 X", 0, w, int(w * 0.95))
        y4 = st.slider("右下 Y", 0, h, int(h * 0.95))

    # --- ガイド線（赤枠と青丸）を描画したプレビュー画像を作成 ---
    pts_guide = np.array([[x1, y1], [x3, y3], [x4, y4], [x2, y2]], np.int32)
    pts_guide = pts_guide.reshape((-1, 1, 2))
    
    img_preview = img_np.copy()
    # 4点を繋ぐ赤い枠線
    cv2.polylines(img_preview, [pts_guide], isClosed=True, color=(255, 0, 0), thickness=8)
    # 4つの角に青い丸印
    for pt in [[x1, y1], [x3, y3], [x2, y2], [x4, y4]]:
        cv2.circle(img_preview, (pt[0], pt[1]), 20, (0, 0, 255), -1)

    st.image(img_preview, caption="位置確認用プレビュー（赤枠が指定範囲です）", use_container_width=True)

    st.subheader("2. 張り替える素材を選択")
    selected_floor = st.selectbox("床材パターン", ["木目調フローリング（ナチュラル）", "ダークウォールナット", "大理石タイル"])

    if st.button("イメージを合成する"):
        texture = np.zeros((400, 400, 3), dtype=np.uint8)
        if "ナチュラル" in selected_floor:
            texture[:] = (120, 180, 220)
        elif "ダーク" in selected_floor:
            texture[:] = (40, 60, 90)
        else:
            texture[:] = (230, 230, 230)

        pts1 = np.float32([[0, 0], [400, 0], [0, 400], [400, 400]])
        pts2 = np.float32([[x1, y1], [x3, y3], [x2, y2], [x4, y4]])

        matrix = cv2.getPerspectiveTransform(pts1, pts2)
        transformed_texture = cv2.warpPerspective(texture, matrix, (w, h))

        mask = np.zeros((h, w), dtype=np.uint8)
        cv2.fillConvexPoly(mask, np.int32(pts2), 255)

        img_result = img_np.copy()
        img_result[mask == 255] = transformed_texture[mask == 255]

        st.success("合成が完了しました！")
        st.image(img_result, caption="リフォーム後イメージ", use_container_width=True)
