import streamlit as st
import pandas as pd
import numpy as np
import os
import re
import base64
import time
import pickle
import streamlit.components.v1 as components
from sklearn.preprocessing import MinMaxScaler
from sklearn.metrics.pairwise import cosine_similarity

# 🔥 TAMBAHAN REVISI: Import library untuk PDF dan Grafik
import plotly.express as px
from fpdf import FPDF

# ==========================================
# 1. KONFIGURASI TAMPILAN & CSS (ADAPTIVE & CLEAN)
# ==========================================
st.set_page_config(page_title="Sistem Rekomendasi Diet", page_icon="🥗", layout="wide")

st.markdown("""
    <style>
    /* HAPUS TULISAN PRESS ENTER & INSTRUKSI INPUT */
    [data-testid="InputInstructions"] { 
        display: none !important; 
        visibility: hidden !important;
    }
    
    .block-container {
        padding-top: 3.5rem !important;
        padding-bottom: 5rem !important;
    }

    /* KOTAK METRIC ADAPTIF */
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

    /* KOTAK DESKRIPSI */
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

    @media (max-width: 640px) {
        h1 { font-size: 20px !important; }
    }

    /* 🔥 TAMBAHAN REVISI: MELEBARKAN SIDEBAR AGAR TEKS TIDAK TERPOTONG */
    [data-testid="stSidebar"] {
        min-width: 480px !important;
        max-width: 480px !important;
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

# 🔥 TAMBAHAN REVISI: Fungsi Khusus untuk Cetak PDF (Kop Surat & TNR 12)
def buat_laporan_pdf(res, top, df_final, score_val):
    pdf = FPDF()
    pdf.add_page()
    
    # 1. Judul Laporan (Font Times New Roman Bold 16)
    pdf.set_font("Times", 'B', 16)
    pdf.cell(0, 10, txt="Laporan Rekomendasi Menu Harian Sehat", ln=True, align='C')
    
    # 2. Garis Pembatas (Kop Surat)
    y_pos = pdf.get_y() + 2 
    pdf.set_line_width(0.8) 
    pdf.line(10, y_pos, 200, y_pos)
    pdf.set_line_width(0.2) 
    pdf.line(10, y_pos + 1.5, 200, y_pos + 1.5)
    
    pdf.ln(10) 
    
    # 3. Identitas Pengguna & Target Gizi
    pdf.set_font("Times", 'B', 12)
    pdf.cell(0, 10, txt="A. Target Kebutuhan Gizi", ln=True)
    pdf.set_font("Times", '', 12) 
    
    # Variabel lebar kolom agar titik dua (:) sejajar rapi
    col1 = 40 
    col2 = 5  
    col3 = 0  
    t_baris = 8 
    
    pdf.cell(col1, t_baris, txt="Nama Pengguna"); pdf.cell(col2, t_baris, txt=":", align='C'); pdf.cell(col3, t_baris, txt=str(res['nama']), ln=True)
    pdf.cell(col1, t_baris, txt="Tujuan Diet"); pdf.cell(col2, t_baris, txt=":", align='C'); pdf.cell(col3, t_baris, txt=str(res['goal']), ln=True)
    pdf.cell(col1, t_baris, txt="Target Kalori"); pdf.cell(col2, t_baris, txt=":", align='C'); pdf.cell(col3, t_baris, txt=f"{res['target_kalori']:.1f} Kkal", ln=True)
    pdf.cell(col1, t_baris, txt="Makronutrien"); pdf.cell(col2, t_baris, txt=":", align='C'); pdf.cell(col3, t_baris, txt=f"Protein {res['protein']:.1f}g | Karbohidrat {res['karbo']:.1f}g | Lemak {res['lemak']:.1f}g", ln=True)
    pdf.ln(5)
    
    # 4. Hasil Rekomendasi
    pdf.set_font("Times", 'B', 12)
    pdf.cell(0, 10, txt="B. Hasil Rekomendasi Sistem", ln=True)
    pdf.set_font("Times", '', 12)
    
    pdf.cell(col1, t_baris, txt="Rekomendasi Utama"); pdf.cell(col2, t_baris, txt=":", align='C'); pdf.cell(col3, t_baris, txt=f"Paket {top['Id Paket']} - {top['Paket']}", ln=True)
    pdf.cell(col1, t_baris, txt="Skor Cosine Sim."); pdf.cell(col2, t_baris, txt=":", align='C'); pdf.cell(col3, t_baris, txt=f"{score_val:.4f}", ln=True)
    pdf.cell(col1, t_baris, txt="Kalori Menu Ini"); pdf.cell(col2, t_baris, txt=":", align='C'); pdf.cell(col3, t_baris, txt=f"{top['Total Kalori']} Kkal", ln=True)
    pdf.ln(5)
    
    # 5. Tabel Menu (TNR 12)
    pdf.set_font("Times", 'B', 12)
    pdf.cell(35, 10, 'Waktu', border=1, align='C')
    pdf.cell(105, 10, 'Bahan Makanan', border=1, align='C')
    pdf.cell(50, 10, 'Porsi', border=1, align='C')
    pdf.ln()
    
    pdf.set_font("Times", '', 12)
    for _, row in df_final.iterrows():
        waktu_bersih = row['Waktu Makan'].replace('🌅 ', '').replace('☀️ ', '').replace('🌙 ', '')
        bahan = str(row['Bahan Makanan'])[:50]
        porsi = str(row['Porsi (Gram)'])[:25]
        
        pdf.cell(35, 10, waktu_bersih, border=1)
        pdf.cell(105, 10, bahan, border=1)
        pdf.cell(50, 10, porsi, border=1)
        pdf.ln()

    # Catatan Bawah
    pdf.ln(10)
    pdf.set_font("Times", 'I', 10)
    pdf.cell(0, 10, txt="*Laporan ini di-generate otomatis oleh Sistem Rekomendasi Diet Berbasis Content-Based Filtering.", ln=True, align='C')
    
    return pdf.output(dest="S").encode("latin-1")

# HEADER: LOGO & JUDUL
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
# 3. SIDEBAR & LOGIKA INPUT (SESSION STATE)
# ==========================================
if 'hasil_rekomendasi' not in st.session_state:
    st.session_state.hasil_rekomendasi = None

if 'pesan_error' not in st.session_state:
    st.session_state.pesan_error = None

with st.sidebar:
    st.header("📝 Form Data Diri")
    with st.form("form_pengguna"):
        nama_input = st.text_input("Nama Lengkap")
        
        # 🔥 TAMBAHAN REVISI: Mengubah Selectbox menjadi Radio Button (GForm style)
        gender = st.radio("Jenis Kelamin", ["Laki-laki", "Perempuan"])
        usia = st.number_input("Usia (Tahun)", min_value=1, value=None, placeholder="Input Usia...", step=1)
        bb = st.number_input("Berat Badan (kg)", min_value=10, value=None, placeholder="Input BB...", step=1) 
        tb = st.number_input("Tinggi Badan (cm)", min_value=50, value=None, placeholder="Input TB...", step=1)
        
        aktivitas = st.radio("Tingkat Aktivitas", [
            "Sangat Ringan (Duduk bekerja/belajar, hampir tidak pernah olahraga)",
            "Ringan (Aktivitas sehari-hari + Olahraga ringan 1-3 hari/minggu)",
            "Sedang (Aktivitas cukup padat + Olahraga kardio/gym 3-5 hari/minggu)",
            "Berat (Pekerjaan fisik/Olahraga berat 6-7 hari/minggu)",
            "Sangat Berat (Atlet profesional atau pekerjaan fisik sangat berat setiap hari)"
        ])
        
        goal = st.radio("Tujuan Diet (Goal)", [
            "Defisit (Menurunkan Berat Badan)", 
            "Maintenance (Menjaga Berat Badan)", 
            "Surplus (Menambah Massa Otot)"
        ])
        
        alergi = st.radio("Riwayat Alergi Makanan", ["Tidak Ada", "Ada Alergi"])
        
        submitted = st.form_submit_button("Cari Rekomendasi 🚀")

        if submitted:
            if not (nama_input and bb and tb and usia):
                st.warning("⚠️ Mohon lengkapi data diri Anda!")
            elif alergi != "Tidak Ada" or usia < 18 or usia > 40:
                st.session_state.pesan_error = "🛑 Maaf, sistem ini hanya dirancang untuk rentang usia dewasa sehat (18-40 tahun) dan tanpa riwayat alergi."
                st.session_state.hasil_rekomendasi = None
            else:
                st.session_state.pesan_error = None
                
                # PERHITUNGAN TDEE
                if gender == "Laki-laki": bmr = (10 * bb) + (6.25 * tb) - (5 * usia) + 5
                else: bmr = (10 * bb) + (6.25 * tb) - (5 * usia) - 161
                
                pal_map = {"Sangat Ringan (Duduk bekerja/belajar, hampir tidak pernah olahraga)": 1.2, "Ringan (Aktivitas sehari-hari + Olahraga ringan 1-3 hari/minggu)": 1.375, "Sedang (Aktivitas cukup padat + Olahraga kardio/gym 3-5 hari/minggu)": 1.55, "Berat (Pekerjaan fisik/Olahraga berat 6-7 hari/minggu)": 1.725, "Sangat Berat (Atlet profesional atau pekerjaan fisik sangat berat setiap hari)": 1.9}
                tdee = bmr * pal_map[aktivitas]
                target_kalori = tdee
                
                if "Defisit" in goal and tdee > 1500: target_kalori -= 500
                elif "Surplus" in goal and tdee < 2500: target_kalori += 500
                
                # SIMPAN KE STATE
                st.session_state.hasil_rekomendasi = {
                    "nama": nama_input, "target_kalori": target_kalori,
                    "protein": (target_kalori * 0.2) / 4,
                    "karbo": (target_kalori * 0.5) / 4,
                    "lemak": (target_kalori * 0.3) / 9, "goal": goal
                }
                
                t_stamp = str(time.time())
                script_js = "<script>\n"
                script_js += "var v = window.parent.document.querySelector('button[kind=\"headerNoPadding\"]');\n"
                script_js += "if (v) { v.click(); }\n"
                script_js += "// Waktu: " + t_stamp + "\n"
                script_js += "</script>"
                components.html(script_js, height=0)

# ==========================================
# 4. DISPLAY HASIL (OUTPUT UTAMA)
# ==========================================
if st.session_state.pesan_error:
    st.error(st.session_state.pesan_error)

elif st.session_state.hasil_rekomendasi:
    res = st.session_state.hasil_rekomendasi
    st.subheader(f"📊 Analisis Energi: {res['nama'].upper()}")
    
    # 4 Kolom Metrik
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Target Kalori", f"{res['target_kalori']:.1f} Kkal")
    c2.metric("Protein", f"{res['protein']:.1f} g")
    c3.metric("Karbohidrat", f"{res['karbo']:.1f} g")
    c4.metric("Lemak", f"{res['lemak']:.1f} g")
    
    # 🔥 TAMBAHAN REVISI: Grafik Pie Chart Plotly di bawah metrik
    st.write("### 🍩 Visualisasi Proporsi Makronutrien")
    data_grafik = pd.DataFrame({
        'Nutrisi': ['Protein', 'Karbohidrat', 'Lemak'],
        'Jumlah (Gram)': [res['protein'], res['karbo'], res['lemak']]
    })
    
    # Membuat efek Donut Chart agar lebih modern
    fig = px.pie(data_grafik, values='Jumlah (Gram)', names='Nutrisi', hole=0.4, 
                 color_discrete_sequence=['#ff9999','#66b3ff','#99ff99'])
    
    fig.update_layout(margin=dict(t=0, b=0, l=0, r=0)) 
    st.plotly_chart(fig, use_container_width=True)
    
    st.markdown("---")

    file_paket = 'datasetpaketmenu.csv'
    if os.path.exists(file_paket):
        df_paket = pd.read_csv(file_paket, sep=';')
        df_paket.columns = df_paket.columns.str.strip()
        
        # PROSES MACHINE LEARNING
        fitur = ['Total Kalori', 'Total Protein', 'Total Karbohidrat', 'Total Lemak']
        
        with open('scaler_gizi.pkl', 'rb') as file:
            scaler = pickle.load(file)
        
        vektor_db = scaler.transform(df_paket[fitur])
        vektor_user = scaler.transform([[res['target_kalori'], res['protein'], res['karbo'], res['lemak']]])
        df_paket['Score'] = cosine_similarity(vektor_user, vektor_db)[0]
        
        # PRE-FILTERING
        if "Defisit" in res['goal']: df_h = df_paket[df_paket['Paket'].str.startswith('D')]
        elif "Surplus" in res['goal']: df_h = df_paket[df_paket['Paket'].str.startswith('S')]
        else: df_h = df_paket[df_paket['Paket'].str.startswith('M')]
        
        # AMBIL REKOMENDASI TERBAIK
        top = df_h.sort_values('Score', ascending=False).iloc[0]
        score_val = top['Score']
        
        if score_val >= 0.80:
            status_rekomendasi = "🔥 High Recommendation (Sangat Direkomendasikan)"
        elif score_val >= 0.60:
            status_rekomendasi = "👍 Moderate Recommendation (Cukup Direkomendasikan)"
        elif score_val >= 0.50:
            status_rekomendasi = "⚠️ Low Recommendation (Kurang Direkomendasikan)"
        else:
            status_rekomendasi = "🛑 Not Recommended (Tidak Direkomendasikan)"

        # TAMPILKAN HASIL PAKET MENU
        st.success(f"🏆 Rekomendasi Utama: Paket {top['Id Paket']} - {top['Paket']}")
        st.info(f"📊 **Tingkat Akurasi Sistem:** {status_rekomendasi}  \n🎯 **Skor Kemiripan (Cosine Similarity):** {score_val:.4f}")
        
        st.write("### 🍱 Porsi Bahan Makanan")
        df_final = format_menu_ke_tabel(top['Sarapan'], top['Makan Siang'], top['Makan Malam'])
        st.dataframe(df_final, use_container_width=True, hide_index=True)
        
        st.write("### 👨‍🍳 Deskripsi & Cara Penyajian")
        desc = str(top['Detail Makanan']).replace("Sarapan:", "<b>🌅 Sarapan:</b><br>").replace("Siang:", "<br><br><b>☀️ Makan Siang:</b><br>").replace("Malam:", "<br><br><b>🌙 Makan Malam:</b><br>")
        st.markdown(f'<div class="desc-box">{desc}</div>', unsafe_allow_html=True)
        
        st.info(f"💡 Paket ini mengandung **{top['Total Kalori']} Kkal**. Selisih: **{abs(top['Total Kalori'] - res['target_kalori']):.1f} Kkal**.")

        # 🔥 TAMBAHAN REVISI: Tombol Cetak PDF di Paling Bawah
        st.markdown("---")
        st.write("### 🖨️ Cetak Laporan Kesehatan")
        st.write("Simpan hasil perhitungan kalori dan rekomendasi menu Anda dalam format PDF.")
        
        # Panggil fungsi pembuat PDF
        pdf_bytes = buat_laporan_pdf(res, top, df_final, score_val)
        
        # Tombol Download Bawaan Streamlit
        nama_file = f"Laporan_Diet_{res['nama'].replace(' ', '_')}.pdf"
        st.download_button(
            label="📄 Unduh Laporan (PDF)",
            data=pdf_bytes,
            file_name=nama_file,
            mime="application/pdf"
        )
else:
    st.info("👈 Silakan lengkapi form di samping untuk melihat rekomendasi.")
