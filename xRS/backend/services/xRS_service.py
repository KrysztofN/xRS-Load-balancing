from threading import Lock
from typing import Dict, List
import time


class xRSService:
    def __init__(self, latency_rings_threshold: Dict[str, float], latency_rings_threshold_down: Dict[str, float]):
        self.thresholds = latency_rings_threshold
        self.downscale_thresholds = latency_rings_threshold_down
        self.routing_table = {}
        self.lock = Lock()
        self.current_state = "ring1_only"
        
        self.load_history = {
            "Ring1": [],
            "Ring2": [],
            "Ring3": []
        }
        self.max_history = 10
        self.last_state_change = time.time()
        self.min_state_duration = 30
        
    def calculate_ring_load(self, latency_rings: Dict[str, List[str]], server_loads: Dict) -> Dict[str, float]:
        loads = {}
        for ring, server_list in latency_rings.items():
            if not server_list:
                loads[ring] = 0.0
                continue
            
            max_load = 0.0
            for server_ip in server_list:
                if server_ip in server_loads:
                    max_load = max(max_load, server_loads[server_ip]['cpu'])
            
            loads[ring] = max_load
        
        return loads
    
    def smooth_load(self, ring: str, current_load: float) -> float:
        if ring not in self.load_history:
            self.load_history[ring] = []
        
        self.load_history[ring].append(current_load)
        if len(self.load_history[ring]) > self.max_history:
            self.load_history[ring].pop(0)
        
        return sum(self.load_history[ring]) / len(self.load_history[ring])

    def get_available_rings(self, latency_rings: Dict[str, List[str]]) -> List[str]:
        return [ring for ring, servers in latency_rings.items() if servers]

    def createRoutingTable(self, latency_rings: Dict[str, List[str]], server_loads: Dict) -> Dict[str, float]:
        routing_table = {ring: 0.0 for ring in latency_rings.keys()}
        
        if not server_loads:
            routing_table["Ring1"] = 100.0
            with self.lock:
                self.routing_table = routing_table
                self.current_state = "ring1_only"
            return routing_table

        available_rings = self.get_available_rings(latency_rings)
        
        if not available_rings:
            routing_table["Ring1"] = 100.0
            with self.lock:
                self.routing_table = routing_table
                self.current_state = "ring1_only"
            return routing_table

        loads_raw = self.calculate_ring_load(latency_rings, server_loads)
        
        loads = {}
        for ring in ["Ring1", "Ring2", "Ring3"]:
            loads[ring] = self.smooth_load(ring, loads_raw.get(ring, 0.0))
        
        ring1_load = loads.get("Ring1", 0.0)
        ring2_load = loads.get("Ring2", 0.0)
        ring3_load = loads.get("Ring3", 0.0)

        up_ring1_threshold = self.thresholds["Ring1"]
        up_ring2_threshold = self.thresholds["Ring2"]
        up_ring3_threshold = self.thresholds["Ring3"]
        
        down_ring1_threshold = self.downscale_thresholds["Ring1"]
        down_ring2_threshold = self.downscale_thresholds["Ring2"]
        down_ring3_threshold = self.downscale_thresholds["Ring3"]

        current_time = time.time()
        can_change_state = (current_time - self.last_state_change) >= self.min_state_duration
        
        new_state = self.current_state
        
        if self.current_state == "ring1_only":
            if "Ring1" not in available_rings:
                routing_table["Ring1"] = 100.0
            elif ring1_load > up_ring1_threshold and "Ring2" in available_rings and can_change_state:
                new_state = "ring1_ring2"
                self.last_state_change = current_time
                routing_table["Ring1"] = 50.0
                routing_table["Ring2"] = 50.0
            else:
                routing_table["Ring1"] = 100.0
        
        elif self.current_state == "ring1_ring2":
            if "Ring1" not in available_rings or "Ring2" not in available_rings:
                new_state = "ring1_only"
                self.last_state_change = current_time
                routing_table["Ring1"] = 100.0
            elif (ring1_load > up_ring2_threshold or ring2_load > up_ring2_threshold) and can_change_state:
                new_state = "ring1_ring2_partial"
                self.last_state_change = current_time
                routing_table["Ring1"] = 40.0
                routing_table["Ring2"] = 60.0
            elif (ring1_load < down_ring1_threshold and ring2_load < down_ring1_threshold) and can_change_state:
                new_state = "ring1_only"
                self.last_state_change = current_time
                routing_table["Ring1"] = 100.0
            else:
                routing_table["Ring1"] = 50.0
                routing_table["Ring2"] = 50.0
        
        elif self.current_state == "ring1_ring2_partial":
            if "Ring1" not in available_rings or "Ring2" not in available_rings:
                new_state = "ring1_only"
                self.last_state_change = current_time
                routing_table["Ring1"] = 100.0
            elif (ring1_load > up_ring3_threshold or ring2_load > up_ring3_threshold) and "Ring3" in available_rings and can_change_state:
                new_state = "ring1_ring2_ring3"
                self.last_state_change = current_time
                routing_table["Ring1"] = 30.0
                routing_table["Ring2"] = 50.0
                routing_table["Ring3"] = 20.0
            elif (ring1_load < down_ring2_threshold and ring2_load < down_ring2_threshold) and can_change_state:
                new_state = "ring1_ring2"
                self.last_state_change = current_time
                routing_table["Ring1"] = 50.0
                routing_table["Ring2"] = 50.0
            else:
                routing_table["Ring1"] = 40.0
                routing_table["Ring2"] = 60.0
        
        elif self.current_state == "ring1_ring2_ring3":
            if "Ring1" not in available_rings or "Ring2" not in available_rings or "Ring3" not in available_rings:
                new_state = "ring1_ring2_partial"
                self.last_state_change = current_time
                routing_table["Ring1"] = 40.0
                routing_table["Ring2"] = 60.0
            elif (ring1_load < down_ring3_threshold and ring2_load < down_ring3_threshold and ring3_load < down_ring3_threshold) and can_change_state:
                new_state = "ring1_ring2_partial"
                self.last_state_change = current_time
                routing_table["Ring1"] = 40.0
                routing_table["Ring2"] = 60.0
            else:
                routing_table["Ring1"] = 30.0
                routing_table["Ring2"] = 50.0
                routing_table["Ring3"] = 20.0
        
        with self.lock:
            self.routing_table = routing_table
            self.current_state = new_state

        return routing_table

    def get_routing_table(self) -> Dict[str, float]:
        with self.lock:
            return self.routing_table.copy()
    
    def get_current_state(self) -> str:
        with self.lock:
            return self.current_state
    
    def monitor_loop(self, lms, get_server_data, interval: int = 1):
        while True:
            try:
                latency_rings = lms.get_latency_rings()
                current_server_data = get_server_data()
                
                loads_raw = self.calculate_ring_load(latency_rings, current_server_data)
                
                loads_smoothed = {}
                for ring in ["Ring1", "Ring2", "Ring3"]:
                    if ring in self.load_history and self.load_history[ring]:
                        loads_smoothed[ring] = sum(self.load_history[ring]) / len(self.load_history[ring])
                    else:
                        loads_smoothed[ring] = 0.0
                
                current_time = time.time()
                time_since_change = current_time - self.last_state_change
                can_change = time_since_change >= self.min_state_duration
                
                print(f"[{time.strftime('%H:%M:%S')}] Raw: R1={loads_raw.get('Ring1', 0):.1f}% R2={loads_raw.get('Ring2', 0):.1f}% R3={loads_raw.get('Ring3', 0):.1f}% | "
                      f"Smooth: R1={loads_smoothed['Ring1']:.1f}% R2={loads_smoothed['Ring2']:.1f}% R3={loads_smoothed['Ring3']:.1f}% | "
                      f"State: {self.current_state} | Can change: {can_change} (waited {time_since_change:.0f}s/{self.min_state_duration}s) | "
                      f"Thresholds: {self.thresholds['Ring1']}%/{self.thresholds['Ring2']}%/{self.thresholds['Ring3']}%")
                
                self.createRoutingTable(latency_rings, current_server_data)
                
            except Exception as e:
                import traceback
                traceback.print_exc()
            time.sleep(interval)