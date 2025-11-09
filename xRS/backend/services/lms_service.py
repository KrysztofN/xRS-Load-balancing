from typing import Dict
import subprocess
import re
import time
from collections import defaultdict
from threading import Lock

class LatencyMonitoringService:
    def __init__(self, servers_config, latency_rings_config, xrs_url):
        self.servers = servers_config
        self.xrs_url = xrs_url
        self.last_update = None
        self.latency_rings_config = latency_rings_config 
        self.latency_rings = {}
        self.lock = Lock()

    def ping_server(self, ip_address: str, count: int = 5) -> Dict:
        try:
            cmd = ['ping', '-c', '4', ip_address]
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=10
            )

            if result.returncode != 0:
                return {
                    "ip": ip_address,
                    "reachable": False,
                    "error": "Host unreachable"
                }
            output = result.stdout

            stats_match = re.search(
                r'rtt min/avg/max/mdev = ([\d.]+)/([\d.]+)/([\d.]+)/([\d.]+)',
                output
            )

            if stats_match:
                return {
                    "ip": ip_address,
                    "reachable": True,
                    "max_ms": float(stats_match.group(3)),
                }

        except Exception as e:
            return {"ip": ip_address, "reachable": False, "error": str(e)}
            
    
    def calculate_ring_rtt(self):
        latency_ring = defaultdict(list)
        for server_ip in self.servers:
            ping_response = self.ping_server(server_ip)
            if ping_response.get("reachable"):
                rtt = ping_response["max_ms"]
                ring_name = self.get_latency_ring(rtt)
                latency_ring[ring_name].append(server_ip)
        
        with self.lock:
            self.latency_rings = dict(latency_ring)

    def get_latency_ring(self, rtt):
        for ring, latency in self.latency_rings_config.items():
            if rtt < latency:
                return ring
        return "Ring4"
    
    def monitor_loop(self, interval=30):
        while True:
            self.calculate_ring_rtt()
            time.sleep(interval)