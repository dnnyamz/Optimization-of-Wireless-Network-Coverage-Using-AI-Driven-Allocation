import http.server
import socketserver
import webbrowser
import os
import urllib.parse
import pandas as pd
import paramiko
import threading
import time
import html as html_parser

PORT = 8080
VIS_DIR = 'visualizations'
ROUTER_IP = os.environ.get('ROUTER_IP', '192.168.1.1')
ROUTER_USER = os.environ.get('ROUTER_USER', 'root')
ROUTER_PASS = os.environ.get('ROUTER_PASS', 'admin123')
RADIO_24 = os.environ.get('ROUTER_RADIO_24', 'radio1')
RADIO_5 = os.environ.get('ROUTER_RADIO_5', 'radio0')

CAPTION_MAP = {
    "optimization_log": "AI Optimization History Telemetry Log",
    "selected_channels_summary": "Intelligent Channel Allocation Strategy Summary",
    "channel_spectrum_utilization": "Channel Spectrum Utilization Analysis",
    "difference_correlation_heatmap": "Difference Correlation Space Heatmap",
    "difference_correlation_summary": "Difference Correlation Summary Matrix",
    "model_metrics_before_after": "Comparative Performance Analysis (Before vs After)",
    "preprocessed_test_correlation_matrix": "Preprocessed Test Target Correlation Matrix",
    "preprocessed_train_correlation_matrix": "Preprocessed Train Target Correlation Matrix",
    "raw_correlation_matrix": "Raw Feature Correlation Space Matrix",
    "real_time_decision_variation": "Real-Time AI Inference Optimization Variation Tracking",
    "real_time_rssi_interference_channel_variation": "Real-Time RSSI Dynamics & Channel Interference Propagation",
    "rssi_vs_channel_utilization_decision": "RSSI Space Map vs Channel Spectrum Utilization Dynamics"
}

router_status = None
telemetry_lock = threading.Lock()

def sedut_realtime_log_dari_router():
    global router_status
    local_log_path = os.path.join(VIS_DIR, 'optimization_log.csv')
    
    # 1. CIPTA FOLDER LOKAL JIKA BELUM WUJUD
    os.makedirs(VIS_DIR, exist_ok=True)
    
    # 2. SAMBUNG SSH DAN AMBIL DATA (VERSI KALIS EOF)
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    try:
        # Sambung SSH ke router
        ssh.connect(ROUTER_IP, username=ROUTER_USER, password=ROUTER_PASS, timeout=3)
        
        # Guna arahan 'cat' untuk baca fail dari router tanpa melalui SFTP negotiation
        cmd_read_log = "cat /root/optimization_log.csv"
        _, stdout_log, _ = ssh.exec_command(cmd_read_log)
        log_content = stdout_log.read().decode('utf-8')
        
        # Simpan kandungan fail yang dibaca terus ke dalam laptop
        if log_content.strip():
            with open(local_log_path, "w", encoding="utf-8") as f:
                f.write(log_content)
            print("[AUTO-SYNC] Berjaya memuat turun log mutakhir via Terminal Command!")
        
        # Ambil konfigurasi saluran wifi fizikal semasa dari router
        cmd_24 = f"uci get wireless.{RADIO_24}.channel"
        cmd_5 = f"uci get wireless.{RADIO_5}.channel"
        
        _, stdout_24, _ = ssh.exec_command(cmd_24)
        _, stdout_5, _ = ssh.exec_command(cmd_5)
        
        ch24 = stdout_24.read().decode().strip() or 'N/A'
        ch5 = stdout_5.read().decode().strip() or 'N/A'
        
        with telemetry_lock:
            router_status = {
                'channel_24': f"Ch {ch24}",
                'channel_5': f"Ch {ch5}",
                'disabled_24': '0',
                'disabled_5': '0'
            }
    except Exception as e:
        print(f"[AUTO-SYNC WARNING] Gagal menarik data dari router (Menggunakan log lokal): {e}")
        # Fallback: Jika router offline, baca data lama dari fail sedia ada di laptop
        if os.path.exists(local_log_path):
            try:
                df = pd.read_csv(local_log_path)
                if not df.empty:
                    last_row = df.iloc[-1]
                    ch_vals = str(last_row.get('Channel', '1_36')).split('_')
                    with telemetry_lock:
                        router_status = {
                            'channel_24': 'Ch ' + ch_vals[0],
                            'channel_5': 'Ch ' + ch_vals[-1],
                            'disabled_24': '0',
                            'disabled_5': '0'
                        }
            except Exception:
                pass
    finally:
        ssh.close()

