from flask import Flask, request, jsonify
from backend import services
import json
from threading import Thread

app = Flask(__name__)

server_data = {}

with open('config.json', 'r') as file:
    data = json.load(file)
servers_config = data["Servers_config"]
latency_rings_config =  data["Latency_rings_config"]
latency_rings_threshold = data["Latency_rings_threshold"]
xRS_url = data["xRS_url"]

lms = services.LatencyMonitoringService(servers_config, latency_rings_config, xRS_url)
xrs = services.xRSService(latency_rings_threshold)

monitoring_thread = Thread(target=lms.monitor_loop, args=(30,), daemon=True)
monitoring_thread.start()

xrs_thread = Thread(target=xrs.monitor_loop, args=(lms, server_data, 5), daemon=True)
xrs_thread.start()

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
    return jsonify(lms.get_latency_rings())

@app.route('/routing-table', methods=['GET'])
def get_routing_table():
    return jsonify(xrs.get_routing_table())

@app.route('/regions-load', methods=['GET'])
def get_regions_load():
    latency_rings = lms.get_latency_rings()
    regions_load = xrs.calculate_ring_load(latency_rings, server_data)
    return jsonify(regions_load)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)