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
<div style="display: flex; align-items: center; justify-content: center; gap: 25px; padding: 15px 0;">
    <img src="data:image/png;base64,{logo_base64}" width="140">
    <div style="text-align: left;">
        <h2 style="margin: 0; color: white;">NÜFUS ANALİZ PORTALİ</h2>
    </div>
</div>
<hr>
""", unsafe_allow_html=True)

st.markdown("""
<div style='text-align: center; font-size: 16px; color: #ccc; margin-top: -10px; margin-bottom: 10px;'>
Bu uygulama Ordu iline ait nüfus verilerini yıl, ilçe ve mahalle bazında analiz etmenizi sağlar. 
Aşağıdaki grafikler üzerinden verileri karşılaştırabilir ve Excel formatında indirebilirsiniz.
</div>
""", unsafe_allow_html=True)




@st.cache_data  # 1.25+ sürümlerde
def load_data():
    # Parquet çok daha hızlı okunur ve cache’lenir
    return pd.read_parquet("nufus_verisi.parquet")

df = load_data()

year_cols = [col for col in df.columns if col.strip().startswith("20") and "YILI NÜFUSU" in col]
df_long = pd.melt(df, id_vars=["İLÇE", "MAHALLE"], value_vars=year_cols,
                  var_name="YIL", value_name="NÜFUS (KİŞİ SAYISI)")

df_long["YIL"] = df_long["YIL"].str.extract(r"(20\d{2})")
df_long["NÜFUS (KİŞİ SAYISI)"] = pd.to_numeric(df_long["NÜFUS (KİŞİ SAYISI)"], errors="coerce")
years = sorted(df_long["YIL"].dropna().unique().tolist())

col1, col2 = st.columns(2)
start_year = col1.selectbox("Başlangıç Yılı", years, index=0)
end_year = col2.selectbox("Bitiş Yılı", years, index=len(years) - 1)

if start_year > end_year:
    st.warning("Başlangıç yılı, bitiş yılından büyük olamaz!")
else:
    df_filtered = df_long[(df_long["YIL"] >= start_year) & (df_long["YIL"] <= end_year)]

    st.subheader(f"📈 Ordu İli Genel Nüfus Değişimi ({start_year} - {end_year})")
    ordu_geneli = df_filtered.groupby("YIL")["NÜFUS (KİŞİ SAYISI)"].sum().reset_index()
    st.plotly_chart(px.line(ordu_geneli, x="YIL", y="NÜFUS (KİŞİ SAYISI)", markers=True), key="chart_ordu")

    # İlçe Bazlı Çoklu Seçim ve Grafik
    st.subheader("📊 İlçe Bazında Nüfus Değişimi Analizi")
    st.markdown("🔽 Aşağıdan birden fazla ilçe seçerek toplu grafik ve Excel çıktıları alabilirsiniz.")

    if "show_clear_ilce" not in st.session_state:
        st.session_state.show_clear_ilce = True
    if "secili_ilceler" not in st.session_state:
        st.session_state.secili_ilceler = sorted(df_filtered["İLÇE"].unique().tolist())

    tum_ilceler = sorted(df_filtered["İLÇE"].unique())

    ilce_col1, ilce_col2 = st.columns([1, 1])

    if ilce_col1.button("✅ Tümünü Seç", key="btn_ilce_select_all"):
        st.session_state.secili_ilceler = tum_ilceler

    # Eğer en az bir ilçe seçiliyse buton gösterilsin
    if st.session_state.secili_ilceler:
        if ilce_col2.button("❌ Seçimi Kaldır", key="btn_ilce_clear"):
            st.session_state.secili_ilceler = []


    secili_ilceler = st.multiselect(
        label=" ",
        options=tum_ilceler,
        key="secili_ilceler",
        placeholder="Bir veya Birden Fazla İlçe Seçiniz...",
        label_visibility="collapsed"
    )

    st.info(f"🔹 Seçili ilçe sayısı: {len(secili_ilceler)}")

    ilceler_df = df_filtered[df_filtered["İLÇE"].isin(secili_ilceler)]
    if not ilceler_df.empty:
        st.plotly_chart(px.line(ilceler_df.groupby(["YIL", "İLÇE"]).sum().reset_index(),
                                x="YIL", y="NÜFUS (KİŞİ SAYISI)", color="İLÇE", markers=True), key="chart_selected_ilceler")

        output_ilce = BytesIO()
        ilceler_df.to_excel(output_ilce, index=False)
        st.download_button("📥 Excel Dosyası Ham Veri İndir", data=output_ilce.getvalue(),
                           file_name="ilce_bazli_nufus_analizi.xlsx")

        pivot_ilce_df = ilceler_df.pivot_table(index="İLÇE", columns="YIL", values="NÜFUS (KİŞİ SAYISI)", aggfunc="sum")
        pivot_ilce_df.loc["TOPLAM"] = pivot_ilce_df.sum(numeric_only=True)
        pivot_ilce_df.reset_index(inplace=True)

        pivot_ilce_out = BytesIO()
        pivot_ilce_df.to_excel(pivot_ilce_out, index=False)
        st.download_button("📊 Pivot Tablo İndir", data=pivot_ilce_out.getvalue(), file_name="ilce_nufus_pivot.xlsx")

    st.markdown("🔽 Nüfus değişimini görmek isediğiniz ilçeyi seçin")
    secili_ilce = st.selectbox("🔽 İlçe Seçin", df_filtered["İLÇE"].unique().tolist(), label_visibility="collapsed")
    ilce_df = df_filtered[df_filtered["İLÇE"] == secili_ilce]
    ilce_agg = ilce_df.groupby("YIL")["NÜFUS (KİŞİ SAYISI)"].sum().reset_index()

    st.subheader(f"🏙️ {secili_ilce} İlçesi Nüfus Değişimi ({start_year} - {end_year})")
    st.plotly_chart(px.line(ilce_agg, x="YIL", y="NÜFUS (KİŞİ SAYISI)", markers=True), key="chart_ilce")

    st.subheader(f"🏘️ {secili_ilce} İlçesi Mahallelerinin Yıllık Nüfus Grafiği")
    st.plotly_chart(px.line(ilce_df, x="YIL", y="NÜFUS (KİŞİ SAYISI)", color="MAHALLE", markers=True), key="chart_ilce_all_mahalle")
    st.markdown("🔽 Aşağıdan bir veya birden fazla mahalle seçin. Grafikler ve indirme dosyaları seçiminize göre güncellenir.")

    if "show_clear" not in st.session_state:
        st.session_state.show_clear = False
    if "secili_mahalleler" not in st.session_state:
        st.session_state.secili_mahalleler = []

    tum_mahalleler = sorted(ilce_df["MAHALLE"].unique())

    col_left, col_right = st.columns([1, 1])
    if col_left.button("✅ Tümünü Seç", key="btn_mahalle_select_all"):
        st.session_state.secili_mahalleler = tum_mahalleler

    # Eğer en az 1 mahalle seçilmişse, buton görünsün
    if len(st.session_state.secili_mahalleler) > 0:
        if col_right.button("❌ Seçimi Kaldır", key="btn_mahalle_clear"):
            st.session_state.secili_mahalleler = []

    secili_mahalleler = st.multiselect(
        label=" ",
        options=tum_mahalleler,
        default=None,
        key="secili_mahalleler",
        placeholder="Bir veya Birden Fazla Mahalle Seçiniz...",
        label_visibility="collapsed"  # Etiketi görünmez yapar
    )


    st.info(f"🟢 Seçili mahalle sayısı: {len(secili_mahalleler)}")

    mahalleler_df = ilce_df[ilce_df["MAHALLE"].isin(secili_mahalleler)]

    if not mahalleler_df.empty:
        st.subheader("📊 Seçilen Mahallelerin Yıllık Nüfus Grafiği")
        st.plotly_chart(px.line(mahalleler_df, x="YIL", y="NÜFUS (KİŞİ SAYISI)", color="MAHALLE", markers=True), key="chart_selected_mahalle")

        output = BytesIO()
        mahalleler_df.to_excel(output, index=False)
        st.download_button("📥 Excel Dosyası Ham Veri İndir", data=output.getvalue(), file_name=f"{secili_ilce}_mahalle_verileri.xlsx")

        pivot_df = mahalleler_df.pivot_table(index="MAHALLE", columns="YIL", values="NÜFUS (KİŞİ SAYISI)", aggfunc="sum")
        pivot_df.loc["TOPLAM"] = pivot_df.sum(numeric_only=True)
        pivot_df.reset_index(inplace=True)

        pivot_out = BytesIO()
        pivot_df.to_excel(pivot_out, index=False)
        st.download_button("📊 Pivot Tablo İndir", data=pivot_out.getvalue(), file_name=f"{secili_ilce}_mahalle_nufus_pivot.xlsx")