def build_html():
    global router_status
    all_images = []
    if os.path.exists(VIS_DIR):
        all_images = sorted([f for f in os.listdir(VIS_DIR) if f.lower().endswith(('.png', '.jpg', '.jpeg', '.gif'))])

    images = []
    has_before_after = any('before_after' in img.lower() for img in all_images)
    for img in all_images:
        if has_before_after and ('model_performance' in img.lower() and 'before_after' not in img.lower()):
            continue
        images.append(img)

    log_file = os.path.join(VIS_DIR, 'optimization_log.csv')
    last_sync = time.strftime('%Y-%m-%d %H:%M:%S')
    
    health_score, rssi, latency, utilization, interference = "98%", "-55 dBm", "12 ms", "34%", "Low"
    prev_24, prev_5, best_24, best_5 = "Ch 11", "Ch 36", "Ch 6", "Ch 149"
    timeline_html = ""
    
    if os.path.exists(log_file):
        try:
            log_df = pd.read_csv(log_file)
            if not log_df.empty:
                latest = log_df.iloc[-1]
                health_score = f"{latest.get('Signal Quality (%)', latest.get('Score', 98))}%"
                rssi = f"{latest.get('RSSI', -55)} dBm"
                latency = f"{latest.get('Latency_Before', latest.get('Latency', 12))} ms"
                utilization = f"{latest.get('Channel_Utilization', latest.get('Utilization', 34))}%"
                interference = str(latest.get('Interference_Status', latest.get('Interference', 'Low')))

                ch_current = str(latest.get('Channel', '1_36')).split('_')
                ch_best = str(latest.get('Best_Channel', latest.get('Channel_After', latest.get('Channel', '1_36')))).split('_')
                
                prev_24 = f"Ch {ch_current[0]}"
                prev_5 = f"Ch {ch_current[-1]}" if len(ch_current) > 1 else "Ch 36"
                best_24 = f"Ch {ch_best[0]}"
                best_5 = f"Ch {ch_best[-1]}" if len(ch_best) > 1 else "Ch 36"
                
                events = log_df.tail(4).iloc[::-1]
                for _, row in events.iterrows():
                    ts_val = str(row.get('Timestamp', '')).split(' ')[-1][:5]
                    dec = str(row.get('Decision', 'No Change'))
                    icon = "fa-check-circle" if "No Change" in dec else "fa-exchange-alt"
                    color = "var(--success)" if "No Change" in dec else "var(--brand)"
                    
                    timeline_html += f'''
                    <div class="timeline-item">
                        <div class="timeline-dot" style="background: {color};"></div>
                        <div class="timeline-time">{ts_val}</div>
                        <div class="timeline-text"><i class="fas {icon}" style="color: {color}; margin-right: 6px;"></i> {html_parser.escape(dec)}</div>
                    </div>'''
        except Exception:
            pass

    if not timeline_html:
        timeline_html = '<div class="timeline-item"><div class="timeline-dot" style="background: var(--success);"></div><div class="timeline-time">--:--</div><div class="timeline-text">Awaiting log synchronization...</div></div>'

    ch24 = router_status.get('channel_24', 'N/A') if router_status else 'N/A'
    ch5 = router_status.get('channel_5', 'N/A') if router_status else 'N/A'
    status_r = 'Online' if router_status and router_status.get('channel_24') != 'Error' else 'Offline'

    vis_validation = ""
    vis_spectrum = ""
    vis_research = ""

    for img in images:
        title = CAPTION_MAP.get(os.path.splitext(img)[0], img.replace('_', ' ').title())
        card = f'''
        <div class="vis-card">
          <div class="vis-header">{title}</div>
          <div class="vis-body" onclick="openModal('/{VIS_DIR}/{urllib.parse.quote(img)}', '{title}')">
            <img src="/{VIS_DIR}/{urllib.parse.quote(img)}" class="vis-img" alt="{title}">
          </div>
        </div>'''
        
        if 'before_after' in img.lower() or 'performance' in img.lower() or 'decision_variation' in img.lower():
            vis_validation += card
        elif 'spectrum' in img.lower() or 'rssi' in img.lower() or 'utilization' in img.lower():
            vis_spectrum += card
        elif 'matrix' in img.lower() or 'correlation' in img.lower() or 'heatmap' in img.lower():
            vis_research += card

    html_template = r'''<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>DZNETS | Network Optimization</title>
  <link href="https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700&family=JetBrains+Mono:wght@400;500&display=swap" rel="stylesheet">
  <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css">
  <style>
    :root {
      --bg: #F8F9FB; --surface: #FFFFFF; --text-main: #1E293B; --text-muted: #64748B;
      --border: #E2E8F0; --brand: #0284C7; --brand-light: #E0F2FE; --accent: #0F172A;
      --success: #10B981; --success-light: #D1FAE5; --danger: #EF4444; --warning: #F59E0B;
      --shadow-sm: 0 1px 2px 0 rgb(0 0 0 / 0.05); --shadow-md: 0 4px 6px -1px rgb(0 0 0 / 0.1);
      --radius: 12px;
    }
    * { box-sizing: border-box; margin: 0; padding: 0; }
    body { font-family: 'Plus Jakarta Sans', sans-serif; background: var(--bg); color: var(--text-main); font-size: 14px; line-height: 1.5; }
    
    .app-container { display: flex; height: 100vh; overflow: hidden; }
    .sidebar { width: 260px; background: var(--surface); border-right: 1px solid var(--border); display: flex; flex-direction: column; flex-shrink: 0; z-index: 10; }
    .sidebar-header { height: 70px; display: flex; align-items: center; padding: 0 24px; border-bottom: 1px solid var(--border); }
    .sidebar-logo { width: 32px; height: 32px; background: var(--brand); border-radius: 8px; display: flex; align-items: center; justify-content: center; color: white; font-size: 14px; margin-right: 12px; }
    .sidebar-brand { font-weight: 700; font-size: 18px; color: var(--accent); letter-spacing: 0.5px; }
    .nav-menu { padding: 24px 16px; flex: 1; }
    .nav-item { display: flex; align-items: center; padding: 12px 16px; margin-bottom: 8px; border-radius: 8px; color: var(--text-muted); font-weight: 600; cursor: pointer; transition: all 0.2s; }
    .nav-item i { width: 24px; font-size: 16px; margin-right: 10px; }
    .nav-item:hover { background: var(--bg); color: var(--brand); }
    .nav-item.active { background: var(--brand-light); color: var(--brand); }
    
    .main-wrapper { flex: 1; display: flex; flex-direction: column; overflow: hidden; }
    .header { height: 70px; background: var(--surface); border-bottom: 1px solid var(--border); display: flex; align-items: center; justify-content: space-between; padding: 0 32px; z-index: 20; flex-shrink: 0; }
    .header-title { font-size: 16px; font-weight: 600; color: var(--text-main); }
    .header-actions { display: flex; align-items: center; gap: 16px; }
    .status-badge { display: flex; align-items: center; gap: 8px; padding: 6px 12px; background: var(--success-light); color: #065F46; border-radius: 20px; font-size: 12px; font-weight: 600; }
    .status-dot { width: 8px; height: 8px; background: var(--success); border-radius: 50%; animation: pulse 2s infinite; }
    @keyframes pulse { 0% { opacity: 1; box-shadow: 0 0 0 0 rgba(16, 185, 129, 0.4); } 70% { opacity: 0.5; box-shadow: 0 0 0 6px rgba(16, 185, 129, 0); } 100% { opacity: 1; box-shadow: 0 0 0 0 rgba(16, 185, 129, 0); } }
    .btn-sync { background: var(--surface); border: 1px solid var(--border); padding: 8px 16px; border-radius: 8px; font-weight: 600; color: var(--text-main); cursor: pointer; display: flex; align-items: center; gap: 8px; transition: all 0.2s; }
    .btn-sync:hover { border-color: var(--brand); color: var(--brand); }
    
    .content-area { flex: 1; overflow-y: auto; padding: 32px; scroll-behavior: smooth; }
    .page-section { display: none; animation: fadeIn 0.3s ease; }
    .page-section.active { display: block; }
    @keyframes fadeIn { from { opacity: 0; transform: translateY(10px); } to { opacity: 1; transform: translateY(0); } }
    
    .section-title { font-size: 20px; font-weight: 700; color: var(--accent); margin-bottom: 24px; display: flex; align-items: center; gap: 10px; }
    .card { background: var(--surface); border: 1px solid var(--border); border-radius: var(--radius); padding: 24px; box-shadow: var(--shadow-sm); }
    .card-header { font-size: 13px; font-weight: 700; color: var(--text-muted); text-transform: uppercase; letter-spacing: 0.5px; margin-bottom: 16px; }
    
    .kpi-grid { display: grid; grid-template-columns: repeat(5, 1fr); gap: 20px; margin-bottom: 24px; }
    .kpi-card { background: var(--surface); border: 1px solid var(--border); border-radius: var(--radius); padding: 20px; box-shadow: var(--shadow-sm); border-left: 4px solid var(--brand); }
    .kpi-label { font-size: 12px; font-weight: 600; color: var(--text-muted); margin-bottom: 8px; }
    .kpi-value { font-size: 24px; font-weight: 700; color: var(--accent); font-family: 'JetBrains Mono', monospace; }
    
    .dashboard-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 24px; margin-bottom: 24px; }
    .data-row { display: flex; justify-content: space-between; padding: 12px 0; border-bottom: 1px solid var(--border); }
    .data-row:last-child { border-bottom: none; }
    .data-label { color: var(--text-muted); font-weight: 500; display: flex; align-items: center; gap: 8px; }
    .data-val { font-weight: 600; color: var(--text-main); font-family: 'JetBrains Mono', monospace; }
    
    .alloc-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 16px; text-align: center; }
    .alloc-box { padding: 16px; border-radius: 8px; border: 1px solid var(--border); background: var(--bg); }
    .alloc-box.target { background: var(--success-light); border-color: var(--success); color: #065F46; }
    .alloc-title { font-size: 11px; font-weight: 700; text-transform: uppercase; margin-bottom: 8px; color: inherit; opacity: 0.8; }
    .alloc-ch { font-size: 22px; font-weight: 700; font-family: 'JetBrains Mono', monospace; }
    
    .decision-grid { display: grid; grid-template-columns: repeat(4, 1fr); gap: 16px; }
    .decision-card { padding: 16px; border-radius: 8px; background: #F8FAFC; border: 1px solid #E2E8F0; text-align: center; }
    .decision-val { font-size: 20px; font-weight: 700; color: var(--success); margin: 8px 0; font-family: 'JetBrains Mono', monospace; }
    
    .timeline { position: relative; padding-left: 20px; }
    .timeline::before { content: ''; position: absolute; left: 0; top: 0; bottom: 0; width: 2px; background: var(--border); }
    .timeline-item { position: relative; padding-bottom: 20px; padding-left: 20px; }
    .timeline-item:last-child { padding-bottom: 0; }
    .timeline-dot { position: absolute; left: -25px; top: 4px; width: 12px; height: 12px; border-radius: 50%; border: 2px solid var(--surface); }
    .timeline-time { font-size: 12px; font-weight: 700; color: var(--text-muted); margin-bottom: 4px; }
    .timeline-text { font-weight: 500; color: var(--text-main); font-family: 'JetBrains Mono', monospace; }
    
    .vis-grid { display: grid; grid-template-columns: repeat(2, 1fr); gap: 24px; margin-bottom: 24px; }
    .vis-card { background: var(--surface); border: 1px solid var(--border); border-radius: var(--radius); overflow: hidden; }
    .vis-header { padding: 16px 20px; border-bottom: 1px solid var(--border); background: var(--bg); font-weight: 600; font-size: 13px; color: var(--accent); }
    .vis-body { padding: 16px; display: flex; justify-content: center; align-items: center; background: #fff; cursor: zoom-in; height: 320px; }
    .vis-img { max-width: 100%; max-height: 100%; object-fit: contain; transition: transform 0.2s; }
    .vis-body:hover .vis-img { transform: scale(1.02); }
    
    .modal { display: none; position: fixed; top: 0; left: 0; width: 100vw; height: 100vh; background: rgba(15, 23, 42, 0.95); z-index: 9999; backdrop-filter: blur(5px); justify-content: center; align-items: center; flex-direction: column; }
    .modal.active { display: flex; }
    .modal-controls { position: absolute; top: 24px; right: 24px; display: flex; gap: 12px; z-index: 10000; }
    .modal-btn { background: rgba(255,255,255,0.1); border: 1px solid rgba(255,255,255,0.2); color: white; width: 40px; height: 40px; border-radius: 8px; cursor: pointer; display: grid; place-items: center; font-size: 16px; transition: all 0.2s; }
    .modal-btn:hover { background: rgba(255,255,255,0.2); }
    .modal-img-wrapper { width: 90vw; height: 80vh; display: flex; justify-content: center; align-items: center; overflow: hidden; cursor: grab; }
    .modal-img-wrapper:active { cursor: grabbing; }
    .modal-img { max-width: 100%; max-height: 100%; object-fit: contain; transform-origin: center; transition: transform 0.1s ease-out; }
    .modal-caption { color: white; font-size: 16px; font-weight: 500; margin-top: 20px; padding: 8px 24px; background: rgba(0,0,0,0.5); border-radius: 20px; }

    .telemetry-container { background: var(--accent); border-radius: var(--radius); overflow: hidden; box-shadow: var(--shadow-md); margin-bottom: 24px; }
    .telemetry-header { padding: 16px 24px; background: rgba(255,255,255,0.05); border-bottom: 1px solid rgba(255,255,255,0.1); display: flex; justify-content: space-between; align-items: center; color: white; }
    .telemetry-title { font-size: 16px; font-weight: 700; display: flex; align-items: center; gap: 10px; }
    .telemetry-pulse { width: 10px; height: 10px; background: #10B981; border-radius: 50%; box-shadow: 0 0 10px #10B981; animation: livePulse 1.5s infinite; }
    @keyframes livePulse { 0% { opacity: 1; } 50% { opacity: 0.3; } 100% { opacity: 1; } }
    .telemetry-body { padding: 0; max-height: 400px; overflow-y: auto; }
    .telemetry-table { width: 100%; border-collapse: collapse; text-align: left; color: #E2E8F0; font-family: 'JetBrains Mono', monospace; font-size: 12px; }
    .telemetry-table th { background: rgba(0,0,0,0.3); padding: 12px 24px; position: sticky; top: 0; font-weight: 600; text-transform: uppercase; font-size: 11px; letter-spacing: 0.5px; color: #94A3B8; border-bottom: 1px solid rgba(255,255,255,0.1); }
    .telemetry-table td { padding: 12px 24px; border-bottom: 1px solid rgba(255,255,255,0.05); }
    .telemetry-table tr:hover td { background: rgba(255,255,255,0.02); }

    .footer { background: #FFFFFF; border-top: 1px solid var(--border); padding: 32px 40px; margin-top: auto; display: flex; flex-direction: column; gap: 16px; }
    .footer-content { display: flex; justify-content: space-between; align-items: flex-start; flex-wrap: wrap; gap: 24px; }
    .footer-left { color: var(--text-muted); font-size: 13px; line-height: 1.6; }
    .footer-left strong { color: var(--text-main); font-size: 14px; }
    .footer-right { display: flex; gap: 24px; }
    .sys-stat { display: flex; align-items: center; gap: 8px; font-size: 12px; font-weight: 600; color: var(--text-main); }
    .sys-dot { width: 8px; height: 8px; background: var(--success); border-radius: 50%; }
  </style>
</head>
<body>

<div class="app-container">
  <aside class="sidebar">
    <div class="sidebar-header">
      <div class="sidebar-logo"><i class="fas fa-wifi"></i></div>
      <div class="sidebar-brand">DZNETS</div>
    </div>
    <nav class="nav-menu">
      <div class="nav-item active" onclick="switchPage('page-command', this)"><i class="fas fa-desktop"></i> Command Center</div>
      <div class="nav-item" onclick="switchPage('page-validation', this)"><i class="fas fa-chart-line"></i> Performance Validation</div>
      <div class="nav-item" onclick="switchPage('page-spectrum', this)"><i class="fas fa-broadcast-tower"></i> Spectrum Analysis</div>
      <div class="nav-item" onclick="switchPage('page-research', this)"><i class="fas fa-microchip"></i> Research Analytics</div>
    </nav>
  </aside>

  <div class="main-wrapper">
    <header class="header">
      <div class="header-title">Optimization of Wireless Network Coverage Using AI-Driven Allocation</div>
      <div class="header-actions">
        <div class="status-badge" title="Router Connected & AI Engine Active"><div class="status-dot"></div> System Active</div>
        <div style="font-size: 12px; color: var(--text-muted); font-weight: 500;">Last Sync: <span id="sync-time">__LAST_SYNC__</span></div>
        <button class="btn-sync" onclick="manualSync()"><i class="fas fa-sync-alt"></i> Sync Telemetry</button>
      </div>
    </header>

    <div class="content-area">
      <div id="page-command" class="page-section active">
        <h2 class="section-title"><i class="fas fa-desktop"></i> Network Command Center</h2>
        
        <div class="kpi-grid">
          <div class="kpi-card"><div class="kpi-label">Network Health Score</div><div class="kpi-value" id="kpi-health">__HEALTH_SCORE__</div></div>
          <div class="kpi-card" style="border-left-color: var(--success);"><div class="kpi-label">Current RSSI</div><div class="kpi-value" id="kpi-rssi">__RSSI__</div></div>
          <div class="kpi-card" style="border-left-color: var(--warning);"><div class="kpi-label">Current Latency</div><div class="kpi-value" id="kpi-latency">__LATENCY__</div></div>
          <div class="kpi-card" style="border-left-color: #8B5CF6;"><div class="kpi-label">Channel Utilization</div><div class="kpi-value" id="kpi-utilization">__UTILIZATION__</div></div>
          <div class="kpi-card" style="border-left-color: var(--danger);"><div class="kpi-label">Interference Level</div><div class="kpi-value" id="kpi-interference">__INTERFERENCE__</div></div>
        </div>

        <div class="dashboard-grid">
          <div class="card">
            <div class="card-header"><i class="fas fa-server" style="margin-right: 8px;"></i> Current Router Configuration</div>
            <div class="data-row"><div class="data-label"><i class="fas fa-wifi"></i> 2.4 GHz Active Channel</div><div class="data-val" id="router-ch24">__CH24__</div></div>
            <div class="data-row"><div class="data-label"><i class="fas fa-signal"></i> 5 GHz Active Channel</div><div class="data-val" id="router-ch5">__CH5__</div></div>
            <div class="data-row"><div class="data-label"><i class="fas fa-power-off"></i> Router Status</div><div class="data-val" style="color: var(--success);"><i class="fas fa-circle" style="font-size: 8px;"></i> __STATUS_R__</div></div>
            <div class="data-row"><div class="data-label"><i class="fas fa-brain"></i> AI Engine Status</div><div class="data-val" style="color: var(--success);"><i class="fas fa-circle" style="font-size: 8px;"></i> Active</div></div>
          </div>

          <div class="card">
            <div class="card-header"><i class="fas fa-robot" style="margin-right: 8px;"></i> AI Recommendation Panel</div>
            <div style="display: flex; gap: 24px; align-items: center;">
              <div style="flex: 1;">
                <div class="alloc-title">Previous Allocation</div>
                <div class="alloc-grid" style="margin-bottom: 0;">
                  <div class="alloc-box"><div style="font-size: 11px; color: var(--text-muted);">2.4 GHz</div><div class="alloc-ch" id="prev-24">__PREV_24__</div></div>
                  <div class="alloc-box"><div style="font-size: 11px; color: var(--text-muted);">5 GHz</div><div class="alloc-ch" id="prev-5">__PREV_5__</div></div>
                </div>
              </div>
              <div style="color: var(--border);"><i class="fas fa-chevron-right fa-2x"></i></div>
              <div style="flex: 1;">
                <div class="alloc-title" style="color: var(--success);">Recommended Target</div>
                <div class="alloc-grid" style="margin-bottom: 0;">
                  <div class="alloc-box target"><div style="font-size: 11px; font-weight: 600;">2.4 GHz</div><div class="alloc-ch" id="best-24">__BEST_24__</div></div>
                  <div class="alloc-box target"><div style="font-size: 11px; font-weight: 600;">5 GHz</div><div class="alloc-ch" id="best-5">__BEST_5__</div></div>
                </div>
              </div>
            </div>
          </div>
        </div>

        <div class="card">
          <div class="card-header"><i class="fas fa-history" style="margin-right: 8px;"></i> AI Optimization Timeline</div>
          <div class="timeline" id="timeline-container">__TIMELINE_HTML__</div>
        </div>
      </div>

      <div id="page-validation" class="page-section"><h2 class="section-title"><i class="fas fa-chart-line"></i> Performance Validation</h2><div class="vis-grid">__VIS_VALIDATION__</div></div>
      <div id="page-spectrum" class="page-section"><h2 class="section-title"><i class="fas fa-broadcast-tower"></i> Channel Spectrum Analysis</h2><div class="vis-grid">__VIS_SPECTRUM__</div></div>
      <div id="page-research" class="page-section">
        <h2 class="section-title"><i class="fas fa-microchip"></i> Research Analytics & Live Telemetry</h2>
        <div class="telemetry-container">
          <div class="telemetry-header">
            <div class="telemetry-title"><div class="telemetry-pulse"></div>LIVE TELEMETRY CENTER</div>
            <div style="font-size: 12px; font-weight: 500; color: #94A3B8;"><i class="fas fa-sync fa-spin"></i> Auto-refreshing 5min</div>
          </div>
          <div class="telemetry-body">
            <table class="telemetry-table">
              <thead><tr><th>Timestamp</th><th>RSSI</th><th>Latency</th><th>Utilization</th><th>Decision</th></tr></thead>
              <tbody id="telemetry-body"><tr><td colspan="5" style="text-align:center; padding:24px;">Initializing Telemetry Pipeline...</td></tr></tbody>
            </table>
          </div>
        </div>
        <div class="vis-grid">__VIS_RESEARCH__</div>
      </div>

      <footer class="footer">
        <div class="footer-content">
          <div class="footer-left">
            <strong>Optimization of Wireless Network Coverage Using AI-Driven Allocation</strong><br>
            Developed by Daniel<br>Bachelor of Computer Science (Network Computing)<br>UiTM Kampus Jasin<br>Version 1.0 &copy; 2026.
          </div>
        </div>
      </footer>
    </div>
  </div>
</div>

<div id="imgModal" class="modal">
  <div class="modal-controls">
    <button class="modal-btn" onclick="zoomImg(0.2)"><i class="fas fa-search-plus"></i></button>
    <button class="modal-btn" onclick="zoomImg(-0.2)"><i class="fas fa-search-minus"></i></button>
    <button class="modal-btn" onclick="resetZoom()"><i class="fas fa-expand"></i></button>
    <button class="modal-btn" onclick="closeModal()" style="background: var(--danger); border-color: var(--danger);"><i class="fas fa-times"></i></button>
  </div>
  <div class="modal-img-wrapper" id="imgWrapper"><img id="modalImg" class="modal-img" src=""></div>
  <div class="modal-caption" id="modalCaption"></div>
</div>

<script>
  function switchPage(pageId, element) {
    var sections = document.querySelectorAll('.page-section');
    for (var i = 0; i < sections.length; i++) {
      sections[i].classList.remove('active');
    }
    var items = document.querySelectorAll('.nav-item');
    for (var j = 0; j < items.length; j++) {
      items[j].classList.remove('active');
    }
    document.getElementById(pageId).classList.add('active');
    element.classList.add('active');
  }

  var modal = document.getElementById('imgModal');
  var modalImg = document.getElementById('modalImg');
  var imgWrapper = document.getElementById('imgWrapper');
  var scale = 1, panning = false, pointX = 0, pointY = 0, startX = 0, startY = 0;

  function openModal(src, caption) {
    modal.classList.add('active'); 
    modalImg.src = src;
    document.getElementById('modalCaption').innerText = caption; 
    resetZoom();
  }
  function closeModal() { modal.classList.remove('active'); }
  function applyTransform() { modalImg.style.transform = 'translate(' + pointX + 'px, ' + pointY + 'px) scale(' + scale + ')'; }
  function zoomImg(delta) { scale += delta; if(scale < 0.5) scale = 0.5; if(scale > 5) scale = 5; applyTransform(); }
  function resetZoom() { scale = 1; pointX = 0; pointY = 0; applyTransform(); }

  imgWrapper.onwheel = function(e) { e.preventDefault(); zoomImg(e.deltaY * -0.002); };
  imgWrapper.onmousedown = function(e) { e.preventDefault(); startX = e.clientX - pointX; startY = e.clientY - pointY; panning = true; };
  imgWrapper.onmouseup = function() { panning = false; };
  imgWrapper.onmouseleave = function() { panning = false; };
  imgWrapper.onmousemove = function(e) { if (!panning) return; e.preventDefault(); pointX = e.clientX - startX; pointY = e.clientY - startY; applyTransform(); };

  function manualSync() {
    var icon = document.querySelector('.btn-sync i');
    icon.classList.add('fa-spin');
    setTimeout(function() { icon.classList.remove('fa-spin'); }, 1000);
    fetchTelemetryData();
  }

  async function fetchTelemetryData() {
    try {
      var response = await fetch('/visualizations/optimization_log.csv?t=' + new Date().getTime());
      if(response.ok) {
        var text = await response.text();
        var rows = text.trim().split('\n');
        if(rows.length > 1) {
          var headers = rows[0].split(',').map(function(h) { return h.trim().replace(/['"]/g, ''); });
          
          var idxTime = headers.findIndex(function(h) { return h.toLowerCase().includes('time'); });
          var idxRSSI = headers.findIndex(function(h) { return h.toLowerCase().includes('rssi'); });
          var idxLat = headers.findIndex(function(h) { return h.toLowerCase().includes('lat'); });
          var idxUtil = headers.findIndex(function(h) { return h.toLowerCase().includes('util'); });
          var idxDec = headers.findIndex(function(h) { return h.toLowerCase().includes('dec'); });
          var idxScore = headers.findIndex(function(h) { return h.toLowerCase().includes('qual') || h.toLowerCase().includes('score'); });
          var idxInterf = headers.findIndex(function(h) { return h.toLowerCase().includes('interf'); });
          var idxCh = headers.findIndex(function(h) { return h.toLowerCase().includes('channel'); });
          var idxBest = headers.findIndex(function(h) { return h.toLowerCase().includes('best') || h.toLowerCase().includes('after'); });

          if (idxTime === -1) idxTime = 0;
          if (idxCh === -1) idxCh = 1;
          if (idxRSSI === -1) idxRSSI = 2;
          if (idxUtil === -1) idxUtil = 4;
          if (idxLat === -1) idxLat = 5;
          if (idxDec === -1) idxDec = headers.length - 1;

          var latestCols = rows[rows.length - 1].split(',').map(function(c) { return c.trim().replace(/['"]/g, ''); });
          
          if(idxScore !== -1 && latestCols[idxScore]) document.getElementById('kpi-health').innerText = latestCols[idxScore] + '%';
          if(idxRSSI !== -1 && latestCols[idxRSSI]) document.getElementById('kpi-rssi').innerText = latestCols[idxRSSI] + ' dBm';
          if(idxLat !== -1 && latestCols[idxLat]) document.getElementById('kpi-latency').innerText = latestCols[idxLat] + ' ms';
          if(idxUtil !== -1 && latestCols[idxUtil]) document.getElementById('kpi-utilization').innerText = latestCols[idxUtil] + '%';
          if(idxInterf !== -1 && latestCols[idxInterf]) document.getElementById('kpi-interference').innerText = latestCols[idxInterf];

          if(idxCh !== -1 && latestCols[idxCh]) {
            var chs = latestCols[idxCh].split('_');
            document.getElementById('router-ch24').innerText = 'Ch ' + chs[0];
            document.getElementById('router-ch5').innerText = 'Ch ' + (chs[1] || '36');
            document.getElementById('prev-24').innerText = 'Ch ' + chs[0];
            document.getElementById('prev-5').innerText = 'Ch ' + (chs[1] || '36');
          }
          if(idxBest !== -1 && latestCols[idxBest]) {
            var bChs = latestCols[idxBest].split('_');
            document.getElementById('best-24').innerText = 'Ch ' + bChs[0];
            document.getElementById('best-5').innerText = 'Ch ' + (bChs[1] || '36');
          }

          var timelineHtml = '';
          var startTimeline = Math.max(1, rows.length - 4);
          for(var i = rows.length - 1; i >= startTimeline; i--) {
            var rCols = rows[i].split(',').map(function(c) { return c.trim().replace(/['"]/g, ''); });
            var ts = rCols[idxTime] ? rCols[idxTime].split(' ').pop().substring(0, 5) : '--:--';
            var dec = rCols[idxDec] || 'No Change';
            var icon = dec.includes('No Change') ? 'fa-check-circle' : 'fa-exchange-alt';
            var color = dec.includes('No Change') ? 'var(--success)' : 'var(--brand)';
            timelineHtml += '<div class="timeline-item">' +
              '<div class="timeline-dot" style="background: ' + color + ';"></div>' +
              '<div class="timeline-time">' + ts + '</div>' +
              '<div class="timeline-text"><i class="fas ' + icon + '" style="color: ' + color + '; margin-right: 6px;"></i> ' + dec + '</div>' +
            '</div>';
          }
          document.getElementById('timeline-container').innerHTML = timelineHtml;

          var tbodyHtml = '';
          for(var i = rows.length - 1; i > 0 && i > rows.length - 16; i--) {
            var cols = rows[i].split(',').map(function(c) { return c.trim().replace(/['"]/g, ''); });
            var dec = cols[idxDec] || 'N/A';
            var decColor = dec.includes('No Change') ? '#94A3B8' : '#10B981';
            var rssiVal = cols[idxRSSI] || '-';
            var latVal = cols[idxLat] || '-';
            var utilVal = cols[idxUtil] || '-';
            var timeVal = cols[idxTime] || '-';
            
            tbodyHtml += '<tr>' +
              '<td>' + timeVal + '</td>' +
              '<td><span style="color:#38BDF8;">' + rssiVal + ' dBm</span></td>' +
              '<td>' + latVal + ' ms</td>' +
              '<td>' + utilVal + '%</td>' +
              '<td style="color:' + decColor + '; font-weight:600;">' + dec + '</td>' +
            '</tr>';
          }
          document.getElementById('telemetry-body').innerHTML = tbodyHtml;
          document.getElementById('sync-time').innerText = new Date().toLocaleTimeString();
        }
      }
    } catch (e) {
      console.log('Fetching telemetry...');
    }
  }

  setInterval(fetchTelemetryData, 5000);
  document.addEventListener('DOMContentLoaded', fetchTelemetryData);
</script>
</body>
</html>'''

    html_template = html_template.replace('__LAST_SYNC__', str(last_sync))
    html_template = html_template.replace('__HEALTH_SCORE__', str(health_score))
    html_template = html_template.replace('__RSSI__', str(rssi))
    html_template = html_template.replace('__LATENCY__', str(latency))
    html_template = html_template.replace('__UTILIZATION__', str(utilization))
    html_template = html_template.replace('__INTERFERENCE__', str(interference))
    html_template = html_template.replace('__CH24__', str(ch24))
    html_template = html_template.replace('__CH5__', str(ch5))
    html_template = html_template.replace('__STATUS_R__', str(status_r))
    html_template = html_template.replace('__PREV_24__', str(prev_24))
    html_template = html_template.replace('__PREV_5__', str(prev_5))
    html_template = html_template.replace('__BEST_24__', str(best_24))
    html_template = html_template.replace('__BEST_5__', str(best_5))
    html_template = html_template.replace('__TIMELINE_HTML__', str(timeline_html))
    html_template = html_template.replace('__VIS_VALIDATION__', str(vis_validation))
    html_template = html_template.replace('__VIS_SPECTRUM__', str(vis_spectrum))
    html_template = html_template.replace('__VIS_RESEARCH__', str(vis_research))

    return html_template

