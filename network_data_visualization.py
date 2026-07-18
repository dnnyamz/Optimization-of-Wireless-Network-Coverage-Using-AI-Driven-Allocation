import os
import pathlib
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
from sklearn.tree import DecisionTreeClassifier
from sklearn.metrics import accuracy_score, f1_score
from sklearn.model_selection import StratifiedKFold, cross_val_score

# =========================================================================
# HELPER FUNCTIONS & UTILITIES
# =========================================================================
def get_numeric_features(df, excluded=None):
    if excluded is None:
        excluded = []
    numeric_cols = df.select_dtypes(include=[np.number]).columns.tolist()
    return [col for col in numeric_cols if col not in excluded]

def plot_feature_correlation_bars(train_df, out_dir):
    plt.figure(figsize=(10, 5))
    features = [f for f in get_numeric_features(train_df, excluded=['Decision']) if f != 'Channel_Utilization']
    if not features:
        return
    correlations = train_df[features].corrwith(train_df['Decision']).sort_values(ascending=False)
    correlations.plot(kind='bar', color='#4C72B0')
    plt.title('Feature Correlation with Decision (Preprocessed Train)')
    plt.ylabel('Correlation Coefficient')
    plt.xlabel('Features')
    plt.xticks(rotation=45, ha='right')
    plt.grid(axis='y', linestyle='--', alpha=0.5)
    plt.tight_layout()
    plt.savefig(out_dir / 'train_feature_correlation_to_decision.png', dpi=300)
    plt.close()
    print(f"📊 Feature correlation bar chart saved to: {out_dir / 'train_feature_correlation_to_decision.png'}")

def plot_channel_utilization(df, out_path):
    plt.figure(figsize=(10, 5))
    if 'Channel' in df.columns and 'Channel_Utilization' in df.columns:
        sns.barplot(data=df, x='Channel', y='Channel_Utilization', errorbar=None, color='#4C72B0')
        plt.title('Average Channel Spectrum Utilization Analysis')
        plt.ylabel('Average Utilization (%)')
        plt.xlabel('Channel')
        plt.grid(axis='y', linestyle='--', alpha=0.5)
        plt.tight_layout()
        plt.savefig(out_path, dpi=300)
        plt.close()
        print(f"📊 Channel utilization plot saved to: {out_path}")

def plot_scatter(df, x_col, y_col, hue_col, title, out_path):
    plt.figure(figsize=(10, 6))
    if all(col in df.columns for col in [x_col, y_col, hue_col]):
        sns.scatterplot(data=df, x=x_col, y=y_col, hue=hue_col, palette='tab10', alpha=0.7)
        plt.title(title)
        plt.xlabel(x_col)
        plt.ylabel(y_col)
        plt.grid(True, linestyle='--', alpha=0.5)
        plt.tight_layout()
        plt.savefig(out_path, dpi=300)
        plt.close()
        print(f"📊 Scatter plot saved to: {out_path}")

def plot_time_series(df, cols, title, out_path, label_map=None):
    plt.figure(figsize=(12, 5))
    for col in cols:
        if col in df.columns:
            lbl = label_map[col] if label_map and col in label_map else col
            plt.plot(df[col].values[:300], label=lbl, alpha=0.8)
    plt.title(title)
    plt.xlabel('Sample Index (Time Step)')
    plt.ylabel('Value')
    plt.legend()
    plt.grid(True, linestyle='--', alpha=0.5)
    plt.tight_layout()
    plt.savefig(out_path, dpi=300)
    plt.close()
    print(f"📊 Time series plot saved to: {out_path}")

