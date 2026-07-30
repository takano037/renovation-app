import streamlit as st
import cv2
import numpy as np
from PIL import Image
import urllib.request
from streamlit_image_coordinates import streamlit_image_coordinates

st.title("🏠 リフォームイメージ作成アプリ")
st.write("部屋の写真をアップロードして、床材や壁紙を合成してみましょう。")

# ネット上のテクスチャ画像（サンプル）を取得する関数
@st.cache_data
def load_texture(url):
    req = urllib.request.urlopen(url)
    arr = np.asarray(bytearray(req.read()), dtype=np.uint8)
    img = cv2.imdecode(arr, cv2.IMREAD_COLOR)
    return cv2.cvtColor(img, cv2.COLOR_BGR2RGB)

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

    # サンプルテクスチャ画像のURLリスト
    if target_type == "床材":
        selected_material = st.selectbox("床材パターン", [
            "オークフローリング（木目）", 
            "ダークウォールナット（木目）"
        ])
        if "オーク" in selected_material:
            texture_url = "https://raw.githubusercontent.com/streamlit/educational-resources/main/images/wood_light.jpg"
        else:
            texture_url = "https://raw.githubusercontent.com/streamlit/educational-resources/main/images/wood_dark.jpg"
    else:
        selected_material = st.selectbox("壁紙パターン", [
            "シックグレー（クロス）", 
            "レンガ調ホワイト"
        ])
        if "グレー" in selected_material:
            texture_url = "https://raw.githubusercontent.com/streamlit/educational-resources/main/images/fabric_gray.jpg"
        else:
            texture_url = "https://raw.githubusercontent.com/streamlit/educational-resources/main/images/brick_white.jpg"

    if len(st.session_state.points) >= 3:
        if st.button("イメージを合成する"):
            # テクスチャ画像の読み込み（150x150px程度にリサイズ）
            try:
                tex_img = load_texture(texture_url)
                tex_img = cv2.resize(tex_img, (150, 150))
                
                # 画像全体にテクスチャをタイリング（敷き詰め）
                th, tw, _ = tex_img.shape
                tiled_texture = np.tile(tex_img, (h // th + 1, w // tw + 1, 1))[:h, :w]

                # 多角形マスクの作成
                mask = np.zeros((h, w), dtype=np.uint8)
                pts_array = np.array([st.session_state.points], dtype=np.int32)
                cv2.fillPoly(mask, pts_array, 255)

                # テクスチャ画像の重ね合わせ（透過処理など）
                img_result = img_np.copy()
                img_result[mask == 255] = tiled_texture[mask == 255]

                st.success("実際のテクスチャ画像で合成が完了しました！")
                st.image(img_result, caption="リフォーム後イメージ", use_container_width=True)
            except Exception as e:
                st.error("画像の読み込みに失敗しました。")
    else:
        st.info("画像上の角を3箇所以上（最大6箇所）タップすると、合成ボタンが有効化されます。")
