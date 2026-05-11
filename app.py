import streamlit as st
import pandas as pd
import numpy as np
import os
from sklearn.preprocessing import MinMaxScaler
from sklearn.metrics.pairwise import cosine_similarity

# ==========================================
# 1. KONFIGURASI TAMPILAN HALAMAN
# ==========================================
st.set_page_config(page_title="Sistem Rekomendasi Diet", page_icon="🥗", layout="wide")
st.title("🥗 Sistem Rekomendasi Paket Menu Diet")
st.write("Masukkan data diri Anda untuk mendapatkan rekomendasi menu harian (Top-1) yang paling sesuai dengan kebutuhan gizi Anda menggunakan algoritma AI.")
st.markdown("---")

# ==========================================
# 2. FORM INPUT DATA PENGGUNA
# ==========================================
with st.form("form_pengguna"):
    col1, col2, col3 = st.columns(3)
    
    with col1:
        nama = st.text_input("Nama Lengkap", placeholder="Misal: Jihan Naurah")
        gender = st.selectbox("Jenis Kelamin", ["Laki-laki", "Perempuan"])
        usia = st.number_input("Usia (Tahun)", min_value=18, max_value=40, value=22)
        
    with col2:
        bb = st.number_input("Berat Badan (kg)", min_value=30.0, value=50.0, step=0.1)
        tb = st.number_input("Tinggi Badan (cm)", min_value=100.0, value=160.0, step=0.1)
        
    with col3:
        aktivitas = st.selectbox("Tingkat Aktivitas", [
            "Ringan (Jarang olahraga)", 
            "Sedang (Olahraga 1-3x seminggu)", 
            "Berat (Olahraga 3-5x seminggu)", 
            "Sangat Berat (Olahraga tiap hari)"
        ])
        goal = st.selectbox("Tujuan Diet (Goal)", [
            "Defisit (Menurunkan Berat Badan)", 
            "Maintenance (Menjaga Berat Badan)", 
            "Surplus (Menambah Massa Otot)"
        ])
        
    submitted = st.form_submit_button("Hitung & Cari Rekomendasi Menu 🚀")

# ==========================================
# 3. PROSES PERHITUNGAN & MODELLING
# ==========================================
if submitted:
    if nama.strip() == "":
        st.warning("⚠️ Mohon isi Nama Anda terlebih dahulu!")
    else:
        # A. Hitung BMR (Mifflin-St Jeor)
        if gender == "Laki-laki":
            bmr = (10 * bb) + (6.25 * tb) - (5 * usia) + 5
        else:
            bmr = (10 * bb) + (6.25 * tb) - (5 * usia) - 161
            
        # B. Hitung TDEE berdasarkan Aktivitas
        pal = 1.2
        if "Ringan" in aktivitas: pal = 1.375
        elif "Sedang" in aktivitas: pal = 1.55
        elif "Sangat Berat" in aktivitas: pal = 1.9
        elif "Berat" in aktivitas: pal = 1.725
        
        tdee = bmr * pal
        
        # C. Hitung Target Kalori & Makronutrien berdasarkan Goal
        target_kalori = tdee
        if "Defisit" in goal: target_kalori -= 500
        elif "Surplus" in goal: target_kalori += 500
        
        target_protein = (target_kalori * 0.20) / 4
        target_karbo = (target_kalori * 0.50) / 4
        target_lemak = (target_kalori * 0.30) / 9
        
        # Tampilkan Kotak Info Kebutuhan Gizi
        st.info(f"🎯 **Target Kebutuhan Gizi Harian {nama}:** \n"
                f"**Kalori:** {target_kalori:.1f} Kkal | **Protein:** {target_protein:.1f}g | "
                f"**Karbohidrat:** {target_karbo:.1f}g | **Lemak:** {target_lemak:.1f}g")

        # D. Load Dataset Paket Menu (Langsung dari root folder GitHub)
        file_paket = 'datasetpaketmenu.csv' 
            
        if os.path.exists(file_paket):
            df_paket = pd.read_csv(file_paket, sep=';')
            df_paket.columns = df_paket.columns.str.strip()
            
            # E. Normalisasi Min-Max
            scaler_paket = MinMaxScaler()
            fitur_gizi = ['Total Kalori', 'Total Protein', 'Total Karbohidrat', 'Total Lemak']
            
            vektor_paket = scaler_paket.fit_transform(df_paket[fitur_gizi])
            
            # F. Vektorisasi Target Pengguna
            target_mentah = pd.DataFrame([[target_kalori, target_protein, target_karbo, target_lemak]], columns=fitur_gizi)
            vektor_target_user = scaler_paket.transform(target_mentah)
            
            # G. Hitung Cosine Similarity
            skor_kemiripan = cosine_similarity(vektor_target_user, vektor_paket)[0]
            df_paket['Similarity_Score'] = skor_kemiripan
            
            # H. Hybrid Filtering Kategori (D/S/M)
            if "Defisit" in goal:
                df_hasil = df_paket[df_paket['Paket'].str.startswith('D', na=False)]
            elif "Surplus" in goal:
                df_hasil = df_paket[df_paket['Paket'].str.startswith('S', na=False)]
            else:
                df_hasil = df_paket[df_paket['Paket'].str.startswith('M', na=False)]
                
            # I. Perangkingan (Ambil Top-1)
            df_hasil = df_hasil.sort_values(by='Similarity_Score', ascending=False)
            
            if len(df_hasil) > 0:
                top_1 = df_hasil.iloc[0]
                selisih_error = top_1['Total Kalori'] - target_kalori
                
                # ==========================================
                # 4. TAMPILAN OUTPUT HASIL REKOMENDASI
                # ==========================================
                st.success(f"✅ Berhasil! Ditemukan rekomendasi menu terbaik untuk {nama}.")
                
                # Kartu Informasi Utama
                col_res1, col_res2, col_res3 = st.columns(3)
                col_res1.metric(label="Kode Paket Terpilih", value=f"{top_1['Id Paket']} ({top_1['Paket']})")
                col_res2.metric(label="Total Kalori Menu", value=f"{top_1['Total Kalori']} Kkal", delta=f"{selisih_error:+.1f} Kkal (Selisih)", delta_color="inverse")
                col_res3.metric(label="Skor Kemiripan", value=f"{top_1['Similarity_Score']:.4f}")
                
                st.markdown("### 🍽️ Rincian Menu Harian")
                
                # Membuat Tabel yang Cantik untuk Sarapan, Siang, Malam
                df_tabel = pd.DataFrame({
                    "Waktu Makan": ["🌅 Sarapan", "☀️ Makan Siang", "🌙 Makan Malam"],
                    "Daftar Menu Makanan": [top_1['Sarapan'], top_1['Makan Siang'], top_1['Makan Malam']]
                })
                # Menyembunyikan Index bawaan Pandas agar tabel rapi
                st.table(df_tabel.assign(hack='').set_index('hack'))
                
                # Info Makronutrien Tambahan
                st.caption(f"**Total Makronutrien Menu Aktual:** Protein: {top_1['Total Protein']}g | Karbohidrat: {top_1['Total Karbohidrat']}g | Lemak: {top_1['Total Lemak']}g")
                
            else:
                st.error("Maaf, tidak ada menu yang tersedia untuk kategori tersebut.")
        else:
            st.error("❌ Dataset Menu tidak ditemukan! Pastikan file 'datasetpaketmenu.csv' sudah di-upload ke GitHub.")
