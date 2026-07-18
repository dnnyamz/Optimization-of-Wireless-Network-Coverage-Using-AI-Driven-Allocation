import os
import pandas as pd
from sklearn.model_selection import train_test_split

def preprocess_from_double_extension_excel():
    # Nama fail yang betul mengikut gambar terminal VS Code kau
    excel_file = 'dataset_wifi_ver3.csv.xlsx' 
    
    print("\n====================================================")
    print(f"[PREPROCESS] Membaca fail Excel Projek: {excel_file}")
    print("====================================================")
    
    # Semakan 1: Adakah fail wujud dalam folder?
    if not os.path.exists(excel_file):
        print(f"❌ [RALAT] FAIL '{excel_file}' TIADA DALAM FOLDER VS CODE KAU!")
        print("👉 Sila pastikan ejaan nama fail sama sebiji macam dekat sebelah kiri VS Code.")
        return

    # Semakan 2: Membaca fail Excel menggunakan engine pembaca Excel (pd.read_excel)
    try:
        # Kita baca fail excel tersebut. Jika ada ralat library 'openpyxl', pandas akan bagitahu.
        df = pd.read_excel(excel_file)
        print(f"✅ Berjaya memuatkan data Excel. Jumlah baris dikesan: {df.shape[0]}")
        print(f"📊 Kolum-kolum sedia ada di dalam fail: {list(df.columns)}")
    except Exception as e:
        print(f"❌ [RALAT] Gagal membaca fail Excel: {e}")
        print("👉 Jika terminal minta library openpyxl, taip di terminal: pip install openpyxl")
        return

    # Semakan 3: Pemetaan nama ciri (Feature Alignment)
    # Memastikan ejaan kolum diselaraskan dengan apa yang model main_automation.py mahukan
    column_mapping = {
        'Signal Strength (dBm)': 'RSSI',
        'Interference_Level_Percent': 'Channel_Utilization',
        'BladeRFxA9 Measurement (dBm)': 'Noise_Floor', 
        'Latency (ms)': 'Latency_Before'
    }
    df = df.rename(columns=column_mapping)

    # Semakan 4: Pengurusan kolum sasaran 'Decision' (0 atau 1)
    if 'Decision' not in df.columns:
        if 'Interference_Status' in df.columns:
            df['Decision'] = df['Interference_Status'].apply(lambda x: 1 if str(x).strip() in ['High', 'Moderate'] else 0)
            print("✅ Kolum 'Interference_Status' ditukar kepada logik binari 'Decision' (0 atau 1).")
        else:
            print("⚠️ Kolum status tiada. Menjana 'Decision' automatik berdasarkan kesesakan saluran (>50%)...")
            util_col = 'Channel_Utilization' if 'Channel_Utilization' in df.columns else df.columns[1]
            df['Decision'] = (df[util_col] > 50).astype(int)

    # Semakan 5: Memastikan kolum 'Channel' wujud. 
    # Jika dalam fail excel tu memang dah ada kolum 'Channel', sistem akan guna yang sedia ada.
    if 'Channel' not in df.columns:
        CHANNELS_24 = [1, 6, 11, 13]
        CHANNELS_5  = [36, 40, 44, 48, 149, 153, 157, 161]

        def assign_channel(row):
            sig   = row['RSSI'] if 'RSSI' in row else -70
            inter = row['Channel_Utilization'] if 'Channel_Utilization' in row else 50
            lat   = row['Latency_Before'] if 'Latency_Before' in row else 30
            net   = row['Network Type'] if 'Network Type' in row else '5G'

            channels = CHANNELS_5 if str(net).strip() == '5G' else CHANNELS_24
            score = (sig + 120) / 40
            score -= (inter / 100) * 0.4
            score -= (lat / 300) * 0.2
            score = max(0.0, min(1.0, score))
            return channels[int(score * (len(channels) - 1))]

        df['Channel'] = df.apply(assign_channel, axis=1)
        print("✅ Kolum 'Channel' berjaya dijana.")

    # Simpan fail induk versi CSV tulen untuk dibaca oleh model utama
    df.to_csv('dataset_wifi_ver3.csv', index=False)
    print("💾 Salinan induk 'dataset_wifi_ver3.csv' tulen berjaya dieksport.")

    # Semakan 6: Menapis senarai ciri utama AI sebelum proses pemisahan dilakukan
    features_ai = ['RSSI', 'Channel_Utilization', 'Noise_Floor', 'Latency_Before', 'Channel']
    
    # Pengisian data fallback sekiranya ada kolum yang tidak lengkap
    for f in features_ai:
        if f not in df.columns:
            if f == 'Noise_Floor':
                df['Noise_Floor'] = -90
            elif f == 'Channel_Utilization':
                df['Channel_Utilization'] = 45

    X = df[features_ai]
    y = df['Decision']

    # Semakan 7: Membahagi dataset (80% Latihan, 20% Ujian)
    print("\n⏳ Memisahkan data kepada pecahan Train-Test Split (80/20)...")
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)

    print(f"✅ Pecahan data selesai dijalankan:")
    print(f"     -> Data Latihan (Train Set 80%): {X_train.shape[0]} baris")
    print(f"     -> Data Ujian (Test Set 20%): {X_test.shape[0]} baris")

    # Semakan 8: Menulis fail CSV latihan & ujian yang baharu ke dalam komputer
    train_df = X_train.copy()
    train_df['Decision'] = y_train.values
    
    test_df = X_test.copy()
    test_df['Decision'] = y_test.values

    train_df.to_csv('preprocessed_train.csv', index=False)
    test_df.to_csv('preprocessed_test.csv', index=False)
    
    if os.path.exists('preprocessed_train.csv') and os.path.exists('preprocessed_test.csv'):
        print("🎉 [SUKSES BEZA] Fail 'preprocessed_train.csv' dan 'preprocessed_test.csv' SEKARANG TELAH DIJANAKAN!")
    print("====================================================\n")

if __name__ == "__main__":
    preprocess_from_double_extension_excel()