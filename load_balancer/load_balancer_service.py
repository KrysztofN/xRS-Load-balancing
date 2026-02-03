import requests
import json 
import random
import time
from threading import Thread, Lock
from typing import Dict, Optional
import csv
from datetime import datetime

class LoadBalancer:
    def __init__(self):
        self.routing_table = {}
        self.server_data = {}
        self.latency_rings = {}
        self.regions_load = {}
        self.request_count = 0
        self.failed_requests = 0
        self.lock = Lock()
        
        self.ring_request_counts = {"Ring1": 0, "Ring2": 0, "Ring3": 0}
        self.server_request_counts = {}
        
        with open('config.json', 'r') as file:
            data = json.load(file)
        self.xrs_url = data["xRS_url"]
        
        self.initialize_csv_files()

    def initialize_csv_files(self):
        with open('ring_loads.csv', 'w', newline='') as f:
            writer = csv.writer(f)
            writer.writerow(['timestamp', 'ring', 'load'])
        
        with open('server_loads.csv', 'w', newline='') as f:
            writer = csv.writer(f)
            writer.writerow(['timestamp', 'server_ip', 'load'])
        
        with open('ring_rps.csv', 'w', newline='') as f:
            writer = csv.writer(f)
            writer.writerow(['timestamp', 'ring', 'rps'])
        
        with open('server_rps.csv', 'w', newline='') as f:
            writer = csv.writer(f)
            writer.writerow(['timestamp', 'server_ip', 'rps'])
        
        with open('routing_table.csv', 'w', newline='') as f:
            writer = csv.writer(f)
            writer.writerow(['timestamp', 'ring', 'percentage'])
        
        with open('system_state.csv', 'w', newline='') as f:
            writer = csv.writer(f)
            writer.writerow(['timestamp', 'state', 'total_rps', 'success_rate'])

    def get_routing_table(self):
        try:
            response = requests.get(self.xrs_url + '/routing-table', timeout=5)
            response.raise_for_status()
            self.routing_table = response.json()
        except Exception as e:
            print(f"Error fetching routing table: {e}")
    
    def get_servers_data(self):
        try:
            response = requests.get(self.xrs_url + '/servers', timeout=5)
            response.raise_for_status()
            self.server_data = response.json()
        except Exception as e:
            print(f"Error fetching server data: {e}")
    
    def get_latency_rings(self):
        try:
            response = requests.get(self.xrs_url + '/lrings', timeout=5)
            response.raise_for_status()
            self.latency_rings = response.json()
        except Exception as e:
            print(f"Error fetching latency rings: {e}")
    
    def get_regions_load(self):
        try:
            response = requests.get(self.xrs_url + '/regions-load', timeout=5)
            response.raise_for_status()
            self.regions_load = response.json()
        except Exception as e:
            print(f"Error fetching regions load: {e}")
    
    def get_system_state(self):
        try:
            response = requests.get(self.xrs_url + '/state', timeout=5)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            return 'unknown'
    
    def save_all_data(self):
        timestamp = datetime.now().isoformat()
        
        with open('ring_loads.csv', 'a', newline='') as f:
            writer = csv.writer(f)
            for ring, load in self.regions_load.items():
                writer.writerow([timestamp, ring, load])
        
        with open('server_loads.csv', 'a', newline='') as f:
            writer = csv.writer(f)
            for server_ip, data in self.server_data.items():
                writer.writerow([timestamp, server_ip, data['cpu']])
        
        with self.lock:
            ring_rps = self.ring_request_counts.copy()
            server_rps = self.server_request_counts.copy()
            self.ring_request_counts = {"Ring1": 0, "Ring2": 0, "Ring3": 0}
            self.server_request_counts = {}
        
        with open('ring_rps.csv', 'a', newline='') as f:
            writer = csv.writer(f)
            for ring, rps in ring_rps.items():
                writer.writerow([timestamp, ring, rps])
        
        with open('server_rps.csv', 'a', newline='') as f:
            writer = csv.writer(f)
            for server_ip, rps in server_rps.items():
                writer.writerow([timestamp, server_ip, rps])
        
        with open('routing_table.csv', 'a', newline='') as f:
            writer = csv.writer(f)
            for ring, percentage in self.routing_table.items():
                writer.writerow([timestamp, ring, percentage])
        
        state = self.get_system_state()
        with self.lock:
            total_rps = self.request_count
            failed = self.failed_requests
            success_rate = (total_rps / (total_rps + failed) * 100) if (total_rps + failed) > 0 else 100.0
        
        with open('system_state.csv', 'a', newline='') as f:
            writer = csv.writer(f)
            writer.writerow([timestamp, state, total_rps, success_rate])

    def update_data(self):
        self.get_routing_table()
        self.get_servers_data()
        self.get_latency_rings()
        self.get_regions_load()
        self.save_all_data()
    
    def update_loop(self, interval=1):
        while True:
            self.update_data()
            time.sleep(interval)
    
    def find_ring_for_server(self, server_ip: str) -> Optional[str]:
        for ring, servers in self.latency_rings.items():
            if server_ip in servers:
                return ring
        return None
        
    def pick2(self) -> Optional[str]:
        if not self.routing_table or not self.latency_rings:
            return None
        
        rings = list(self.routing_table.keys())
        weights = list(self.routing_table.values())
        
        valid_rings = [(ring, weight) for ring, weight in zip(rings, weights) if weight > 0]
        if not valid_rings:
            return None
        
        rings, weights = zip(*valid_rings)
        selected_ring = random.choices(rings, weights=weights, k=1)[0]
        
        servers = self.latency_rings.get(selected_ring, [])
        if not servers:
            return None
        
        if len(servers) == 1:
            return servers[0]
        
        if len(servers) == 2:
            candidate_0_ip = servers[0]
            candidate_1_ip = servers[1]
        else:
            rpc_candidates = random.sample(servers, k=2)
            candidate_0_ip = rpc_candidates[0]
            candidate_1_ip = rpc_candidates[1]
        
        load_0 = self.server_data.get(candidate_0_ip, {}).get('cpu', float('inf'))
        load_1 = self.server_data.get(candidate_1_ip, {}).get('cpu', float('inf'))
        
        rpc_target = candidate_0_ip if load_0 < load_1 else candidate_1_ip
        
        return rpc_target

    def send_request(self) -> Optional[dict]:
        rpc_target = self.pick2()
        
        if not rpc_target:
            with self.lock:
                self.failed_requests += 1
            return None
        
        try:
            response = requests.post(
                f"http://{rpc_target}:6000/compute",
                json={"number": 10},
                timeout=5
            )
            response.raise_for_status()
            
            ring = self.find_ring_for_server(rpc_target)
            
            with self.lock:
                self.request_count += 1
                if ring:
                    self.ring_request_counts[ring] = self.ring_request_counts.get(ring, 0) + 1
                self.server_request_counts[rpc_target] = self.server_request_counts.get(rpc_target, 0) + 1

            return response.json()
        except Exception as e:
            with self.lock:
                self.failed_requests += 1
            return None

    def request_loop(self):
        thread_start_time = time.time()
        
        while True:
            self.send_request()
            
            elapsed = time.time() - thread_start_time
            base_interval = 1.0
            
            if 30 <= elapsed < 80:
                interval = base_interval / 2 
            elif 150 <= elapsed < 250:
                interval = base_interval / 3  
            else:
                interval = base_interval
                
            time.sleep(interval)
    
    def reset_request_count(self):
        with self.lock:
            count = self.request_count
            failed = self.failed_requests
            self.request_count = 0
            self.failed_requests = 0
            return count, failed

if __name__ == "__main__":
    lb = LoadBalancer()
    
    update_thread = Thread(target=lb.update_loop, args=(1,), daemon=True)
    update_thread.start()
    
    request_thread = Thread(target=lb.request_loop, daemon=True)
    request_thread.start()

    try: 
        while True:
            time.sleep(1)
            reqps, failed = lb.reset_request_count()
            print(f"Requests: {reqps} req/s | Failed: {failed}")
    except KeyboardInterrupt:
        print("Shutting down load balancer")