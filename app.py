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
# 1. KONFIGURASI TAMPILAN & CSS
# ==========================================
st.set_page_config(page_title="Sistem Rekomendasi Diet", page_icon="🥗", layout="wide")

st.markdown("""
    <style>
    [data-testid="InputInstructions"] { display: none !important; }
    
    .block-container {
        padding-top: 3.5rem !important;
        padding-bottom: 5rem !important;
    }

    [data-testid="stMetric"] {
        background-color: rgba(0, 212, 255, 0.05); 
        border: 1px solid rgba(0, 212, 255, 0.2);
        padding: 15px 5px;
        border-radius: 15px;
        text-align: center;
    }
    
    [data-testid="stMetricLabel"] p {
        font-size: 14px !important;
        font-weight: 700 !important;
        color: #00b4d8 !important; 
    }

    .desc-box {
        background-color: rgba(0, 212, 255, 0.08); 
        border-left: 5px solid #00d4ff; 
        padding: 20px; 
        border-radius: 10px; 
        margin-top: 15px;
        margin-bottom: 30px;
        font-size: 16px;
        line-height: 1.7;
        border: 1px solid rgba(0, 212, 255, 0.1);
    }

    /* CSS HAPUS KOLOM INDEX TANPA HAPUS ISI */
    table th:first-child { display: none !important; }
    table td:first-child { display: none !important; }
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
        <div style="display: flex; align-items: center; justify-content: center; gap: 20px; border-bottom: 2px solid rgba(128,128,128,0.2); padding-bottom: 20px; margin-bottom: 20px;">
            <img src="data:image/png;base64,{img_base64}" style="width: 80px; height: 80px; border-radius: 50%; border: 3px solid rgba(0,212,255,0.2);">
            <h1 style="margin: 0; font-size: 32px; font-weight: 800; letter-spacing: -1px;">Sistem Rekomendasi Paket Menu Harian Sehat</h1>
        </div>
        """, unsafe_allow_html=True)

st.markdown("""
    <div style="text-align: center; font-style: italic; font-size: 16px; margin-top: -10px; margin-bottom: 10px;">
        "Wujudkan gaya hidup sehat dengan panduan pola makan harian bergizi yang disesuaikan khusus untuk kebutuhan tubuhmu!"
    </div>
    """, unsafe_allow_html=True)
st.markdown("---")

# ==========================================
# 3. SIDEBAR & SESSION STATE
# ==========================================
if 'hasil_rekomendasi' not in st.session_state:
    st.session_state.hasil_rekomendasi = None

with st.sidebar:
    st.header("📝 Form Data Diri")
    with st.form("form_pengguna"):
        nama = st.text_input("Nama Lengkap")
        gender = st.selectbox("Jenis Kelamin", ["Laki-laki", "Perempuan"])
        usia = st.number_input("Usia (Tahun)", min_value=1, value=None, placeholder="Input Usia...", step=1)
        bb = st.number_input("Berat Badan (kg)", min_value=10, value=None, placeholder="Input BB...", step=1) 
        tb = st.number_input("Tinggi Badan (cm)", min_value=50, value=None, placeholder="Input TB...", step=1)
        aktivitas = st.selectbox("Tingkat Aktivitas", [
            "Sangat Ringan (Duduk bekerja/belajar, hampir tidak pernah olahraga)",
            "Ringan (Aktivitas sehari-hari + Olahraga ringan 1-3 hari/minggu)",
            "Sedang (Aktivitas cukup padat + Olahraga kardio/gym 3-5 hari/minggu)",
            "Berat (Pekerjaan fisik/Olahraga berat 6-7 hari/minggu)",
            "Sangat Berat (Atlet profesional atau pekerjaan fisik sangat berat setiap hari)"
        ])
        goal = st.selectbox("Tujuan Diet (Goal)", ["Defisit (Menurunkan Berat Badan)", "Maintenance (Menjaga Berat Badan)", "Surplus (Menambah Massa Otot)"])
        alergi = st.selectbox("Riwayat Alergi Makanan", ["Tidak Ada", "Ada Alergi"])
        submitted = st.form_submit_button("Cari Rekomendasi 🚀")

        if submitted:
            if not (nama and bb and tb and usia):
                st.warning("⚠️ Mohon lengkapi data diri Anda!")
            elif alergi != "Tidak Ada":
                st.error("🛑 Sistem tidak memproses pengguna dengan alergi.")
            else:
                if gender == "Laki-laki": bmr = (10 * bb) + (6.25 * tb) - (5 * usia) + 5
                else: bmr = (10 * bb) + (6.25 * tb) - (5 * usia) - 161
                pal_map = {"Sangat Ringan (Duduk bekerja/belajar, hampir tidak pernah olahraga)": 1.2, "Ringan (Aktivitas sehari-hari + Olahraga ringan 1-3 hari/minggu)": 1.375, "Sedang (Aktivitas cukup padat + Olahraga kardio/gym 3-5 hari/minggu)": 1.55, "Berat (Pekerjaan fisik/Olahraga berat 6-7 hari/minggu)": 1.725, "Sangat Berat (Atlet profesional atau pekerjaan fisik sangat berat setiap hari)": 1.9}
                tdee = bmr * pal_map[aktivitas]
                target_kalori = tdee
                if "Defisit" in goal: target_kalori -= 500
                elif "Surplus" in goal: target_kalori += 500
                
                st.session_state.hasil_rekomendasi = {
                    "nama": nama, "target_kalori": target_kalori,
                    "protein": (target_kalori * 0.2) / 4,
                    "karbo": (target_kalori * 0.5) / 4,
                    "lemak": (target_kalori * 0.3) / 9, "goal": goal
                }
                components.html("<script>window.parent.document.querySelector('button[kind=\"headerNoPadding\"]').click();</script>", height=0)

# ==========================================
# 4. DISPLAY HASIL
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
        # TABEL DIPANGGIL NORMAL
        st.table(format_menu_ke_tabel(top['Sarapan'], top['Makan Siang'], top['Makan Malam']))
        
        st.write("### 👨‍🍳 Deskripsi & Cara Penyajian")
        desc = str(top['Detail Makanan']).replace("Sarapan:", "<b>🌅 Sarapan:</b><br>").replace("Siang:", "<br><br><b>☀️ Makan Siang:</b><br>").replace("Malam:", "<br><br><b>🌙 Makan Malam:</b><br>")
        st.markdown(f'<div class="desc-box">{desc}</div>', unsafe_allow_html=True)
        
        st.info(f"💡 Paket ini mengandung **{top['Total Kalori']} Kkal**. Selisih: **{abs(top['Total Kalori'] - res['target_kalori']):.1f} Kkal**.")
else:
    st.info("👈 Silakan lengkapi form di samping untuk melihat rekomendasi.")
