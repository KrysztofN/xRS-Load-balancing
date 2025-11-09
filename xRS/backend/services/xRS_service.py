from threading import Lock, Thread
from typing import Dict, List
from collections import defaultdict
import time

class xRSService:
    def __init__(self, latency_rings_threshold: Dict[str, float]):
        self.routing_table = {}
        self.latency_rings_threshold = latency_rings_threshold
        self.lock = Lock()
    
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
            return routing_table

        loads = self.calculate_ring_load(latency_rings, server_loads)

        ring1_load = loads.get("Ring1", 0)
        ring2_load = loads.get("Ring2", 0)
        ring3_load = loads.get("Ring3", 0)

        ring1_threshold = self.latency_rings_threshold.get("Ring1", 0)
        ring2_threshold = self.latency_rings_threshold.get("Ring2", 0)
        ring3_threshold = self.latency_rings_threshold.get("Ring3", 0)

        if ring1_load < ring1_threshold:
            routing_table["Ring1"] = 100
        elif ring2_load < ring2_threshold:
            routing_table["Ring1"] = 70
            routing_table["Ring2"] = 30
        elif ring3_load < ring3_threshold:
            routing_table["Ring1"] = 50
            routing_table["Ring2"] = 30
            routing_table["Ring3"] = 20
        else:
            routing_table["Ring1"] = 40
            routing_table["Ring2"] = 30
            routing_table["Ring3"] = 20
            routing_table["Ring4"] = 10
        
        with self.lock:
            self.routing_table = routing_table

        return routing_table

    def get_routing_table(self) -> Dict[str, int]:
        with self.lock:
            return self.routing_table.copy()
    
    def monitor_loop(self, lms, server_data: Dict, interval: int = 5):
        while True:
            try:
                latency_rings = lms.get_latency_rings()
                self.createRoutingTable(latency_rings, server_data)
                
            except Exception as e:
                print(f"Error in xRS monitoring loop: {e}")
            
            time.sleep(interval)