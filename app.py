import streamlit as st
import pandas as pd
import numpy as np
import os
import re
import base64
import streamlit.components.v1 as components
from sklearn.preprocessing import MinMaxScaler
from sklearn.metrics.pairwise import cosine_similarity

# ==========================================
# 1. KONFIGURASI TAMPILAN & CSS (ADAPTIVE THEME)
# ==========================================
st.set_page_config(page_title="Sistem Rekomendasi Diet", page_icon="🥗", layout="wide")

st.markdown("""
    <style>
    /* 1. HAPUS PAKSA TULISAN "PRESS ENTER" */
    [data-testid="InputInstructions"] {
        display: none !important;
        visibility: hidden !important;
    }
    
    /* 2. Jarak konten agar tidak nyundul di HP */
    .block-container {
        padding-top: 3.5rem !important;
        padding-bottom: 5rem !important;
    }

    /* 3. Kotak Metric (Warna Tulisan Otomatis Ikut Tema) */
    [data-testid="stMetric"] {
        background-color: rgba(0, 212, 255, 0.1); 
        border: 1px solid rgba(0, 212, 255, 0.3);
        padding: 15px 5px;
        border-radius: 15px;
        text-align: center;
    }
    
    /* Warna Label Biru Cerah agar terlihat di Gelap/Terang */
    [data-testid="stMetricLabel"] p {
        font-size: 14px !important;
        font-weight: 700 !important;
        color: #00b4d8 !important; 
    }

    /* 4. Kotak Deskripsi (ADAPTIF: Tidak pakai warna Hitam/Putih mati) */
    .desc-box {
        background-color: rgba(0, 212, 255, 0.08); 
        border-left: 5px solid #00d4ff; 
        padding: 20px; 
        border-radius: 10px; 
        margin-top: 15px;
        margin-bottom: 30px;
        font-size: 16px;
        line-height: 1.7;
        /* KUNCI: Menghapus warna teks paksaan agar ikut tema Streamlit */
        border: 1px solid rgba(0, 212, 255, 0.1);
    }

    /* Responsif Mobile */
    @media (max-width: 640px) {
        .block-container { padding-top: 2.5rem !important; }
        h1 { font-size: 18px !important; }
    }
    </style>
    """, unsafe_allow_html=True)

# ==========================================
# 2. FUNGSI PEMBANTU
# ==========================================
def get_base64_of_bin_file(bin_file):
    with open(bin_file, 'rb') as f:
        data = f.read()
    return base64.b64encode(data).decode()

def format_menu_ke_tabel(sarapan, siang, malam):
    data_tabel = []
    waktu_makan = [("🌅 Sarapan", sarapan), ("☀️ Makan Siang", siang), ("🌙 Makan Malam", malam)]
    for waktu, menu_str in waktu_makan:
        items = menu_str.split('+') if '+' in menu_str else menu_str.split(',')
        nama_list, porsi_list = [], []
        for item in items:
            match = re.search(r'\((.*?)\)', item)
            porsi_list.append(match.group(1) if match else "-")
            nama_list.append(re.sub(r'\(.*?\)', '', item).strip())
        data_tabel.append({
            "Waktu Makan": waktu,
            "Bahan Makanan": ", ".join(nama_list),
            "Porsi (Gram)": ", ".join(porsi_list)
        })
    return pd.DataFrame(data_tabel)

# HEADER
img_file = 'Macronutrients.png' 
if os.path.exists(img_file):
    img_base64 = get_base64_of_bin_file(img_file)
    st.markdown(f"""
        <div style="display: flex; align-items: center; justify-content: center; gap: 15px; border-bottom: 2px solid rgba(128,128,128,0.2); padding-bottom: 20px; margin-bottom: 20px;">
            <img src="data:image/png;base64,{img_base64}" style="width: 60px; height: 60px; border-radius: 50%;">
            <h1 style="margin: 0; font-size: 24px; font-weight: 800;">Sistem Rekomendasi Paket Menu Harian Sehat</h1>
        </div>
        """, unsafe_allow_html=True)

# ==========================================
# 3. SIDEBAR & SESSION STATE (FIX KOTAK HILANG)
# ==========================================
if 'hasil_rekomendasi' not in st.session_state:
    st.session_state.hasil_rekomendasi = None

