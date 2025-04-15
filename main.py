
import streamlit as st
import pandas as pd
import plotly.express as px
import base64
from io import BytesIO

st.set_page_config(page_title="Ordu İli Nüfus Analizi", layout="centered")
st.markdown("<meta name='language' content='tr'>", unsafe_allow_html=True)

def get_base64_image(image_path):
    with open(image_path, "rb") as f:
        return base64.b64encode(f.read()).decode()

logo_base64 = get_base64_image("logo.png")

st.markdown(f"""
    <div style="text-align: center; background-color: #0d4c91; padding: 10px 10px; border-radius: 10px;">
        <img src="data:image/png;base64,{logo_base64}" width="70" style="margin-bottom: 5px;">
        <h2 style="color: white; margin-bottom: 0;">Ordu Büyükşehir Belediyesi</h2>
        <h4 style="color: #d0d0d0; margin: 5px 0;">Bilgi İşlem Dairesi Başkanlığı</h4>
        <h5 style="color: #ccc; font-weight: normal; margin: 0;">Coğrafi Bilgi Sistemleri ve Akıllı Şehirler Şube Müdürlüğü</h5>
    </div>
    <hr style="margin-top: 15px; border-color: #444;">
""", unsafe_allow_html=True)

df = pd.read_excel("nufus_verisi.xlsx", sheet_name="Sayfa1")
year_cols = [col for col in df.columns if col.strip().startswith("20") and "YILI NÜFUSU" in col]
df_long = pd.melt(df, id_vars=["İLÇE", "MAHALLE"], value_vars=year_cols,
                  var_name="YIL", value_name="YILLIK_NÜFUS")

df_long["YIL"] = df_long["YIL"].str.extract(r"(20\d{2})")
df_long["YILLIK_NÜFUS"] = pd.to_numeric(df_long["YILLIK_NÜFUS"], errors="coerce")
years = sorted(df_long["YIL"].dropna().unique().tolist())

col1, col2 = st.columns(2)
start_year = col1.selectbox("Başlangıç Yılı", years, index=0)
end_year = col2.selectbox("Bitiş Yılı", years, index=len(years) - 1)

if start_year > end_year:
    st.warning("Başlangıç yılı, bitiş yılından büyük olamaz!")
else:
    df_filtered = df_long[(df_long["YIL"] >= start_year) & (df_long["YIL"] <= end_year)]

    st.subheader(f"📈 Ordu İli Genel Nüfus Değişimi ({start_year} - {end_year})")
    ordu_geneli = df_filtered.groupby("YIL")["YILLIK_NÜFUS"].sum().reset_index()
    st.plotly_chart(px.line(ordu_geneli, x="YIL", y="YILLIK_NÜFUS", markers=True), key="chart_ordu")

    secili_ilce = st.selectbox("🔽 İlçe seçin", df_filtered["İLÇE"].unique().tolist())
    ilce_df = df_filtered[df_filtered["İLÇE"] == secili_ilce]
    ilce_agg = ilce_df.groupby("YIL")["YILLIK_NÜFUS"].sum().reset_index()

    st.subheader(f"🏙️ {secili_ilce} İlçesi Nüfus Değişimi ({start_year} - {end_year})")
    st.plotly_chart(px.line(ilce_agg, x="YIL", y="YILLIK_NÜFUS", markers=True), key="chart_ilce")

    st.subheader(f"🏘️ {secili_ilce} İlçesi Mahallelerinin Yıllık Nüfus Grafiği")
    st.plotly_chart(px.line(ilce_df, x="YIL", y="YILLIK_NÜFUS", color="MAHALLE", markers=True), key="chart_ilce_all_mahalle")

    if "show_clear" not in st.session_state:
        st.session_state.show_clear = False
    if "secili_mahalleler" not in st.session_state:
        st.session_state.secili_mahalleler = []

    tum_mahalleler = sorted(ilce_df["MAHALLE"].unique())

    col_left, col_right = st.columns([1, 1])
    if col_left.button("✅ Tümünü Seç"):
        st.session_state.secili_mahalleler = tum_mahalleler
        st.session_state.show_clear = True
    if st.session_state.show_clear:
        if col_right.button("❌ Hiçbirini Seçme"):
            st.session_state.secili_mahalleler = []
            st.session_state.show_clear = False

    secili_mahalleler = st.multiselect(
        "Mahalle Seç",
        tum_mahalleler,
        default=None,
        key="secili_mahalleler"
    )

    st.info(f"🟢 Seçili mahalle sayısı: {len(secili_mahalleler)}")

    mahalleler_df = ilce_df[ilce_df["MAHALLE"].isin(secili_mahalleler)]

    if not mahalleler_df.empty:
        st.subheader("📊 Seçilen Mahallelerin Yıllık Nüfus Grafiği")
        st.plotly_chart(px.line(mahalleler_df, x="YIL", y="YILLIK_NÜFUS", color="MAHALLE", markers=True), key="chart_selected_mahalle")

        output = BytesIO()
        mahalleler_df.to_excel(output, index=False)
        st.download_button("📥 Seçili Mahalle Verilerini Excel Olarak İndir", data=output.getvalue(), file_name=f"{secili_ilce}_mahalle_verileri.xlsx")

        pivot_df = mahalleler_df.pivot_table(index="MAHALLE", columns="YIL", values="YILLIK_NÜFUS", aggfunc="sum")
        pivot_df.loc["TOPLAM"] = pivot_df.sum(numeric_only=True)
        pivot_df.reset_index(inplace=True)

        pivot_out = BytesIO()
        pivot_df.to_excel(pivot_out, index=False)
        st.download_button("📊 Seçili Mahalleleri Pivot Tablo Olarak İndir", data=pivot_out.getvalue(), file_name=f"{secili_ilce}_mahalle_nufus_pivot.xlsx")