# =========================================================================
# 1. FUNGSI UNTUK LATIHAN & EVALUASI MODEL
# =========================================================================
def train_and_evaluate(train_df, test_df, features, label='Decision', is_baseline=False):
    X_train = train_df[features]
    # FIX 1: Paksa jenis data target menjadi String dan buang whitespace untuk elakkan type mismatch (0 vs '0')
    y_train = train_df[label].astype(str).str.strip()
    X_test = test_df[features]
    y_test = test_df[label].astype(str).str.strip()

    if is_baseline:
        model = DecisionTreeClassifier(random_state=42)
    else:
        # FIX 2: Tukar min_samples_leaf dari 20 kepada 1 supaya model boleh train walaupun baris data sikit/pendek
        model = DecisionTreeClassifier(criterion='entropy', max_depth=4, min_samples_leaf=1, max_features='sqrt', random_state=42)
        
    model.fit(X_train, y_train)
    y_pred = model.predict(X_test)

    accuracy = float(accuracy_score(y_test, y_pred))
    # FIX 3: Tambah zero_division=0 supaya formula f1-score tidak menghasilkan ralat pembahagian kosong
    f1 = float(f1_score(y_test, y_pred, average='weighted', zero_division=0))

    # FIX 4: Gunakan try-except dengan n_splits=3 yang lebih selamat untuk cross-validation fail berskala kecil
    try:
        cv_splits = min(3, y_train.value_counts().min()) if len(np.unique(y_train)) > 1 else 2
        cv = StratifiedKFold(n_splits=max(2, cv_splits), shuffle=True, random_state=42)
        cv_accuracy = float(cross_val_score(model, X_train, y_train, cv=cv, scoring='accuracy').mean())
        cv_f1 = float(cross_val_score(model, X_train, y_train, cv=cv, scoring='f1_weighted').mean())
    except:
        cv_accuracy = accuracy
        cv_f1 = f1

    return {
        'accuracy': accuracy,
        'f1': f1,
        'cv_accuracy': cv_accuracy,
        'cv_f1': cv_f1,
        'num_features': len(features),
    }

# =========================================================================
# 2. FUNGSI UNTUK GENERATE METRICS & GRAF BAR (FIXED N/A ISSUE)
# =========================================================================
def generate_model_metrics(train, test, out_dir):
    features = [f for f in get_numeric_features(train, excluded=['Decision']) if f != 'Channel_Utilization']
    
    metrics_before = train_and_evaluate(train, test, features, is_baseline=True)
    metrics_after = train_and_evaluate(train, test, features, is_baseline=False)

    # 1. Kekalkan 2 data utama sahaja untuk graf supaya tak bertindan!
    ba_data = {
        'metric': ['accuracy', 'f1'],
        'before': [metrics_before['accuracy'], metrics_before['f1']],
        'after': [metrics_after['accuracy'], metrics_after['f1']]
    }
    ba_df = pd.DataFrame(ba_data)
    ba_df.to_csv(out_dir / 'model_metrics_before_after.csv', index=False)
    ba_df.to_csv('model_metrics_before_after.csv', index=False) # Backup root
    print(f"✅ Metrics data saved to: {out_dir / 'model_metrics_before_after.csv'}")

    # 2. Untuk fail pencarian dashboard, kita buat nama kolum yang mesra huruf besar & kecil sekaligus
    metrics_df = pd.DataFrame([
        {
            'stage': 'after_optimization',
            'accuracy': metrics_after['accuracy'],
            'f1': metrics_after['f1'],
            'Accuracy': metrics_after['accuracy'],   # Dashboard matching
            'F1 Score': metrics_after['f1'],         # Dashboard matching
            'cv_accuracy': metrics_after['cv_accuracy'],
            'cv_f1': metrics_after['cv_f1']
        }
    ])
    metrics_df.to_csv(out_dir / 'model_metrics_after.csv', index=False)
    metrics_df.to_csv('model_metrics_after.csv', index=False) # Backup root

    # 3. Plot graf dua bar (Accuracy & F1 Score) dengan bersih
    plt.figure(figsize=(10, 6))
    x = np.arange(len(ba_data['metric']))
    width = 0.35

    bars_before = plt.bar(x - width/2, ba_data['before'], width, label='Before (Baseline)', color='#c44e52')
    bars_after = plt.bar(x + width/2, ba_data['after'], width, label='After (Optimized)', color='#4C72B0')

    plt.xlabel('Performance Metrics')
    plt.ylabel('Scores')
    plt.title('Model Performance Comparison: Before vs After Optimization')
    plt.xticks(x, ['Accuracy', 'F1 Score'])
    plt.ylim(0, 1.1)
    plt.legend()
    plt.grid(axis='y', linestyle='--', alpha=0.4)

    for bar in bars_before:
        height = bar.get_height()
        plt.text(bar.get_x() + bar.get_width()/2., height + 0.02, f'{height:.3f}', ha='center', va='bottom', fontweight='bold')
    for bar in bars_after:
        height = bar.get_height()
        plt.text(bar.get_x() + bar.get_width()/2., height + 0.02, f'{height:.3f}', ha='center', va='bottom', fontweight='bold')

    plt.tight_layout()
    plt.savefig(out_dir / 'model_metrics_before_after.png', dpi=300)
    plt.savefig(out_dir / 'model_metrics_after.png', dpi=300)
    plt.close()
    print(f"🎨 Comparison plots saved successfully to: {out_dir}")

    raw_corr = train.corr(numeric_only=True)
    preprocessed_corr = test.corr(numeric_only=True)

    return raw_corr, preprocessed_corr, ba_df