class DashboardHandler(http.server.SimpleHTTPRequestHandler):
    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)
        
        # 1. Jika akses halaman utama, sedut data dan bagi HTML
        if parsed.path in ('/', '/index.html'):
            sedut_realtime_log_dari_router()
            content = build_html().encode('utf-8')
            self.send_response(200)
            self.send_header('Content-Type', 'text/html; charset=utf-8')
            self.send_header('Content-Length', str(len(content)))
            self.end_headers()
            self.wfile.write(content)
            
        # 2. JIKA BROWSER MINTA FAIL CSV (Sama ada dari butang Sync atau Auto-Refresh 5min)
        elif parsed.path.endswith('optimization_log.csv'):
            # Paksa Python pergi masuk router dan ambil log paling mutakhir dahulu!
            sedut_realtime_log_dari_router()
            super().do_GET()
            
        else:
            super().do_GET()
    
    def log_message(self, format, *args):
        return

def run_dashboard(port=PORT):
    current_dir = os.path.dirname(os.path.abspath(__file__))
    os.chdir(current_dir)
    while True:
        try:
            with socketserver.TCPServer(('127.0.0.1', port), DashboardHandler) as httpd:
                print(f"[DZNETS Enterprise NOC] System active at http://127.0.0.1:{port}")
                webbrowser.open(f"http://127.0.0.1:{port}")
                httpd.serve_forever()
        except OSError:
            port += 1

if __name__ == '__main__':
    run_dashboard()