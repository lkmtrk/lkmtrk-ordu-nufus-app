import pandas as pd

# 1) Excel’i oku
df = pd.read_excel("nufus_verisi.xlsx", sheet_name="Sayfa1")

# 2) Parquet’e yaz
df.to_parquet("nufus_verisi.parquet", index=False)

print("✅ Parquet dosyası oluşturuldu: nufus_verisi.parquet")
