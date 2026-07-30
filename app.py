import streamlit as st
import cv2
import numpy as np
from PIL import Image

st.title("🏠 リフォームイメージ作成アプリ")
st.write("部屋の写真をアップロードして、床材や壁紙を合成してみましょう。")

# 1. 部屋の写真をアップロード
uploaded_file = st.file_uploader("部屋の写真をアップロード", type=["jpg", "jpeg", "png"])

if uploaded_file is not None:
    # 画像を読み込み
    image = Image.open(uploaded_file)
    img_np = np.array(image)
    
    st.image(image, caption="アップロード画像", use_container_width=True)

    st.subheader("1. 床（または壁）の位置を指定")
    st.write("画像の中の『床（または壁）』の4箇所の角の座標を指定してください（単位: ピクセル）。")
    
    # 画像のサイズを取得
    h, w, _ = img_np.shape

    # 簡易的な位置調整（スライダーで4つの角を指定）
    col1, col2 = st.columns(2)
    with col1:
        x1 = st.slider("左上 X", 0, w, int(w * 0.2))
        y1 = st.slider("左上 Y", 0, h, int(h * 0.6))
        x2 = st.slider("左下 X", 0, w, int(w * 0.0))
        y2 = st.slider("左下 Y", 0, h, h)
    with col2:
        x3 = st.slider("右上 X", 0, w, int(w * 0.8))
        y3 = st.slider("右上 Y", 0, h, int(h * 0.6))
        x4 = st.slider("右下 X", 0, w, w)
        y4 = st.slider("右下 Y", 0, h, h)

    st.subheader("2. 張り替える素材を選択")
    selected_floor = st.selectbox("床材パターン", ["木目調フローリング（ナチュラル）", "ダークウォールナット", "大理石タイル"])

    if st.button("イメージを合成する"):
        # ダミーの素材画像生成（テスト用: 選択に応じた色・パターンの画像を自動生成）
        texture = np.zeros((400, 400, 3), dtype=np.uint8)
        if "ナチュラル" in selected_floor:
            texture[:] = (120, 180, 220) # 木目色（RGB）
        elif "ダーク" in selected_floor:
            texture[:] = (40, 60, 90)
        else:
            texture[:] = (230, 230, 230)

        # 遠近変換（透視変換 / Perspective Transform）の計算
        pts1 = np.float32([[0, 0], [400, 0], [0, 400], [400, 400]]) # テクスチャの4角
        pts2 = np.float32([[x1, y1], [x3, y3], [x2, y2], [x4, y4]]) # 写真上の指定4角

        # 変換行列を取得して変形
        matrix = cv2.getPerspectiveTransform(pts1, pts2)
        transformed_texture = cv2.warpPerspective(texture, matrix, (w, h))

        # マスクの作成と合成
        mask = np.zeros((h, w), dtype=np.uint8)
        cv2.fillConvexPoly(mask, np.int32(pts2), 255)
        
        # 写真と変形画像を重ね合わせ
        img_result = img_np.copy()
        img_result[mask == 255] = transformed_texture[mask == 255]

        st.success("合成が完了しました！")
        st.image(img_result, caption="リフォーム後イメージ", use_container_width=True)
