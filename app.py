import streamlit as st
from clean_kmz import process_kmz_bytes

st.set_page_config(
    page_title="KMZ Metadata Cleaner & FDT Cleaner", layout="wide"
)

st.title("🌐 KMZ Metadata & FDT Cleaner (ETL Ready)")
st.write(
    "Unggah file KMZ atau KML Anda untuk membersihkan karakter tak terlihat"
    " (seperti `U+200B`) dan merapikan folder FDT secara otomatis."
)

uploaded_file = st.file_uploader(
    "Pilih file .KMZ atau .KML", type=["kmz", "kml"]
)

if uploaded_file is not None:
  file_bytes = uploaded_file.read()
  filename = uploaded_file.name

  try:
    cleaned_bytes, changes = process_kmz_bytes(file_bytes, filename)

    st.success(
        f"Berhasil memproses file! Ditemukan {len(changes)} elemen yang"
        " diperbaiki."
    )

    # Buat nama file output
    base_name = filename.rsplit(".", 1)[0]
    ext = filename.rsplit(".", 1)[1]
    output_filename = f"{base_name}_Cleaned.{ext}"

    st.download_button(
        label="📥 Unduh File Bersih (Siap ETL)",
        data=cleaned_bytes,
        file_name=output_filename,
        mime=(
            "application/vnd.google-earth.kmz"
            if ext.lower() == "kmz"
            else "application/vnd.google-earth.kml+xml"
        ),
    )

    if changes:
      st.subheader("📋 Log Perubahan Metadata:")
      for idx, c in enumerate(changes, 1):
        st.markdown(
            f"**{idx}. `{c['new']}`** — *[{c['type']}] {c['path']}*<br>`Masalah:"
            f" {c['issues']}`",
            unsafe_allow_html=True,
        )
    else:
      st.info(
          "Tidak ada perubahan yang diperlukan. Metadata file ini sudah bersih"
          " dari spasi siluman."
      )

  except Exception as e:
    st.error(f"Terjadi kesalahan saat memproses file: {e}")
