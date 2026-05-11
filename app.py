import streamlit as st
import pandas as pd
import numpy as np
import os
import re
from sklearn.preprocessing import MinMaxScaler
from sklearn.metrics.pairwise import cosine_similarity

# ==========================================
# 1. KONFIGURASI TAMPILAN HALAMAN & CSS
# ==========================================
st.set_page_config(page_title="Sistem Rekomendasi Diet", page_icon="🥗", layout="wide")

# JURUS RAHASIA CSS UNTUK MENGHILANGKAN TULISAN "Press Enter..."
st.markdown("""
    <style>
    /* Menyembunyikan teks instruksi bawaan Streamlit di dalam input form */
    div[data-testid="InputInstructions"] {
        display: none !important;
    }
    </style>
    """, unsafe_allow_html=True)

st.title("🥗 Sistem Rekomendasi Paket Menu Diet")
st.write("Dapatkan rekomendasi menu harian yang dipersonalisasi berdasarkan algoritma AI Cosine Similarity.")
st.markdown("---")

# ==========================================
# 2. FUNGSI PEMBANTU (PARSING MENU MENYAMPING)
# ==========================================
def format_menu_menyamping(sarapan, siang, malam):
    """Fungsi untuk memecah string menu menjadi kolom tersendiri per waktu makan"""
    data_tabel = []
    waktu_makan = [("🌅 Sarapan", sarapan), ("☀️ Makan Siang", siang), ("🌙 Makan Malam", malam)]
    
    for waktu, menu_str in waktu_makan:
        items = menu_str.split(',')
        nama_list = []
        berat_list = []
        
        for item in items:
            # Mencari berat di dalam kurung menggunakan Regex
            gram_match = re.search(r'\((.*?)\)', item)
            berat = gram_match.group(1) if gram_match else "-"
            # Menghapus bagian dalam kurung dari nama menu
            nama_menu = re.sub(r'\(.*?\)', '', item).strip()
            
            nama_list.append(nama_menu)
            berat_list.append(berat)
            
        data_tabel.append({
            "Waktu Makan": waktu,
            "Daftar Menu": ", ".join(nama_list),
            "Total Porsi/Gram": ", ".join(berat_list)
        })
    return pd.DataFrame(data_tabel)

# ==========================================
# 3. FORM INPUT DATA PENGGUNA
# ==========================================
with st.sidebar:
    st.header("📝 Form Data Diri")
    with st.form("form_pengguna"):
        nama = st.text_input("Nama Lengkap")
        gender = st.selectbox("Jenis Kelamin", ["Laki-laki", "Perempuan"])
        usia = st.number_input("Usia (Tahun)", min_value=18, max_value=40, value=22, step=1)
        
        # Mengatur value=None agar kotak kosong saat awal dibuka
        bb = st.number_input("Berat Badan (kg)", min_value=30, value=None, placeholder="Ketik BB...", step=1) 
        tb = st.number_input("Tinggi Badan (cm)", min_value=100, value=None, placeholder="Ketik TB...", step=1)
        
        # OPSI DISAMAKAN 100% DENGAN KUESIONER GOOGLE FORM
        aktivitas = st.selectbox("Tingkat Aktivitas", [
            "Sangat Ringan (Duduk bekerja/belajar, hampir tidak pernah olahraga)",
            "Ringan (Aktivitas sehari-hari + Olahraga ringan 1-3 hari/minggu)",
            "Sedang (Aktivitas cukup padat + Olahraga kardio/gym 3-5 hari/minggu)",
            "Berat (Pekerjaan fisik/Olahraga berat 6-7 hari/minggu)",
            "Sangat Berat (Atlet profesional atau pekerjaan fisik sangat berat setiap hari)"
        ])
        
        goal = st.selectbox("Tujuan Diet (Goal)", [
            "Defisit (Menurunkan Berat Badan)", 
            "Maintenance (Menjaga Berat Badan)", 
            "Surplus (Menambah Massa Otot)"
        ])
        
        submitted = st.form_submit_button("Cari Rekomendasi 🚀")

