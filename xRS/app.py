from flask import Flask, request, jsonify

app = Flask(__name__)

server_data = {}

@app.route('/report', methods=['POST'])
def report_load():
    data = request.json
    server_ip = data['server_ip']
    cpu_load = data['cpu_load']
    active_requests = data['active_requests']
    server_data[server_ip] = {
        'cpu': cpu_load,
        'time': data['timestamp'],
        'active_requests' : active_requests
    }
    
    return jsonify({'status': 'ok'})

@app.route('/servers', methods=['GET'])
def view_servers():
    return jsonify(server_data)

app.run(host='0.0.0.0', port=5000)