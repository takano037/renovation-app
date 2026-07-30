import streamlit as st
import cv2
import numpy as np
from PIL import Image, ImageOps
from streamlit_image_coordinates import streamlit_image_coordinates

st.title("🏠 リフォームイメージ作成アプリ")
st.write("部屋の写真をアップロードして、プリセット素材や手持ちの画像で合成してみましょう。")

# 1. 部屋の写真アップロード
uploaded_room = st.file_uploader("部屋の写真をアップロード", type=["jpg", "jpeg", "png"])

if uploaded_room is not None:
    room_img = Image.open(uploaded_room)
    room_img = ImageOps.exif_transpose(room_img)
    
    max_size = 1000
    room_img.thumbnail((max_size, max_size))
    
    img_np = np.array(room_img)
    h, w, _ = img_np.shape

    st.subheader("1. 張り替えるエリア（床または壁）の角をタップ（4箇所推奨）")
    st.write("時計回りに角をタップしてください（※4点指定が最も綺麗にパース変形されます）。")

    if "points" not in st.session_state:
        st.session_state.points = []

    if st.button("選択した点をリセット"):
        st.session_state.points = []
        st.rerun()

    # ガイド描画
    img_display = img_np.copy()
    for i, pt in enumerate(st.session_state.points):
        cv2.circle(img_display, (pt[0], pt[1]), 10, (255, 0, 0), -1)
        cv2.putText(img_display, str(i + 1), (pt[0] + 15, pt[1] + 15),
                    cv2.FONT_HERSHEY_SIMPLEX, 1.0, (255, 255, 255), 2)

    if len(st.session_state.points) >= 3:
        pts_arr = np.array(st.session_state.points, np.int32).reshape((-1, 1, 2))
        cv2.polylines(img_display, [pts_arr], isClosed=True, color=(255, 0, 0), thickness=3)

    img_pil_display = Image.fromarray(img_display)

    # スマホはみ出し防止サイズ調整
    display_max_width = 500
    disp_w = w
    disp_h = h
    if w > display_max_width:
        scale = display_max_width / float(w)
        disp_w = display_max_width
        disp_h = int(h * scale)
        img_pil_display = img_pil_display.resize((disp_w, disp_h))
    else:
        scale = 1.0

    coords = streamlit_image_coordinates(img_pil_display, key="pil_coords")

    if coords is not None and len(st.session_state.points) < 6:
        click_x = int(coords["x"] / scale)
        click_y = int(coords["y"] / scale)
        
        new_pt = [click_x, click_y]
        if not st.session_state.points or st.session_state.points[-1] != new_pt:
            st.session_state.points.append(new_pt)
            st.rerun()

    st.write(f"現在選択された点の数: {len(st.session_state.points)} / 6 (最小3点が必要)")

    # 2. 素材の選択方式
    st.subheader("2. 張り替える素材を選択")
    
    tab1, tab2 = st.tabs(["① プリセット素材から選ぶ", "② 画像を直接アップロード"])
    
    tex_img = None

    with tab1:
        target_type = st.radio("張り替える部位", ["床材", "壁紙"], horizontal=True)
        if target_type == "床材":
            selected_material = st.selectbox("床材パターン", ["オークフローリング（ナチュラル木目）", "ダークウォールナット（深み木目）"])
            pattern_key = "oak" if "オーク" in selected_material else "walnut"
        else:
            selected_material = st.selectbox("壁紙パターン", ["シックグレー（織物クロス調）", "レンガ調ホワイトクロス"])
            pattern_key = "gray_fabric" if "グレー" in selected_material else "brick"

        preset_tex = np.zeros((400, 400, 3), dtype=np.uint8)
        if pattern_key == "oak":
            preset_tex[:] = (210, 180, 140)
            for y in range(0, 400, 40):
                cv2.line(preset_tex, (0, y), (400, y), (180, 150, 110), 3)
        elif pattern_key == "walnut":
            preset_tex[:] = (80, 55, 35)
            for y in range(0, 400, 50):
                cv2.line(preset_tex, (0, y), (400, y), (50, 35, 20), 4)
        elif pattern_key == "brick":
            preset_tex[:] = (245, 245, 240)
            for y in range(0, 400, 40):
                cv2.line(preset_tex, (0, y), (400, y), (200, 200, 190), 2)
        else:
            preset_tex[:] = (130, 135, 140)
            for i in range(0, 400, 10):
                cv2.line(preset_tex, (i, 0), (i, 400), (115, 120, 125), 1)

        tex_img = preset_tex

    with tab2:
        uploaded_texture = st.file_uploader("お持ちの素材画像（JPG/PNG）をアップロード", type=["jpg", "jpeg", "png"])
        if uploaded_texture is not None:
            custom_pil = Image.open(uploaded_texture)
            custom_pil = ImageOps.exif_transpose(custom_pil)
            custom_np = np.array(custom_pil)
            if custom_np.shape[2] == 4:
                custom_np = cv2.cvtColor(custom_np, cv2.COLOR_RGBA2RGB)
            tex_img = custom_np
            st.success("カスタム素材画像を使用します！")

    # 3. 合成処理（明るさ保持＋ナチュラル陰影ブレンド）
    if len(st.session_state.points) >= 3:
        if st.button("イメージを合成する"):
            pts_cnt = len(st.session_state.points)

            # 遠近変換またはタイリング
            if pts_cnt == 4:
                pts1 = np.float32([[0, 0], [400, 0], [400, 400], [0, 400]])
                pts2 = np.float32(st.session_state.points)
                tex_resized = cv2.resize(tex_img, (400, 400))
                matrix = cv2.getPerspectiveTransform(pts1, pts2)
                warped_texture = cv2.warpPerspective(tex_resized, matrix, (w, h))
            else:
                th, tw, _ = tex_img.shape
                warped_texture = np.tile(tex_img, (h // th + 1, w // tw + 1, 1))[:h, :w]

            # --- 明るさを潰さないマイルド陰影ブレンド ---
            # 1. 元画像の明暗（グレースケール）を取得
            gray_orig = cv2.cvtColor(img_np, cv2.COLOR_RGB2GRAY).astype(float) / 255.0
            
            # 2. 影の強さを調整（元背景の暗さを抑え、明るさを80%以上保持）
            shadow_map = 0.75 + (gray_orig * 0.25)
            shadow_map = np.dstack([shadow_map, shadow_map, shadow_map])

            # 3. 素材画像本来の発色と明るさを保ちつつ薄く影をのせる
            blended_texture = (warped_texture.astype(float) * shadow_map).clip(0, 255).astype(np.uint8)

            # マスク適用
            mask = np.zeros((h, w), dtype=np.uint8)
            pts_array = np.array([st.session_state.points], dtype=np.int32)
            cv2.fillPoly(mask, pts_array, 255)

            img_result = img_np.copy()
            img_result[mask == 255] = blended_texture[mask == 255]

            st.success("合成が完了しました！")
            st.image(img_result, caption="リフォーム後イメージ", use_container_width=True)
    else:
        st.info("画像上の角を3箇所以上タップすると、合成ボタンが有効化されます。")