# ==========================================
# 4. PROSES PERHITUNGAN & MODELLING
# ==========================================
if submitted:
    # Validasi jika form belum diisi lengkap
    if not nama or bb is None or tb is None:
        st.warning("⚠️ Mohon lengkapi Nama, Berat Badan, dan Tinggi Badan Anda di form samping!")
    else:
        # A. Perhitungan BMR & TDEE
        if gender == "Laki-laki":
            bmr = (10 * bb) + (6.25 * tb) - (5 * usia) + 5
        else:
            bmr = (10 * bb) + (6.25 * tb) - (5 * usia) - 161
            
        # PEMETAAN NILAI PAL YANG BARU DAN AKURAT
        pal_dict = {
            "Sangat Ringan (Duduk bekerja/belajar, hampir tidak pernah olahraga)": 1.2,
            "Ringan (Aktivitas sehari-hari + Olahraga ringan 1-3 hari/minggu)": 1.375,
            "Sedang (Aktivitas cukup padat + Olahraga kardio/gym 3-5 hari/minggu)": 1.55,
            "Berat (Pekerjaan fisik/Olahraga berat 6-7 hari/minggu)": 1.725,
            "Sangat Berat (Atlet profesional atau pekerjaan fisik sangat berat setiap hari)": 1.9
        }
        
        # Mengambil nilai pengali (PAL) langsung berdasarkan kalimat yang dipilih
        tdee = bmr * pal_dict[aktivitas]
        
        # B. Target Gizi
        target_kalori = tdee
        if "Defisit" in goal: target_kalori -= 500
        elif "Surplus" in goal: target_kalori += 500
        
        t_protein = (target_kalori * 0.20) / 4
        t_karbo = (target_kalori * 0.50) / 4
        t_lemak = (target_kalori * 0.30) / 9

        # --- DISPLAY TARGET KALORI ---
        st.subheader(f"📊 Hasil Analisis Kebutuhan Energi: {nama.upper()}")
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Target Kalori", f"{target_kalori:.0f} Kkal")
        c2.metric("Protein", f"{t_protein:.1f}g")
        c3.metric("Karbohidrat", f"{t_karbo:.1f}g")
        c4.metric("Lemak", f"{t_lemak:.1f}g")
        
        st.markdown("---")

        # C. Modelling Cosine Similarity
        file_paket = 'datasetpaketmenu.csv' 
        if os.path.exists(file_paket):
            df_paket = pd.read_csv(file_paket, sep=';')
            df_paket.columns = df_paket.columns.str.strip()
            
            scaler = MinMaxScaler()
            fitur = ['Total Kalori', 'Total Protein', 'Total Karbohidrat', 'Total Lemak']
            vektor_db = scaler.fit_transform(df_paket[fitur])
            
            target_vec = pd.DataFrame([[target_kalori, t_protein, t_karbo, t_lemak]], columns=fitur)
            vektor_user = scaler.transform(target_vec)
            
            skor = cosine_similarity(vektor_user, vektor_db)[0]
            df_paket['Score'] = skor
            
            # Hybrid Filtering
            if "Defisit" in goal: df_h = df_paket[df_paket['Paket'].str.startswith('D')]
            elif "Surplus" in goal: df_h = df_paket[df_paket['Paket'].str.startswith('S')]
            else: df_h = df_paket[df_paket['Paket'].str.startswith('M')]
            
            top_1 = df_h.sort_values('Score', ascending=False).iloc[0]
            
            # --- DISPLAY HASIL REKOMENDASI ---
            st.success(f"🏆 Rekomendasi Terbaik: Paket {top_1['Id Paket']} (Skor Kemiripan: {top_1['Score']:.4f})")
            
            st.write("### 🍱 Rincian Menu Harian")
            
            # Memanggil fungsi format menyamping
            df_menu_rapi = format_menu_menyamping(top_1['Sarapan'], top_1['Makan Siang'], top_1['Makan Malam'])
            
            # Menampilkan tabel
            st.table(df_menu_rapi.assign(hack='').set_index('hack'))
            
            # Detail Info Bawah
            st.info(f"💡 **Informasi Gizi Paket:** Menu ini mengandung total **{top_1['Total Kalori']} Kkal**. "
                    f"Selisih dengan target Anda adalah **{abs(top_1['Total Kalori'] - target_kalori):.1f} Kkal**.")
            
        else:
            st.error("File 'datasetpaketmenu.csv' tidak ditemukan.")
else:
    # Tampilan awal saat belum submit
    st.info("👈 Silakan isi form data diri Anda pada sidebar di sebelah kiri lalu klik 'Cari Rekomendasi'.")
