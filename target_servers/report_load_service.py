import psutil
import requests
import time
import json

def get_cpu_load():
    return psutil.cpu_percent(interval=1)

def report_to_xrs(cpu_load, xRS_url):
    payload = {
        'cpu_load': cpu_load,
        'timestamp': time.time()
    }
    
    try:
        response = requests.post(xRS_url, json=payload, timeout=2)
        if response.status_code == 200:
            print(f"[{time.strftime('%H:%M:%S')}] Reported - CPU: {cpu_load}%")
        else:
            print(f"Error: XRS returned {response.status_code}")
    except requests.exceptions.RequestException as e:
        print(f"Failed to report to XRS: {e}")

def main():
    data = {}
    with open('config.json', 'r') as file:
        data = json.load(file)
    xRS_url = data["xRS_url"]
    report_interval = data["report_interval"]

    print(f"Reporting to: {xRS_url}")
    print(f"Report interval: {report_interval}s")
    
    while True:
        cpu_load = get_cpu_load()
        report_to_xrs(cpu_load)
        time.sleep(report_interval)

if __name__ == '__main__':
    main()