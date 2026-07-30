import streamlit as st
import cv2
import numpy as np
from PIL import Image
from streamlit_image_coordinates import streamlit_image_coordinates

st.title("🏠 リフォームイメージ作成アプリ")
st.write("部屋の写真をアップロードして、床材や壁紙を合成してみましょう。")

# テクスチャ画像をプログラム内で自動生成する関数
def generate_texture(pattern_type):
    # 200x200ピクセルのキャンバスを作成
    tex = np.zeros((200, 200, 3), dtype=np.uint8)
    
    if pattern_type == "oak":  # オーク木目
        tex[:] = (210, 180, 140)
        for y in range(0, 200, 20):  # 板目・木目線
            cv2.line(tex, (0, y), (200, y), (180, 150, 110), 2)
            cv2.line(tex, (0, y+1), (200, y+1), (230, 200, 160), 1)
            
    elif pattern_type == "walnut":  # ウォールナット木目
        tex[:] = (80, 55, 35)
        for y in range(0, 200, 25):
            cv2.line(tex, (0, y), (200, y), (50, 35, 20), 3)
            cv2.line(tex, (0, y+1), (200, y+1), (100, 70, 45), 1)
            
    elif pattern_type == "brick":  # レンガ調クロス
        tex[:] = (240, 240, 235)
        # 横目地
        for y in range(0, 200, 30):
            cv2.line(tex, (0, y), (200, y), (200, 200, 195), 2)
        # 縦目地
        for y_idx, y in enumerate(range(0, 200, 30)):
            offset = 50 if y_idx % 2 == 1 else 0
            for x in range(offset, 200, 100):
                cv2.line(tex, (x, y), (x, y+30), (200, 200, 195), 2)
                
    elif pattern_type == "gray_fabric":  # シックグレー織物調
        tex[:] = (130, 135, 140)
        # 織り目グリッド
        for i in range(0, 200, 6):
            cv2.line(tex, (i, 0), (i, 200), (115, 120, 125), 1)
            cv2.line(tex, (0, i), (200, i), (145, 150, 155), 1)
            
    return tex

uploaded_file = st.file_uploader("部屋の写真をアップロード", type=["jpg", "jpeg", "png"])

if uploaded_file is not None:
    image = Image.open(uploaded_file)
    max_size = 1000
    image.thumbnail((max_size, max_size))
    
    img_np = np.array(image)
    h, w, _ = img_np.shape

    st.subheader("1. 張り替えるエリア（床または壁）の角をタップ（3〜6箇所）")
    st.write("時計回りに角をタップしてください。最大6箇所まで指定できます。")

    if "points" not in st.session_state:
        st.session_state.points = []

    if st.button("選択した点をリセット"):
        st.session_state.points = []
        st.rerun()

    img_display = img_np.copy()
    for i, pt in enumerate(st.session_state.points):
        cv2.circle(img_display, (pt[0], pt[1]), 10, (255, 0, 0), -1)
        cv2.putText(img_display, str(i + 1), (pt[0] + 15, pt[1] + 15),
                    cv2.FONT_HERSHEY_SIMPLEX, 1.0, (255, 255, 255), 2)

    if len(st.session_state.points) >= 3:
        pts_arr = np.array(st.session_state.points, np.int32).reshape((-1, 1, 2))
        cv2.polylines(img_display, [pts_arr], isClosed=True, color=(255, 0, 0), thickness=3)

    img_pil_display = Image.fromarray(img_display)
    coords = streamlit_image_coordinates(img_pil_display, key="pil_coords")

    if coords is not None and len(st.session_state.points) < 6:
        click_x = int(coords["x"])
        click_y = int(coords["y"])
        
        new_pt = [click_x, click_y]
        if not st.session_state.points or st.session_state.points[-1] != new_pt:
            st.session_state.points.append(new_pt)
            st.rerun()

    st.write(f"現在選択された点の数: {len(st.session_state.points)} / 6 (最小3点が必要)")

    st.subheader("2. 張り替える素材を選択")
    
    target_type = st.radio("張り替える部位", ["床材", "壁紙"], horizontal=True)

    if target_type == "床材":
        selected_material = st.selectbox("床材パターン", [
            "オークフローリング（ナチュラル木目）", 
            "ダークウォールナット（深み木目）"
        ])
        pattern_key = "oak" if "オーク" in selected_material else "walnut"
    else:
        selected_material = st.selectbox("壁紙パターン", [
            "シックグレー（織物クロス調）", 
            "レンガ調ホワイトクロス"
        ])
        pattern_key = "gray_fabric" if "グレー" in selected_material else "brick"

    if len(st.session_state.points) >= 3:
        if st.button("イメージを合成する"):
            # プログラム内生成テクスチャを取得
            tex_img = generate_texture(pattern_key)
            
            # 画像全体にテクスチャをタイリング（敷き詰め）
            th, tw, _ = tex_img.shape
            tiled_texture = np.tile(tex_img, (h // th + 1, w // tw + 1, 1))[:h, :w]

            # 多角形マスクの作成
            mask = np.zeros((h, w), dtype=np.uint8)
            pts_array = np.array([st.session_state.points], dtype=np.int32)
            cv2.fillPoly(mask, pts_array, 255)

            # テクスチャの重ね合わせ
            img_result = img_np.copy()
            img_result[mask == 255] = tiled_texture[mask == 255]

            st.success("リアルなテクスチャ柄で合成が完了しました！")
            st.image(img_result, caption="リフォーム後イメージ", use_container_width=True)
    else:
        st.info("画像上の角を3箇所以上（最大6箇所）タップすると、合成ボタンが有効化されます。")
