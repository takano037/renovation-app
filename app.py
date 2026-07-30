import streamlit as st
import cv2
import numpy as np
from PIL import Image
from streamlit_image_coordinates import streamlit_image_coordinates

st.title("🏠 リフォームイメージ作成アプリ")
st.write("部屋の写真をアップロードして、床材や壁紙を合成してみましょう。")

# リアルなテクスチャ生成関数
def generate_texture(pattern_type):
    tex = np.zeros((400, 400, 3), dtype=np.uint8)
    
    if pattern_type == "oak":  # オーク木目
        tex[:] = (210, 180, 140)
        for y in range(0, 400, 40):
            cv2.line(tex, (0, y), (400, y), (180, 150, 110), 3)
            cv2.line(tex, (0, y+2), (400, y+2), (230, 200, 160), 2)
            
    elif pattern_type == "walnut":  # ウォールナット木目
        tex[:] = (80, 55, 35)
        for y in range(0, 400, 50):
            cv2.line(tex, (0, y), (400, y), (50, 35, 20), 4)
            cv2.line(tex, (0, y+2), (400, y+2), (100, 70, 45), 2)
            
    elif pattern_type == "brick":  # レンガ調クロス
        tex[:] = (245, 245, 240)
        for y in range(0, 400, 40):
            cv2.line(tex, (0, y), (400, y), (200, 200, 190), 2)
        for y_idx, y in enumerate(range(0, 400, 40)):
            offset = 100 if y_idx % 2 == 1 else 0
            for x in range(offset, 400, 200):
                cv2.line(tex, (x, y), (x, y+40), (200, 200, 190), 2)
                
    elif pattern_type == "gray_fabric":  # シックグレー織物調
        tex[:] = (130, 135, 140)
        for i in range(0, 400, 10):
            cv2.line(tex, (i, 0), (i, 400), (115, 120, 125), 1)
            cv2.line(tex, (0, i), (400, i), (145, 150, 155), 1)
            
    return tex

uploaded_file = st.file_uploader("部屋の写真をアップロード", type=["jpg", "jpeg", "png"])

if uploaded_file is not None:
    image = Image.open(uploaded_file)
    max_size = 1000
    image.thumbnail((max_size, max_size))
    
    img_np = np.array(image)
    h, w, _ = img_np.shape

    st.subheader("1. 張り替えるエリア（床または壁）の角をタップ（4箇所推称）")
    st.write("時計回りに角をタップしてください（※奥行き計算のため4点指定が最も綺麗になります）。")

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
        selected_material = st.selectbox("床材パターン", ["オークフローリング（ナチュラル木目）", "ダークウォールナット（深み木目）"])
        pattern_key = "oak" if "オーク" in selected_material else "walnut"
    else:
        selected_material = st.selectbox("壁紙パターン", ["シックグレー（織物クロス調）", "レンガ調ホワイトクロス"])
        pattern_key = "gray_fabric" if "グレー" in selected_material else "brick"

    if len(st.session_state.points) >= 3:
        if st.button("イメージを合成する"):
            tex_img = generate_texture(pattern_key)
            pts_cnt = len(st.session_state.points)

            # --- 1. 遠近変換（パース処理）またはタイリング ---
            if pts_cnt == 4:
                # 4点指定の場合：遠近感（パース）を計算して変形
                pts1 = np.float32([[0, 0], [400, 0], [400, 400], [0, 400]])
                pts2 = np.float32(st.session_state.points)
                matrix = cv2.getPerspectiveTransform(pts1, pts2)
                warped_texture = cv2.warpPerspective(tex_img, matrix, (w, h))
            else:
                # 多角形の場合：タイリング処理
                th, tw, _ = tex_img.shape
                warped_texture = np.tile(tex_img, (h // th + 1, w // tw + 1, 1))[:h, :w]

            # --- 2. 陰影（光と影）の抽出とブレンド ---
            # 元写真をグレースケール（明暗）化して規格化（0.0〜1.0）
            gray_orig = cv2.cvtColor(img_np, cv2.COLOR_RGB2GRAY).astype(float) / 255.0
            # 陰影を強調するための調整
            shadow_map = np.dstack([gray_orig, gray_orig, gray_orig])

            # テクスチャと元の陰影を「乗算（Multiply）」合成
            blended_texture = (warped_texture.astype(float) * shadow_map * 1.2).clip(0, 255).astype(np.uint8)

            # --- 3. マスク作成と適用 ---
            mask = np.zeros((h, w), dtype=np.uint8)
            pts_array = np.array([st.session_state.points], dtype=np.int32)
            cv2.fillPoly(mask, pts_array, 255)

            img_result = img_np.copy()
            img_result[mask == 255] = blended_texture[mask == 255]

            st.success("陰影と遠近感を反映して合成しました！")
            st.image(img_result, caption="リフォーム後イメージ", use_container_width=True)
    else:
        st.info("画像上の角を3箇所以上タップすると、合成ボタンが有効化されます。")
