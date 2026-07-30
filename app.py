import streamlit as st
import cv2
import numpy as np
from PIL import Image
from streamlit_image_coordinates import streamlit_image_coordinates

st.title("🏠 リフォームイメージ作成アプリ")
st.write("部屋の写真をアップロードして、床材や壁紙を合成してみましょう。")

uploaded_file = st.file_uploader("部屋の写真をアップロード", type=["jpg", "jpeg", "png"])

if uploaded_file is not None:
    # 画像の読み込みと自動リサイズ（メモリオーバー対策）
    image = Image.open(uploaded_file)
    max_size = 1000
    image.thumbnail((max_size, max_size))
    
    img_np = np.array(image)
    h, w, _ = img_np.shape

    st.subheader("1. 床（または壁）の角をタップ（3〜6箇所）")
    st.write("時計回りに角をタップしてください。最大6箇所まで指定できます（4箇所や5箇所でもOK）。")

    if "points" not in st.session_state:
        st.session_state.points = []

    if st.button("選択した点をリセット"):
        st.session_state.points = []
        st.rerun()

    # ガイドの描画（選択した点に赤い丸と番号を表示）
    img_display = img_np.copy()
    for i, pt in enumerate(st.session_state.points):
        cv2.circle(img_display, (pt[0], pt[1]), 10, (255, 0, 0), -1)
        cv2.putText(img_display, str(i + 1), (pt[0] + 15, pt[1] + 15),
                    cv2.FONT_HERSHEY_SIMPLEX, 1.0, (255, 255, 255), 2)

    # 3点以上あれば多角形の外枠線を描画
    if len(st.session_state.points) >= 3:
        pts_arr = np.array(st.session_state.points, np.int32).reshape((-1, 1, 2))
        cv2.polylines(img_display, [pts_arr], isClosed=True, color=(255, 0, 0), thickness=3)

    img_pil_display = Image.fromarray(img_display)
    coords = streamlit_image_coordinates(img_pil_display, key="pil_coords")

    # 6点未満の場合のみタップを受け付ける
    if coords is not None and len(st.session_state.points) < 6:
        click_x = int(coords["x"])
        click_y = int(coords["y"])
        
        new_pt = [click_x, click_y]
        if not st.session_state.points or st.session_state.points[-1] != new_pt:
            st.session_state.points.append(new_pt)
            st.rerun()

    st.write(f"現在選択された点の数: {len(st.session_state.points)} / 6 (最小3点が必要)")

    # 2. 素材選択
    st.subheader("2. 張り替える素材を選択")
    selected_floor = st.selectbox("床材パターン", ["木目調フローリング（ナチュラル）", "ダークウォールナット", "大理石タイル"])

    # 3点以上選択されていれば「イメージを合成する」ボタンを有効化
    if len(st.session_state.points) >= 3:
        if st.button("イメージを合成する"):
            # 選択された床材に応じた色設定（タイポを修正）
            if "ナチュラル" in selected_floor:
                color = [220, 180, 120]  # RGB指定
            elif "ダーク" in selected_floor:
                color = [90, 60, 40]
            else:
                color = [230, 230, 230]

            # 多角形（3〜6角形）のマスク作成
            mask = np.zeros((h, w), dtype=np.uint8)
            pts_array = np.array([st.session_state.points], dtype=np.int32)
            cv2.fillPoly(mask, pts_array, 255)

            # 指定エリアを隙間なく完璧に塗り潰す
            img_result = img_np.copy()
            img_result[mask == 255] = color

            st.success("合成が完了しました！")
            st.image(img_result, caption="リフォーム後イメージ", use_container_width=True)
    else:
        st.info("画像上の角を3箇所以上（最大6箇所）タップすると、合成ボタンが有効化されます。")
