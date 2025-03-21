import os
import csv
from collections import defaultdict
import datetime
from locust import HttpUser, task, between
import time



# Folder containing ELB logs
log_folder = "elb-logs"

# List to store all log entries
parsed_logs = []

# Iterate over all files in the folder
for filename in os.listdir(log_folder):
    if filename.endswith(".log"):  # Ensure we're reading only log files
        file_path = os.path.join(log_folder, filename)
        with open(file_path, "r") as file:
            reader = csv.reader(file, delimiter=" ")
            for row in reader:
                parsed_log = {
                    "type": row[0],
                    "timestamp": row[1],
                    "elb": row[2],
                    "client_ip": row[3].split(":")[0],
                    "client_port": row[3].split(":")[1],
                    "target_ip": row[4].split(":")[0],
                    "target_port": row[4].split(":")[1],
                    "request_processing_time": float(row[5]),
                    "target_processing_time": float(row[6]),
                    "response_processing_time": float(row[7]),
                    "elb_status_code": int(row[8]),
                    "target_status_code": int(row[9]),
                    "received_bytes": int(row[10]),
                    "sent_bytes": int(row[11]),
                    "request": row[12],
                    "user_agent": row[13],
                    "ssl_cipher": row[14],
                    "ssl_protocol": row[15],
                    "target_group_arn": row[16],
                    "trace_id": row[17],
                    "domain_name": row[18],
                    "chosen_cert_arn": row[19],
                    "matched_rule_priority": row[20],
                    "request_creation_time": row[21],
                    "actions_executed": row[22],
                    "redirect_url": row[23],
                    "error_reason": row[24],
                    "target_port_list": row[25],
                    "target_status_code_list": row[26],
                    "classification": row[27],
                    "classification_reason": row[28],
                }
                parsed_logs.append(parsed_log)

# Now `parsed_logs` contains all the parsed log data
# Group logs by timestamp
grouped_logs = defaultdict(list)

for log in parsed_logs:
    timestamp = log["timestamp"]  # e.g., "2024-11-15T23:55:06.858547Z"
    grouped_logs[timestamp].append(log)

# Sort the grouped logs by timestamp
sorted_timestamps = sorted(grouped_logs.keys())

sorted_timestamps = sorted(grouped_logs.keys())
log_sequence = [(timestamp, grouped_logs[timestamp]) for timestamp in sorted_timestamps]


def parse_timestamp(timestamp):
    return datetime.datetime.strptime(timestamp, "%Y-%m-%dT%H:%M:%S.%fZ")

# Calculate delays between timestamps
delays = []
for i in range(1, len(sorted_timestamps)):
    current_time = parse_timestamp(sorted_timestamps[i])
    previous_time = parse_timestamp(sorted_timestamps[i - 1])
    delay = (current_time - previous_time).total_seconds()
    delays.append(delay)

class TimestampUser(HttpUser):
    wait_time = between(0, 0)  # No wait time between tasks

    @task
    def replay_requests(self):
        for timestamp, requests in log_sequence:
            for request in requests:
                # Extract path and headers
                path = request["request"].split(" ")[1]
                headers = {"User-Agent": request["user_agent"]}

                # Send the request
                self.client.get(path, headers=headers)

            # Calculate delay until the next timestamp
            current_index = log_sequence.index((timestamp, requests))
            if current_index < len(log_sequence) - 1:
                next_timestamp = log_sequence[current_index + 1][0]
                current_time = parse_timestamp(timestamp)
                next_time = parse_timestamp(next_timestamp)
                delay = (next_time - current_time).total_seconds()
                time.sleep(delay)  # Wait until the next timestamp

