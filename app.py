import os
import streamlit as st
import cv2
import numpy as np
from PIL import Image, ImageOps
import io  # 画像ダウンロード用
from streamlit_image_coordinates import streamlit_image_coordinates

# ページ基本設定
st.set_page_config(
    page_title="RoomSimulator - リフォームシミュレーター",
    page_icon="✨",
    layout="centered"
)

# --- ★ スマホ画面のピンチズーム（拡大・縮小）を許可するHTML設定 ---
st.markdown("""
    <head>
        <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=5.0, user-scalable=yes">
    </head>
""", unsafe_allow_html=True)

# --- スタイリッシュデザイン（CSS / Google Fonts）の適用 ---
st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700&family=Noto+Sans+JP:wght@400;500;700&display=swap');

    /* 全体フォント適用 */
    html, body, [class*="css"], div[data-testid="stAppViewContainer"] {
        font-family: 'Inter', 'Noto Sans JP', sans-serif !important;
        letter-spacing: -0.01em;
    }

    /* メインタイトルデザイン */
    .main-title {
        font-family: 'Inter', sans-serif;
        font-size: 2.2rem;
        font-weight: 700;
        color: #1a202c;
        margin-bottom: 0.2rem;
        letter-spacing: -0.03em;
    }

    .sub-title {
        font-size: 0.95rem;
        color: #718096;
        margin-bottom: 1.8rem;
        font-weight: 500;
    }

    /* アコーディオン・見出しデザインの洗練 */
    div[data-testid="stExpander"] {
        border-radius: 8px !important;
        border: 1px solid #e2e8f0 !important;
        box-shadow: 0 1px 3px rgba(0, 0, 0, 0.05) !important;
        background-color: #fafafa !important;
    }

    /* ダウンロードボタンのデザイン */
    div[data-testid="stDownloadButton"] button {
        background-color: #2e5a44 !important;
        background: #2e5a44 !important;
        color: white !important;
        border: none !important;
        font-weight: 600 !important;
        border-radius: 6px !important;
        padding: 0.6rem 1rem !important;
        transition: all 0.2s ease;
    }
    div[data-testid="stDownloadButton"] button:hover {
        background-color: #1f3f2f !important;
        color: white !important;
        box-shadow: 0 4px 12px rgba(46, 90, 68, 0.25) !important;
    }
    
    /* 調整ボタンのスタイル調整 */
    div.stButton > button {
        padding: 0.2rem 0.5rem !important;
        font-size: 0.8rem !important;
    }
    </style>
