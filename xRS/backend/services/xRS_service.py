from threading import Lock, Thread
from typing import Dict, List
from collections import defaultdict
from datetime import datetime
import time
import csv

class xRSService:
    def __init__(self, latency_rings_threshold: Dict[str, float]):
        self.enter_thresholds = latency_rings_threshold
        self.exit_thresholds = {
            ring: threshold * 0.7
            for ring, threshold in latency_rings_threshold.items()
        }
        self.routing_table = {}
        self.lock = Lock()
        self.current_state = "Ring1"

    def calculate_ring_load(self, latency_rings: Dict[str, List[str]], server_loads: Dict) -> Dict[str, float]:
        loads = defaultdict(float)
        
        for ring, server_list in latency_rings.items():
            server_count = 0
            cumulative_load = 0.0
            
            for server_ip in server_list:
                if server_ip in server_loads:
                    server_count += 1
                    cumulative_load += server_loads[server_ip]['cpu']
            
            if server_count > 0:
                loads[ring] = cumulative_load / server_count
            else:
                loads[ring] = 0.0
        
        return dict(loads)

    def createRoutingTable(self, latency_rings: Dict[str, List[str]], server_loads: Dict) -> Dict[str, int]:
        routing_table = {
            "Ring1": 0,
            "Ring2": 0,
            "Ring3": 0,
            "Ring4": 0
        }

        if not server_loads:
            routing_table["Ring1"] = 100
            with self.lock:
                self.routing_table = routing_table
            return routing_table

        loads = self.calculate_ring_load(latency_rings, server_loads)
        self.save_load_data(loads, server_loads)

        ring1_load = loads.get("Ring1", 0)
        ring2_load = loads.get("Ring2", 0)
        ring3_load = loads.get("Ring3", 0)
        
        if self.current_state == "Ring1":
            if ring1_load >= self.enter_thresholds.get("Ring1", 70):
                self.current_state = "ring2"
                routing_table = {"Ring1": 70, "Ring2": 30, "Ring3": 0, "Ring4": 0}
            else:
                routing_table = {"Ring1": 100, "Ring2": 0, "Ring3": 0, "Ring4": 0}
        
        elif self.current_state == "ring2":
            if ring1_load < self.exit_thresholds.get("Ring1", 49):
                self.current_state = "Ring1"
                routing_table = {"Ring1": 100, "Ring2": 0, "Ring3": 0, "Ring4": 0}
            elif ring2_load >= self.enter_thresholds.get("Ring2", 70):
                self.current_state = "ring3"
                routing_table = {"Ring1": 50, "Ring2": 30, "Ring3": 20, "Ring4": 0}
            else:
                routing_table = {"Ring1": 70, "Ring2": 30, "Ring3": 0, "Ring4": 0}
        
        elif self.current_state == "ring3":
            if ring2_load < self.exit_thresholds.get("Ring2", 49):
                self.current_state = "ring2"
                routing_table = {"Ring1": 70, "Ring2": 30, "Ring3": 0, "Ring4": 0}
            elif ring3_load >= self.enter_thresholds.get("Ring3", 70):
                self.current_state = "ring4"
                routing_table = {"Ring1": 40, "Ring2": 30, "Ring3": 20, "Ring4": 10}
            else:
                routing_table = {"Ring1": 50, "Ring2": 30, "Ring3": 20, "Ring4": 0}
        
        elif self.current_state == "ring4":
            if ring3_load < self.exit_thresholds.get("Ring3", 49):
                self.current_state = "ring3"
                routing_table = {"Ring1": 50, "Ring2": 30, "Ring3": 20, "Ring4": 0}
            else:
                routing_table = {"Ring1": 40, "Ring2": 30, "Ring3": 20, "Ring4": 10}
        
        with self.lock:
            self.routing_table = routing_table

        return routing_table

    def get_routing_table(self) -> Dict[str, int]:
        with self.lock:
            return self.routing_table.copy()
    
    def save_load_data(self, loads: Dict[str, float], server_loads: Dict):
        timestamp = datetime.now().isoformat()

        with open('ring_loads.csv', 'a', newline='') as csv_file:  
            writer = csv.writer(csv_file)
            if csv_file.tell() == 0:
                writer.writerow(['ring', 'load', 'timestamp', 'state'])
            for key, value in loads.items():
                writer.writerow([key, value, timestamp, self.current_state])
        
        with open('server_loads.csv', 'a', newline='') as csv_file:  
            writer = csv.writer(csv_file)
            if csv_file.tell() == 0:
                writer.writerow(['server_ip', 'load', 'timestamp'])
            for key, value in server_loads.items():
                writer.writerow([key, value['cpu'], timestamp])
    
    def monitor_loop(self, lms, server_data: Dict, interval: int = 1):
        while True:
            try:
                latency_rings = lms.get_latency_rings()
                self.createRoutingTable(latency_rings, server_data)
            except Exception as e:
                pass
            
            time.sleep(interval)