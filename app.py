import streamlit as st
import cv2
import numpy as np
from PIL import Image
from streamlit_image_coordinates import streamlit_image_coordinates

st.title("🏠 リフォームイメージ作成アプリ")
st.write("部屋の写真をアップロードして、床材や壁紙を合成してみましょう。")

uploaded_file = st.file_uploader("部屋の写真をアップロード", type=["jpg", "jpeg", "png"])

if uploaded_file is not None:
    image = Image.open(uploaded_file)
    img_np = np.array(image)
    h, w, _ = img_np.shape

    st.subheader("1. 床（または壁）の4箇所の角を順番にタップ")
    st.write("【順番】 ①左上 ➔ ②右上 ➔ ③右下 ➔ ④左下 の順に画像上をクリックしてください。")

    # セッション状態（タップした座標の保存用）の初期化
    if "points" not in st.session_state:
        st.session_state.points = []

    # リセットボタン
    if st.button("選択した点をリセット"):
        st.session_state.points = []
        st.rerun()

    # タップ位置を描画したプレビューの作成
    img_display = img_np.copy()
    for i, pt in enumerate(st.session_state.points):
        # タップした場所に赤い丸を描画
        cv2.circle(img_display, (pt[0], pt[1]), 15, (255, 0, 0), -1)
        cv2.putText(img_display, str(i + 1), (pt[0] + 20, pt[1] + 20),
                    cv2.FONT_HERSHEY_SIMPLEX, 1.5, (255, 255, 255), 3)

    # 4点揃ったら枠線を描画
    if len(st.session_state.points) == 4:
        pts_arr = np.array(st.session_state.points, np.int32).reshape((-1, 1, 2))
        cv2.polylines(img_display, [pts_arr], isClosed=True, color=(255, 0, 0), thickness=5)

    # 画像の表示＆タップ座標の取得（クリックイベント）
    # ※表示サイズに合わせて座標変換を行うため Pillow 画像を表示
    img_pil_display = Image.fromarray(img_display)
    coords = streamlit_image_coordinates(img_pil_display, key="pil")

    # 画像がタップされた場合の処理
    if coords is not None and len(st.session_state.points) < 4:
        # タップされた座標を登録（表示上のサイズから元画像サイズへ換算）
        click_x = int(coords["x"])
        click_y = int(coords["y"])
        
        # 重複登録防止チェック
        new_pt = [click_x, click_y]
        if not st.session_state.points or st.session_state.points[-1] != new_pt:
            st.session_state.points.append(new_pt)
            st.rerun()

    st.write(f"現在選択された点の数: {len(st.session_state.points)} / 4")

    # 2. 素材選択と合成
    st.subheader("2. 張り替える素材を選択")
    selected_floor = st.selectbox("床材パターン", ["木目調フローリング（ナチュラル）", "ダークウォールナット", "大理石タイル"])

    if len(st.session_state.points) == 4:
        if st.button("イメージを合成する"):
            # ダミーテクスチャ作成
            texture = np.zeros((400, 400, 3), dtype=np.uint8)
            if "ナチュラル" in selected_floor:
                texture[:] = (120, 180, 220)
            elif "ダーク" in selected_floor:
                texture[:] = (40, 60, 90)
            else:
                texture[:] = (230, 230, 230)

            # ①左上, ②右上, ③右下, ④左下
            pts1 = np.float32([[0, 0], [400, 0], [400, 400], [0, 400]])
            pts2 = np.float32(st.session_state.points)

            matrix = cv2.getPerspectiveTransform(pts1, pts2)
            transformed_texture = cv2.warpPerspective(texture, matrix, (w, h))

            mask = np.zeros((h, w), dtype=np.uint8)
            cv2.fillConvexPoly(mask, np.int32(pts2), 255)

            img_result = img_np.copy()
            img_result[mask == 255] = transformed_texture[mask == 255]

            st.success("合成が完了しました！")
            st.image(img_result, caption="リフォーム後イメージ", use_container_width=True)
    else:
        st.info("画像上の床の角を4箇所タップすると、合成ボタンが有効化されます。")
