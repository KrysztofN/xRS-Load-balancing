import requests
import json 
import random
import time
from threading import Thread

class LoadBalancer:
    def __init__(self):
        self.routing_table = {}
        self.server_data = {}
        self.latency_rings = {}
    
        with open('config.json', 'r') as file:
            data = json.load(file)
        self.xrs_url = data["xRS_url"]

    def get_routing_table(self):
        try:
            response = requests.get(self.xrs_url + '/routing', timeout=5)
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
    
    def update_data(self):
        self.get_routing_table()
        self.get_servers_data()
        self.get_latency_rings()
    
    def update_loop(self, interval=1):
        while True:
            self.update_data()
            time.sleep(interval)
        
    def pick2(self) -> str:
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
        
        rpc_candidates = random.sample(servers, k=min(2, len(servers)))
        
        candidate_0_ip = rpc_candidates[0]
        candidate_1_ip = rpc_candidates[1] if len(rpc_candidates) > 1 else rpc_candidates[0]
        
        load_0 = self.server_data.get(candidate_0_ip, {}).get('cpu', float('inf'))
        load_1 = self.server_data.get(candidate_1_ip, {}).get('cpu', float('inf'))
        
        rpc_target = candidate_0_ip if load_0 < load_1 else candidate_1_ip
        
        return rpc_target

    def send_request(self):
        rpc_target = self.pick2()
        
        if not rpc_target:
            return None
        
        try:
            response = requests.post(
                f"http://{rpc_target}:6000/compute",
                json={"number": 10},
                timeout=5
            )
            response.raise_for_status()
            return response.json()
        except Exception as e:
            print(f"Error sending request to {rpc_target}: {e}")
            return None

    def request_loop(self, interval=1):
        while True:
            self.send_request()
            time.sleep(interval)


if __name__ == "__main__":
    lb = LoadBalancer()
    
    update_thread = Thread(target=lb.update_loop, args=(1,), daemon=True)
    update_thread.start()
    
    request_thread = Thread(target=lb.request_loop, args=(1,), daemon=True)
    request_thread.start()