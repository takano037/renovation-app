import streamlit as st
from PIL import Image

st.title("🏠 リフォームイメージ作成アプリ")
st.write("部屋の写真をアップロードして、イメージ画像を確認できます。")

# 1. 画像アップロード機能
uploaded_file = st.file_uploader("部屋の写真をアップロード", type=["jpg", "jpeg", "png"])

# 2. 素材（床材・壁紙）の選択
st.subheader("差し替え素材の選択")
selected_floor = st.selectbox("床材を選択", ["オークフローリング", "ウォールナット", "大理石調タイル"])
selected_wall = st.selectbox("壁紙を選択", ["シンプルホワイト", "アクセントグレー", "木目調クロス"])

# 3. 実行と結果表示
if uploaded_file is not None:
    image = Image.open(uploaded_file)
    st.image(image, caption="リフォーム前", use_container_width=True)
    
    if st.button("リフォームイメージを生成"):
        st.info("画像を処理中...")
        st.success("（※ここに合成された画像が表示されるよう処理を追加していきます）")