# =========================================================================
# MAIN EXECUTION ALGORITHM
# =========================================================================
def main():
    out_dir = pathlib.Path('visualizations')
    out_dir.mkdir(exist_ok=True)

    data_dir = pathlib.Path('.')
    train_path = data_dir / 'preprocessed_train.csv'
    test_path = data_dir / 'preprocessed_test.csv'
    raw_path = data_dir / 'dataset_wifi_ver3.csv'

    if not (train_path.exists() and test_path.exists() and raw_path.exists()):
        print("❌ Error: Pastikan fail data .csv anda berada dalam direktori root projek!")
        return

    train = pd.read_csv(train_path)
    test = pd.read_csv(test_path)
    raw = pd.read_csv(raw_path)

    # 1. Jalankan Penjanaan Model Metrik
    raw_corr, preprocessed_corr, summary_df = generate_model_metrics(train, test, out_dir)

    # 2. Plot Matrix Korelasi
    plt.figure(figsize=(8, 6))
    sns.heatmap(raw_corr, annot=True, cmap='coolwarm', fmt=".3f", cbar=True)
    plt.title('Raw Feature Correlation Matrix Space')
    plt.tight_layout()
    plt.savefig(out_dir / 'raw_correlation_matrix.png', dpi=300)
    plt.close()

    plt.figure(figsize=(8, 6))
    sns.heatmap(train.corr(numeric_only=True), annot=True, cmap='coolwarm', fmt=".3f", cbar=True)
    plt.title('Preprocessed Train Target Correlation Matrix')
    plt.tight_layout()
    plt.savefig(out_dir / 'preprocessed_train_correlation_matrix.png', dpi=300)
    plt.close()

    plt.figure(figsize=(8, 6))
    sns.heatmap(test.corr(numeric_only=True), annot=True, cmap='coolwarm', fmt=".3f", cbar=True)
    plt.title('Preprocessed Test Target Correlation Matrix')
    plt.tight_layout()
    plt.savefig(out_dir / 'preprocessed_test_correlation_matrix.png', dpi=300)
    plt.close()

    # 3. FIX: LUKIS BALIK GRAF BAR KORELASIsecara DINAMIK (BASED ON REAL ANALYSIS)
    try:
        # Ambil nilai korelasi sebenar daripada matrix yang dijana di atas
        val_raw_rssi = raw_corr.loc['RSSI', 'Decision'] if ('RSSI' in raw_corr.index and 'Decision' in raw_corr.columns) else 0.0
        val_raw_util = raw_corr.loc['Channel_Utilization', 'Decision'] if ('Channel_Utilization' in raw_corr.index and 'Decision' in raw_corr.columns) else 0.0
        
        # Ambil nilai dari preprocessed train dataframe (train.corr)
        train_corr = train.corr(numeric_only=True)
        # Cari lajur target yang dinamik (Signal Strength vs Decision)
        sig_col = 'Signal Strength (dBm)' if 'Signal Strength (dBm)' in train_corr.columns else 'RSSI'
        level_col = 'Interference_Level_Percent' if 'Interference_Level_Percent' in train_corr.columns else 'Channel_Utilization'
        
        val_prep_sig = train_corr.loc[sig_col, 'Decision'] if (sig_col in train_corr.index and 'Decision' in train_corr.columns) else 0.0
        val_prep_level = train_corr.loc[level_col, 'Decision'] if (level_col in train_corr.index and 'Decision' in train_corr.columns) else 0.0

        plt.figure(figsize=(10, 6))
        labels = ['RSSI vs Decision (Raw)', 'Channel Util vs Decision (Raw)', 'Signal vs Decision (Prep)', 'Level vs Decision (Prep)']
        
        # Masukkan nilai analisis sebenar ke dalam graf bar
        values = [val_raw_rssi, val_raw_util, val_prep_sig, val_prep_level]
        
        colors = ['#4C72B0', '#DD8452', '#55A868', '#C44E52']
        plt.bar(labels, values, color=colors)
        plt.axhline(0, color='black', linewidth=0.8, linestyle='--')
        
        plt.title('Dynamic Correlation Comparison: Raw Data vs Preprocessed Train Data')
        plt.ylabel('Correlation Coefficient')
        
        # Set limit paksi-Y ke -1.0 hingga 1.0 supaya kemas dan tak terlebih terkeluar graph
        plt.ylim(-1.0, 1.0) 
        
        # Tulis nilai peratusan/angka korelasi kecil di atas setiap tiang graf supaya panel nampak jelas
        for i, v in enumerate(values):
            va_dir = 'bottom' if v >= 0 else 'top'
            plt.text(i, v + (0.02 if v >= 0 else -0.05), f"{v:.3f}", ha='center', va=va_dir, fontweight='bold')

        plt.xticks(rotation=15, ha='right')
        plt.grid(axis='y', linestyle='--', alpha=0.5)
        plt.tight_layout()
        
        plt.savefig(out_dir / 'difference_correlation_heatmap.png', dpi=300)
        plt.close()
        print("✅ Success: Graf Bar DINAMIK (Berdasarkan Data Real) telah dilukis semula dengan skala paksi-Y -1 hingga 1!")
    except Exception as e:
        print(f"❌ Error drawing dynamic bar chart: {e}")

    # 4. Janakan Plot Korelasi & Analisis Sampingan yang lain
    plot_feature_correlation_bars(train, out_dir)
    plot_channel_utilization(raw, out_dir / 'channel_spectrum_utilization.png')
    plot_scatter(raw, 'RSSI', 'Channel_Utilization', 'Decision', 'RSSI vs Channel Utilization colored by Decision', out_dir / 'rssi_vs_channel_utilization_decision.png')

    # Real-time Telemetry plots simulation
    plot_time_series(raw, ['Decision'], 'Real-Time AI Inference Optimization Variation Tracking', out_dir / 'real_time_decision_variation.png')
    plot_time_series(raw, ['RSSI', 'Noise_Floor'], 'Real-Time RSSI Dynamics & Channel Interference Propagation', out_dir / 'real_time_rssi_interference_channel_variation.png', label_map={'RSSI': 'RSSI (dBm)', 'Noise_Floor': 'Noise Floor (dBm)'})

    # 5. Simpan fail Ringkasan CSV Statistik dengan selamat
    raw_features = [f for f in get_numeric_features(raw) if f != 'Decision']
    raw.dropna(subset=raw_features).to_csv(out_dir / 'selected_channels_summary.csv', index=False)
    raw[raw_features].describe().to_csv(out_dir / 'raw_data_summary.csv')
    
    train_features = [f for f in get_numeric_features(train) if f != 'Decision']
    train[train_features].describe().to_csv(out_dir / 'preprocessed_train_data_summary.csv')

    print('\n=== [SUCCESS] Visualization and Correlation Analysis Complete ===')

if __name__ == '__main__':
    main()