""", unsafe_allow_html=True)

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

# 単一レイヤー（1箇所の合成）を処理する関数（黒フチ対策済み）
def process_layer(base_img, points, tex_path, rotation_opt, repeat_count, opacity_pct):
    if not os.path.exists(tex_path) or len(points) < 3:
        return base_img
    
    h, w, _ = base_img.shape
    tex_pil = Image.open(tex_path)
    tex_pil = ImageOps.exif_transpose(tex_pil)
    tex_np = np.array(tex_pil)
    if tex_np.shape[2] == 4:
        tex_np = cv2.cvtColor(tex_np, cv2.COLOR_RGBA2RGB)
    
    # 向き回転
    if rotation_opt == "90度回転（横）":
        tex_np = cv2.rotate(tex_np, cv2.ROTATE_90_CLOCKWISE)
    elif rotation_opt == "右斜め（45度）":
        tex_np = rotate_image(tex_np, -45)
    elif rotation_opt == "左斜め（-45度）":
        tex_np = rotate_image(tex_np, 45)

    # リピート処理
    if repeat_count > 1:
        tex_tiled = np.tile(tex_np, (repeat_count, repeat_count, 1))
    else:
        tex_tiled = tex_np

    # 変形（BORDER_WRAP を指定して端に黒枠が混ざるのを完全に防止）
    pts_cnt = len(points)
    if pts_cnt == 4:
        pts1 = np.float32([[0, 0], [400, 0], [400, 400], [0, 400]])
        pts2 = np.float32(points)
        tex_resized = cv2.resize(tex_tiled, (400, 400))
        matrix = cv2.getPerspectiveTransform(pts1, pts2)
        warped_texture = cv2.warpPerspective(tex_resized, matrix, (w, h), borderMode=cv2.BORDER_WRAP)
    else:
        th, tw, _ = tex_tiled.shape
        warped_texture = np.tile(tex_tiled, (h // th + 2, w // tw + 2, 1))[:h, :w]

    # 陰影ブレンド
    gray_orig = cv2.cvtColor(base_img, cv2.COLOR_RGB2GRAY).astype(float) / 255.0
    shadow_map = 0.75 + (gray_orig * 0.25)
    shadow_map = np.dstack([shadow_map, shadow_map, shadow_map])
    blended_texture = (warped_texture.astype(float) * shadow_map).clip(0, 255).astype(np.uint8)

    # マスク作成（アンチエイリアス処理による黒フチを回避するため二値化固定）
    alpha = opacity_pct / 100.0
    mask = np.zeros((h, w), dtype=np.uint8)
    pts_array = np.array([points], dtype=np.int32)
    cv2.fillPoly(mask, pts_array, 255)

    img_result = base_img.copy()
    blended_area = (blended_texture[mask == 255].astype(float) * alpha + 
                    base_img[mask == 255].astype(float) * (1.0 - alpha))
    img_result[mask == 255] = blended_area.clip(0, 255).astype(np.uint8)
    return img_result

# 全レイヤーを順に重ねて最終画像を再計算する関数
def render_all_layers(original_img, layers):
    result = original_img.copy()
    for layer in layers:
        result = process_layer(
            result,
            layer["points"],
            layer["tex_path"],
            layer["rotation_opt"],
            layer["repeat_count"],
            layer["opacity_pct"]
        )
    return result

# --- 素材ギャラリー用ポップアップモーダル関数 ---
@st.dialog("🎨 素材ギャラリーから選択", width="large")
def open_material_gallery(folder_path, state_key_to_set):
    st.write(f"**カテゴリ: {os.path.basename(folder_path)}**")
    files = sorted([f for f in os.listdir(folder_path) if f.lower().endswith(('.png', '.jpg', '.jpeg'))])
    
    if files:
        st.markdown("""
            <style>
            div[data-testid="stHorizontalBlock"] {
                display: flex !important;
                flex-direction: row !important;
                flex-wrap: nowrap !important;
                gap: 0.2rem !important;
            }
            div[data-testid="column"] {
                width: 19% !important;
                flex: 0 0 19% !important;
                min-width: 19% !important;
                padding: 0px !important;
            }
            div[data-testid="column"] img {
                height: 55px !important;
                object-fit: cover !important;
                border-radius: 4px !important;
            }
            div[data-testid="column"] button,
            div[data-testid="column"] button[kind="primary"],
            div[data-testid="column"] button[kind="secondary"] {
                padding: 2px 0px !important;
                font-size: 10px !important;
                background-color: #2e5a44 !important;
                background: #2e5a44 !important;
                color: white !important;
                border: none !important;
                border-radius: 3px !important;
                min-height: 22px !important;
                height: 22px !important;
            }
            div[data-testid="column"] button:hover {
                background-color: #1f3f2f !important;
                color: white !important;
            }
            div[data-testid="column"] button:disabled {
                background-color: #e0e0e0 !important;
                color: #888888 !important;
            }
            </style>
        """, unsafe_allow_html=True)

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
                        is_selected = (file_path == st.session_state.get(state_key_to_set))
                        btn_label = "✅" if is_selected else "選択"
                        if st.button(btn_label, key=f"dialog_btn_{file_path}_{state_key_to_set}", disabled=is_selected, use_container_width=True):
                            st.session_state[state_key_to_set] = file_path
                            st.rerun()
    else:
        st.warning("このフォルダには画像がありません。")

# --- タイトル表示 ---
st.markdown('<div class="main-title">RoomSimulator</div>', unsafe_allow_html=True)
st.markdown('<div class="sub-title">部屋の写真に建材・壁紙・床材をインタラクティブにシミュレーション</div>', unsafe_allow_html=True)

assets_dir = "assets"

# --- セッション状態の初期化 ---
if "layers" not in st.session_state:
    st.session_state.layers = []  # 各エリアのレイヤー保存用
if "current_points" not in st.session_state:
    st.session_state.current_points = []

# 1. 部屋の写真アップロード
uploaded_room = st.file_uploader("部屋の写真をアップロード", type=["jpg", "jpeg", "png"])

if uploaded_room is not None:
    room_img = Image.open(uploaded_room)
    room_img = ImageOps.exif_transpose(room_img)
    max_size = 1000
    room_img.thumbnail((max_size, max_size))
    original_np = np.array(room_img)
    h, w, _ = original_np.shape

    # 画像が切り替わったらクリア
    if st.session_state.get("last_uploaded") != uploaded_room.name:
        st.session_state.layers = []
        st.session_state.current_points = []
        st.session_state.last_uploaded = uploaded_room.name

    st.subheader("1. 張り替えエリアの選択")
    st.caption("角を順にタップしてエリアを指定してください（4箇所推奨、最大8点）。")

    if st.button("選択中のタップ点をリセット"):
        st.session_state.current_points = []
        st.rerun()

    # 現在のレイヤー群を重ね合わせた状態の画像を準備
    current_combined_np = render_all_layers(original_np, st.session_state.layers)

    # タップ用の点描画
    img_display = current_combined_np.copy()
    for i, pt in enumerate(st.session_state.current_points):
        cv2.circle(img_display, (pt[0], pt[1]), 10, (255, 0, 0), -1)
        cv2.putText(img_display, str(i + 1), (pt[0] + 15, pt[1] + 15),
                    cv2.FONT_HERSHEY_SIMPLEX, 1.0, (255, 255, 255), 2)

    if len(st.session_state.current_points) >= 3:
        pts_arr = np.array(st.session_state.current_points, np.int32).reshape((-1, 1, 2))
        cv2.polylines(img_display, [pts_arr], isClosed=True, color=(255, 0, 0), thickness=3)

    img_pil_display = Image.fromarray(img_display)

    # スマホはみ出し防止
    display_max_width = 500
    disp_w, disp_h = w, h
    if w > display_max_width:
        scale = display_max_width / float(w)
        disp_w = display_max_width
        disp_h = int(h * scale)
        img_pil_display = img_pil_display.resize((disp_w, disp_h))
    else:
        scale = 1.0

    coords = streamlit_image_coordinates(img_pil_display, key="pil_coords")

    if coords is not None and len(st.session_state.current_points) < 8:
        click_x = int(coords["x"] / scale)
        click_y = int(coords["y"] / scale)
        new_pt = [click_x, click_y]
        if not st.session_state.current_points or st.session_state.current_points[-1] != new_pt:
            st.session_state.current_points.append(new_pt)
            st.rerun()

    st.write(f"現在選択された点の数: {len(st.session_state.current_points)} / 8")

    # 新規レイヤー追加エリア
    if len(st.session_state.current_points) >= 3:
        st.subheader("2. 新しい張り替えエリアの追加")
        layer_name = st.text_input("エリアの名前（例: 床, 正面壁, 天井）", value=f"エリア {len(st.session_state.layers)+1}")
        
        subfolders = [f for f in os.listdir(assets_dir) if os.path.isdir(os.path.join(assets_dir, f))] if os.path.exists(assets_dir) else []
        selected_folder = st.selectbox("📂 カテゴリを選択", subfolders) if subfolders else None

        if selected_folder:
            target_path = os.path.join(assets_dir, selected_folder)
            files = sorted([f for f in os.listdir(target_path) if f.lower().endswith(('.png', '.jpg', '.jpeg'))])
            if files:
                # デフォルトの選択画像をセット
                if "new_selected_tex_path" not in st.session_state or not os.path.exists(st.session_state.new_selected_tex_path):
                    st.session_state.new_selected_tex_path = os.path.join(target_path, files[0])

                if st.button("🖼️ 素材ギャラリー（一覧）を開く", key="btn_open_gallery_new"):
                    open_material_gallery(target_path, "new_selected_tex_path")

                # 現在選択中の素材プレビュー
                if os.path.exists(st.session_state.new_selected_tex_path):
                    st.caption("現在選択中の素材:")
                    st.image(st.session_state.new_selected_tex_path, width=100)

                col1, col2 = st.columns(2)
                with col1:
                    rot = st.radio("柄の向き", ["標準（縦）", "90度回転（横）", "右斜め（45度）", "左斜め（-45度）"], key="new_rot")
                with col2:
                    rep = st.slider("柄の細かさ", 1, 8, 3, key="new_rep")
                opac = st.slider("不透明度(%)", 10, 100, 100, 5, key="new_opac")

                if st.button("✨ この張り替えエリアを追加保存する", type="primary"):
                    st.session_state.layers.append({
                        "name": layer_name,
                        "points": st.session_state.current_points.copy(),
                        "tex_path": st.session_state.new_selected_tex_path,
                        "rotation_opt": rot,
                        "repeat_count": rep,
                        "opacity_pct": opac
                    })
                    st.session_state.current_points = []
                    st.success(f"「{layer_name}」を追加しました！")
                    st.rerun()

    # --- 登録済みエリアの調整・編集エリア ---
    if st.session_state.layers:
        st.write("---")
        st.subheader("⚙️ 登録済みエリアの再調整・編集")
        st.caption("保存済みのエリアの柄、向き、透明度、および「角の位置」を修正できます。")

        for idx, layer in enumerate(st.session_state.layers):
            expander_key = f"expander_state_{idx}"
            is_expanded = st.session_state.get(expander_key, False)
            
            with st.expander(f"📍 エリア {idx+1}: {layer['name']}", expanded=is_expanded):
                st.session_state[expander_key] = True
                
                c_del, _ = st.columns([1, 3])
                with c_del:
                    if st.button(f"🗑️ このエリアを削除", key=f"del_{idx}"):
                        st.session_state.layers.pop(idx)
                        st.rerun()

                # --- 編集枠専用プレビュー画像の作成 ---
                layer_prev_np = render_all_layers(original_np, st.session_state.layers)
                for i, pt in enumerate(layer["points"]):
                    cv2.circle(layer_prev_np, (pt[0], pt[1]), 10, (0, 0, 255), -1)  # 赤い丸
                    cv2.putText(layer_prev_np, str(i + 1), (pt[0] + 15, pt[1] + 15),
                                cv2.FONT_HERSHEY_SIMPLEX, 1.0, (255, 255, 255), 2)

                if len(layer["points"]) >= 3:
                    pts_arr = np.array(layer["points"], np.int32).reshape((-1, 1, 2))
                    cv2.polylines(layer_prev_np, [pts_arr], isClosed=True, color=(0, 0, 255), thickness=3)

                layer_prev_pil = Image.fromarray(layer_prev_np)

                # スマホ対応リサイズ
                if w > display_max_width:
                    scale_edit = display_max_width / float(w)
                    edit_disp_w = display_max_width
                    edit_disp_h = int(h * scale_edit)
                    layer_prev_pil = layer_prev_pil.resize((edit_disp_w, edit_disp_h))
                else:
                    scale_edit = 1.0

                # --- 位置調整エリア ---
                st.markdown("**🎯 角（ポイント）の位置調整**")
                
                pt_sel_key = f"pt_sel_idx_{idx}"
                if pt_sel_key not in st.session_state:
                    st.session_state[pt_sel_key] = 0
                
                pt_labels = [f"点 {i+1}: (X: {pt[0]}, Y: {pt[1]})" for i, pt in enumerate(layer["points"])]
                selected_pt_idx = st.selectbox("調整したい点を選択", range(len(layer["points"])), index=st.session_state[pt_sel_key], format_func=lambda i: pt_labels[i], key=f"pt_sel_sb_{idx}")
                
                if selected_pt_idx != st.session_state[pt_sel_key]:
                    st.session_state[pt_sel_key] = selected_pt_idx
                    st.rerun()

                st.caption(f"💡 「点 {selected_pt_idx+1}」を移動したい場所を画像上で直接タップするか、下の矢印ボタンで微調整できます。")

                # 画像上での直接タップ検知（ワンタップで大きく移動）
                edit_coords = streamlit_image_coordinates(layer_prev_pil, key=f"edit_coords_{idx}")
                if edit_coords is not None:
                    edit_click_x = int(edit_coords["x"] / scale_edit)
                    edit_click_y = int(edit_coords["y"] / scale_edit)
                    new_edit_pt = [edit_click_x, edit_click_y]
                    
                    if layer["points"][selected_pt_idx] != new_edit_pt:
                        layer["points"][selected_pt_idx] = new_edit_pt
                        st.rerun()

                # 1px移動ボタン（微調整用）
                col_up, col_down, col_left, col_right = st.columns(4)
                step_1 = 1
                with col_up:
                    if st.button("⬆️ 上へ", key=f"up_{idx}"):
                        layer["points"][selected_pt_idx][1] -= step_1
                        st.rerun()
                with col_down:
                    if st.button("⬇️ 下へ", key=f"down_{idx}"):
                        layer["points"][selected_pt_idx][1] += step_1
                        st.rerun()
                with col_left:
                    if st.button("⬅️ 左へ", key=f"left_{idx}"):
                        layer["points"][selected_pt_idx][0] -= step_1
                        st.rerun()
                with col_right:
                    if st.button("➡️ 右へ", key=f"right_{idx}"):
                        layer["points"][selected_pt_idx][0] += step_1
                        st.rerun()
                
                # 3px移動ボタン（微調整用）
                col_sup, col_sdown, col_sleft, col_sright = st.columns(4)
                step_3 = 3
                with col_sup:
                    if st.button("⏫ 上へ(3)", key=f"sup_{idx}"):
                        layer["points"][selected_pt_idx][1] -= step_3
                        st.rerun()
                with col_sdown:
                    if st.button("安静 ⏬ 下へ(3)", key=f"sdown_{idx}"):
                        layer["points"][selected_pt_idx][1] += step_3
                        st.rerun()
                with col_sleft:
                    if st.button("⏪ 左へ(3)", key=f"sleft_{idx}"):
                        layer["points"][selected_pt_idx][0] -= step_3
                        st.rerun()
                with col_sright:
                    if st.button("⏩ 右へ(3)", key=f"sright_{idx}"):
                        layer["points"][selected_pt_idx][0] += step_3
                        st.rerun()

                st.write("---")

                # 素材変更
                if os.path.exists(assets_dir):
                    subfolders = [f for f in os.listdir(assets_dir) if os.path.isdir(os.path.join(assets_dir, f))]
                    cur_folder = os.path.basename(os.path.dirname(layer["tex_path"]))
                    folder_idx = subfolders.index(cur_folder) if cur_folder in subfolders else 0
                    sel_fol = st.selectbox("📂 カテゴリ変更", subfolders, index=folder_idx, key=f"fol_{idx}")

                    t_path = os.path.join(assets_dir, sel_fol)
                    
                    if st.button("🖼️ 素材ギャラリー（一覧）を開く", key=f"btn_gal_{idx}"):
                        st.session_state[f"layer_tex_{idx}"] = layer["tex_path"]
                        open_material_gallery(t_path, f"layer_tex_{idx}")

                    if f"layer_tex_{idx}" in st.session_state and os.path.exists(st.session_state[f"layer_tex_{idx}"]):
                        layer["tex_path"] = st.session_state[f"layer_tex_{idx}"]

                    st.caption("現在選択中の素材:")
                    st.image(layer["tex_path"], width=100)

                # パラメータ調整
                c1, c2 = st.columns(2)
                with c1:
                    rot_opts = ["標準（縦）", "90度回転（横）", "右斜め（45度）", "左斜め（-45度）"]
                    layer["rotation_opt"] = st.radio("柄の向き", rot_opts, index=rot_opts.index(layer["rotation_opt"]), key=f"rot_{idx}")
                with c2:
                    layer["repeat_count"] = st.slider("柄の細かさ", 1, 8, layer["repeat_count"], key=f"rep_{idx}")

                layer["opacity_pct"] = st.slider("不透明度(%)", 10, 100, layer["opacity_pct"], 5, key=f"opac_{idx}")

    # 最終プレビュー表示
    final_output_np = render_all_layers(original_np, st.session_state.layers)
    st.write("---")
    st.subheader("🖼️ 全体コーディネート完成イメージ")
    st.image(final_output_np, caption="リアルタイム調整後の完成イメージ", use_container_width=True)

    # 使用中の素材品番（ファイル名）＆エリア名一覧表示
    if st.session_state.layers:
        st.markdown("**📋 このイメージで使用中の素材品番（品番: カテゴリ）**")
        for layer in st.session_state.layers:
            filename_with_ext = os.path.basename(layer["tex_path"])
            filename_no_ext = os.path.splitext(filename_with_ext)[0]  # 品番
            category_name = os.path.basename(os.path.dirname(layer["tex_path"]))  # カテゴリ
            area_name = layer["name"]  # エリア名
            
            # エリア名を灰色の薄文字で表示
            st.markdown(f"- **{filename_no_ext}** ({category_name}) <span style='color: gray; font-size: 0.9em;'>- {area_name}</span>", unsafe_allow_html=True)

    # イメージ保存（ダウンロード）ボタン
    final_pil = Image.fromarray(final_output_np)
    buf = io.BytesIO()
    final_pil.save(buf, format="JPEG", quality=95)
    byte_im = buf.getvalue()

    st.download_button(
        label="💾 このリフォームイメージを保存する",
        data=byte_im,
        file_name="reform_simulation.jpg",
        mime="image/jpeg",
        use_container_width=True
    )
