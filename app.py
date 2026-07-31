import os
import streamlit as st
import cv2
import numpy as np
from PIL import Image, ImageOps
from streamlit_image_coordinates import streamlit_image_coordinates

# 画像を任意の角度で回転（黒枠が出ないようにクロップ）する関数
def rotate_image(image, angle):
    (h, w) = image.shape[:2]
    (cX, cY) = (w // 2, h // 2)
    M = cv2.getRotationMatrix2D((cX, cY), angle, 1.0)
    cos = np.abs(M[0, 0])
    sin = np.abs(M[0, 1])
    new_w = int((h * sin) + (w * cos))
    new_h = int((h * cos) + (w * sin))
    M[0, 2] += (new_w / 2) - cX
    M[1, 2] += (new_h / 2) - cY
    rotated = cv2.warpAffine(image, M, (new_w, new_h), borderMode=cv2.BORDER_REFLECT)
    return rotated

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
    
    tab1, tab2 = st.tabs(["① フォルダから選ぶ", "② 画像を直接アップロード"])
    
    tex_img = None

    # --- ポップアップ（モーダル）表示用ダイアログ関数 ---
    @st.dialog("🎨 素材ギャラリーから選択", width="large")
    def open_material_gallery(folder_path):
        st.write(f"**カテゴリ: {os.path.basename(folder_path)}**")
        files = sorted([f for f in os.listdir(folder_path) if f.lower().endswith(('.png', '.jpg', '.jpeg'))])
        
        if files:
            # どんな画面幅でも「絶対に5列」で固定するCSS
            st.markdown("""
                <style>
                /* モーダル枠のパディング最小化 */
                div[data-testid="stDialog"] div[role="dialog"] {
                    padding: 10px !important;
                }
                
                /* st.columns を使わず HTML Grid で5列を強制 */
                .custom-gallery-container {
                    display: grid !important;
                    grid-template-columns: repeat(5, 1fr) !important;
                    gap: 3px !important; /* スマホ向けに間隔をさらに詰める */
                    width: 100% !important;
                    margin-bottom: 10px;
                }
                
                /* 各画像カードのスタイル */
                .gallery-card {
                    display: flex;
                    flex-direction: column;
                    align-items: center;
                    width: 100%;
                }
                .gallery-card img {
                    width: 100% !important;
                    height: 50px !important; /* サムネイルの高さをスマホ向けにコンパクトに */
                    object-fit: cover !important;
                    border-radius: 3px !important;
                }
                
                /* 深緑色ボタンの指定（スマホ向けにさらにコンパクトに） */
                div[data-testid="stDialog"] button,
                div[data-testid="stDialog"] button[kind="primary"],
                div[data-testid="stDialog"] button[kind="secondary"] {
                    padding: 1px 0px !important;
                    font-size: 9px !important;
                    background-color: #2e5a44 !important;
                    background: #2e5a44 !important;
                    color: white !important;
                    border: none !important;
                    border-radius: 3px !important;
                    min-height: 20px !important;
                    height: 20px !important;
                    line-height: 1 !important;
                    margin-top: 1px !important;
                }
                div[data-testid="stDialog"] button:hover {
                    background-color: #1f3f2f !important;
                    color: white !important;
                }
                div[data-testid="stDialog"] button:disabled {
                    background-color: #e0e0e0 !important;
                    background: #e0e0e0 !important;
                    color: #888888 !important;
                }
                </style>
            """, unsafe_allow_html=True)

            # st.columns を使わずに純粋な繰り返し処理で配置
            cols_per_row = 5
            for i in range(0, len(files), cols_per_row):
                cols = st.columns(cols_per_row)
                for j in range(cols_per_row):
                    if i + j < len(files):
                        filename = files[i + j]
                        file_path = os.path.join(folder_path, filename)
                        img_thumb = Image.open(file_path)
                        img_thumb = ImageOps.exif_transpose(img_thumb)
                        
                        with cols[j]:
                            st.image(img_thumb, use_container_width=True)
                            rel_path = os.path.relpath(file_path, "assets")
                            is_selected = (rel_path == st.session_state.get("selected_preset_path"))
                            btn_label = "✅" if is_selected else "選択"
                            if st.button(btn_label, key=f"dialog_btn_{rel_path}", disabled=is_selected, use_container_width=True):
                                st.session_state.selected_preset_path = rel_path
                                st.rerun()
        else:
            st.warning("このフォルダには画像がありません。")

    with tab1:
        assets_dir = "assets"
        
        if os.path.exists(assets_dir):
            subfolders = [f for f in os.listdir(assets_dir) if os.path.isdir(os.path.join(assets_dir, f))]
            root_files = [f for f in os.listdir(assets_dir) if f.lower().endswith(('.png', '.jpg', '.jpeg'))]
            
            folder_options = subfolders.copy()
            if root_files:
                folder_options.append("未分類（assets直下）")

            if folder_options:
                selected_folder_name = st.selectbox("📂 カテゴリ（フォルダ）を選択", folder_options)
                
                if selected_folder_name == "未分類（assets直下）":
                    target_folder_path = assets_dir
                else:
                    target_folder_path = os.path.join(assets_dir, selected_folder_name)

                if "selected_preset_path" not in st.session_state:
                    first_file = sorted([f for f in os.listdir(target_folder_path) if f.lower().endswith(('.png', '.jpg', '.jpeg'))])
                    if first_file:
                        st.session_state.selected_preset_path = os.path.relpath(os.path.join(target_folder_path, first_file[0]), "assets")

                if st.button("🖼️ 素材ギャラリー（一覧）を開く"):
                    open_material_gallery(target_folder_path)

                if "selected_preset_path" in st.session_state:
                    full_selected_path = os.path.join(assets_dir, st.session_state.selected_preset_path)
                    if os.path.exists(full_selected_path):
                        preset_pil = Image.open(full_selected_path)
                        preset_pil = ImageOps.exif_transpose(preset_pil)
                        preset_np = np.array(preset_pil)
                        if preset_np.shape[2] == 4:
                            preset_np = cv2.cvtColor(preset_np, cv2.COLOR_RGBA2RGB)
                        tex_img = preset_np

                        st.write("---")
                        st.caption("現在選択中の素材:")
                        st.image(preset_pil, caption=st.session_state.selected_preset_path, width=120)
            else:
                st.warning("`assets` フォルダ内に画像またはサブフォルダが見つかりません。")
        else:
            st.warning("`assets` フォルダが存在しません。")

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

    # --- 3. 素材の向き・サイズ調整 ---
    st.subheader("3. 模様の向きとサイズ（縮小倍率）調整")
    
    col_dir, col_rep = st.columns([1, 2])
    with col_dir:
        rotation_opt = st.radio("柄の向き", ["標準（縦）", "90度回転（横）", "右斜め（45度）", "左斜め（-45度）"], horizontal=False)
    with col_rep:
        repeat_count = st.slider("柄の細かさ（リピート回数）", min_value=1, max_value=8, value=3)

    # 4. 合成処理
    if len(st.session_state.points) >= 3 and tex_img is not None:
        if st.button("イメージを合成する"):
            pts_cnt = len(st.session_state.points)

            # 向き調整（回転処理）
            if rotation_opt == "90度回転（横）":
                tex_img = cv2.rotate(tex_img, cv2.ROTATE_90_CLOCKWISE)
            elif rotation_opt == "右斜め（45度）":
                tex_img = rotate_image(tex_img, -45)
            elif rotation_opt == "左斜め（-45度）":
                tex_img = rotate_image(tex_img, 45)

            # 素材画像を縮小して敷き詰める（タイリング処理）
            if repeat_count > 1:
                tex_tiled = np.tile(tex_img, (repeat_count, repeat_count, 1))
            else:
                tex_tiled = tex_img

            # 遠近変換またはタイリング
            if pts_cnt == 4:
                pts1 = np.float32([[0, 0], [400, 0], [400, 400], [0, 400]])
                pts2 = np.float32(st.session_state.points)
                tex_resized = cv2.resize(tex_tiled, (400, 400))
                matrix = cv2.getPerspectiveTransform(pts1, pts2)
                warped_texture = cv2.warpPerspective(tex_resized, matrix, (w, h))
            else:
                th, tw, _ = tex_tiled.shape
                warped_texture = np.tile(tex_tiled, (h // th + 1, w // tw + 1, 1))[:h, :w]

            # ナチュラル陰影ブレンド
            gray_orig = cv2.cvtColor(img_np, cv2.COLOR_RGB2GRAY).astype(float) / 255.0
            shadow_map = 0.75 + (gray_orig * 0.25)
            shadow_map = np.dstack([shadow_map, shadow_map, shadow_map])

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
        st.info("画像上の角を3箇所在上タップすると、合成ボタンが有効化されます。")