with st.sidebar:
    st.header("📝 Form Data Diri")
    with st.form("form_pengguna"):
        nama = st.text_input("Nama Lengkap")
        gender = st.selectbox("Jenis Kelamin", ["Laki-laki", "Perempuan"])
        usia = st.number_input("Usia (Tahun)", min_value=18, max_value=40, step=1)
        bb = st.number_input("Berat Badan (kg)", min_value=30, step=1) 
        tb = st.number_input("Tinggi Badan (cm)", min_value=100, step=1)
        aktivitas = st.selectbox("Tingkat Aktivitas", ["Sangat Ringan", "Ringan", "Sedang", "Berat", "Sangat Berat"])
        goal = st.selectbox("Tujuan Diet (Goal)", ["Defisit (Menurunkan Berat Badan)", "Maintenance (Menjaga Berat Badan)", "Surplus (Menambah Massa Otot)"])
        alergi = st.selectbox("Riwayat Alergi Makanan", ["Tidak Ada", "Ada Alergi"])
        submitted = st.form_submit_button("Cari Rekomendasi 🚀")

        if submitted:
            if alergi != "Tidak Ada":
                st.error("🛑 Sistem tidak memproses pengguna dengan alergi.")
            else:
                if gender == "Laki-laki": bmr = (10 * bb) + (6.25 * tb) - (5 * usia) + 5
                else: bmr = (10 * bb) + (6.25 * tb) - (5 * usia) - 161
                pal_map = {"Sangat Ringan": 1.2, "Ringan": 1.375, "Sedang": 1.55, "Berat": 1.725, "Sangat Berat": 1.9}
                tdee = bmr * pal_map[aktivitas]
                target_kalori = tdee
                if "Defisit" in goal: target_kalori -= 500
                elif "Surplus" in goal: target_kalori += 500
                
                # SIMPAN HASIL KE MEMORI
                st.session_state.hasil_rekomendasi = {
                    "nama": nama, "target_kalori": target_kalori,
                    "protein": (target_kalori * 0.2) / 4,
                    "karbo": (target_kalori * 0.5) / 4,
                    "lemak": (target_kalori * 0.3) / 9, "goal": goal
                }
                
                # Script tutup sidebar
                components.html("<script>window.parent.document.querySelector('button[kind=\"headerNoPadding\"]').click();</script>", height=0)

# ==========================================
# 4. DISPLAY HASIL (PERMANEN DI LAYAR)
# ==========================================
if st.session_state.hasil_rekomendasi:
    res = st.session_state.hasil_rekomendasi
    
    st.subheader(f"📊 Analisis Energi: {res['nama'].upper()}")
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Target Kalori", f"{res['target_kalori']:.1f} Kkal")
    c2.metric("Protein", f"{res['protein']:.1f} g")
    c3.metric("Karbohidrat", f"{res['karbo']:.1f} g")
    c4.metric("Lemak", f"{res['lemak']:.1f} g")
    
    st.markdown("---")

    file_paket = 'datasetpaketmenu.csv'
    if os.path.exists(file_paket):
        df_paket = pd.read_csv(file_paket, sep=';')
        df_paket.columns = df_paket.columns.str.strip()
        scaler = MinMaxScaler()
        fitur = ['Total Kalori', 'Total Protein', 'Total Karbohidrat', 'Total Lemak']
        vektor_db = scaler.fit_transform(df_paket[fitur])
        vektor_user = scaler.transform([[res['target_kalori'], res['protein'], res['karbo'], res['lemak']]])
        df_paket['Score'] = cosine_similarity(vektor_user, vektor_db)[0]
        
        if "Defisit" in res['goal']: df_h = df_paket[df_paket['Paket'].str.startswith('D')]
        elif "Surplus" in res['goal']: df_h = df_paket[df_paket['Paket'].str.startswith('S')]
        else: df_h = df_paket[df_paket['Paket'].str.startswith('M')]
        
        top = df_h.sort_values('Score', ascending=False).iloc[0]
        
        st.success(f"🏆 Rekomendasi: Paket {top['Id Paket']} (Skor Kemiripan: {top['Score']:.4f})")
        st.write("### 🍱 Porsi Bahan Makanan")
        st.table(format_menu_ke_tabel(top['Sarapan'], top['Makan Siang'], top['Makan Malam']).assign(h='').set_index('h'))
        
        st.write("### 👨‍🍳 Deskripsi & Cara Penyajian")
        desc = str(top['Detail Makanan']).replace("Sarapan:", "<b>🌅 Sarapan:</b><br>").replace("Siang:", "<br><br><b>☀️ Makan Siang:</b><br>").replace("Malam:", "<br><br><b>🌙 Makan Malam:</b><br>")
        # MENGGUNAKAN DIV TANPA WARNA TEKS STATIS
        st.markdown(f'<div class="desc-box">{desc}</div>', unsafe_allow_html=True)
        
        st.info(f"💡 Paket ini mengandung **{top['Total Kalori']} Kkal**. Selisih: **{abs(top['Total Kalori'] - res['target_kalori']):.1f} Kkal**.")
else:
    st.info("👈 Silakan lengkapi form di samping untuk melihat rekomendasi.")
