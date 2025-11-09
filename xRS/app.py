from flask import Flask, request, jsonify
from backend import services
import json

app = Flask(__name__)

server_data = {}

with open('config.json', 'r') as file:
    data = json.load(file)
servers_config = data["Servers_config"]
latency_rings_config =  data["Latency_rings_config"]
latency_rings_threshold = data["Latency_rings_threshold"]
xRS_url = data["xRS_url"]

lms = services.LatencyMonitoringService(servers_config, latency_rings_config, xRS_url)
lms.monitor_loop(interval=30)

@app.route('/report', methods=['POST'])
def report_load():
    data = request.json
    server_ip = request.remote_addr
    cpu_load = data['cpu_load']
    server_data[server_ip] = {
        'cpu': cpu_load,
        'time': data['timestamp'],
    }
    
    return jsonify({'status': 'ok'})

@app.route('/servers', methods=['GET'])
def view_servers():
    return jsonify(server_data)

@app.route('/lrings', methods=['GET'])
def get_latency_rings():
    return jsonify(lms.latency_rings)


app.run(host='0.0.0.0', port=5000)