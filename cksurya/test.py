import os
import logging
import re
from collections import defaultdict

def process_logs(log_dir):
    if not os.path.exists(log_dir):
        logging.error(f"Log directory '{log_dir}' does not exist.")
        return None

    log_files = [f for f in os.listdir(log_dir) if f.endswith(".log")]
    interval_data = defaultdict(lambda: {"target_avg_time": [], "response_avg_time": [], "url_list": defaultdict(lambda: {"count": 0, "status_codes": defaultdict(int)})})

    unique_ips = set()
    requests_per_second = defaultdict(int)

    for file in log_files:
        file_path = os.path.join(log_dir, file)  # Fix incorrect file path
        try:
            with open(file_path, "r") as f:  # Use correct file path
                for line in f:
                    match = re.search(r'(\d+\.\d+\.\d+\.\d+):\d+ .* (\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2})', line)
                    if match:
                        ip, timestamp = match.groups()
                        unique_ips.add(ip)
                        requests_per_second[timestamp] += 1
        except Exception as e:
            logging.error(f"Error processing file '{file}': {e}")

    max_spawn_rate = max(requests_per_second.values(), default=1)
    return len(unique_ips), max_spawn_rate
# Example usage
log_dir_path = "../logs/elb-logs"
users, spawn_rate = process_logs(log_dir_path)
print(f"Unique Users: {users}, Spawn Rate: {spawn_rate}")



