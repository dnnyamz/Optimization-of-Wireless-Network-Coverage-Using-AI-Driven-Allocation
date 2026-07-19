# Optimization-of-Wireless-Network-Coverage-Using-AI-Driven-Allocation
# AI-Driven Wireless Network Optimization Dashboard

An intelligent wireless network optimization system designed to analyze live network conditions, predict channel utilization, mitigate interference, and dynamically recommend optimal channels using a Decision Tree machine learning model.

## Key Features
* **Real-Time Wireless Scanning:** Continuously tracks RSSI, channel utilization, and interference metrics.
* **Predictive AI Engine:** Utilizes a preprocessed Decision Tree model to recommend optimal channels.
* **Interactive Dashboard:** Live visualization of network performance statistics and historical trends.
* **Performance Validation:** Comparative tracking of network latency (ping) and throughput before and after AI deployment.

---

## Performance Visualizations

### 1. Network Latency & Stability Analysis
The system effectively flattens massive latency spikes, bringing down the ping response times to a highly stable threshold.
![Network Latency](results/Latency_Graph.png)

### 2. Throughput Performance Consistency
Evaluation across consecutive test cycles proves that the AI model secures consistently higher download and upload speeds while mitigating heavy fluctuations.
![Network Throughput](results/Throughput_graph.png)

---

## Project Structure
* `main_automation.py` - Core automation engine managing the optimization workflow.
* `dashboard.py` - Streamlit/Dash interface displaying network health and AI insights.
* `decision_tree_preprocessed.py` - The trained machine learning script handling channel recommendations.
* `network_data_visualization.py` - Script responsible for generating the analytical line graphs.
* `Ping_Before_AI.txt` / `Ping_After_AI.txt` - Raw network log files used for validation.

