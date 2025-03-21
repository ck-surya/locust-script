import os
import time
import csv
import re
from datetime import datetime, timedelta
from locust import HttpUser, task, between, events
from locust.runners import MasterRunner
from requests.exceptions import RequestException

# Load user credentials
with open("config/credentials.csv", "r") as f:
    reader = csv.DictReader(f)
    credentials = list(reader)

# Load and merge log data from all ELB logs
log_entries = []
log_dir = "logs/elb-logs"

for filename in os.listdir(log_dir):
    if filename.endswith(".log") or filename.endswith(".txt"):
        with open(os.path.join(log_dir, filename), "r") as f:
            for line in f:
                match = re.search(r"(\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\.\d+Z).*?\"(\w+) (https?://\S+) HTTP", line)
                if match:
                    timestamp_str, method, url = match.groups()

                    # Convert to datetime in UTC
                    utc_dt = datetime.strptime(timestamp_str, "%Y-%m-%dT%H:%M:%S.%fZ")
                    
                    # Convert to IST
                    ist_dt = utc_dt + timedelta(hours=5, minutes=30)
                    ist_hour = ist_dt.hour
                    ist_min = ist_dt.minute

                    # Filter: include only 17:30 to 20:30 IST
                    if (ist_hour == 17 and ist_min >= 30) or (18 <= ist_hour < 20) or (ist_hour == 20 and ist_min <= 30):
                        log_entries.append({
                            "timestamp": utc_dt.timestamp(),  # keep original UTC timestamp for timing logic
                            "method": method,
                            "url": url
                        })

# Sort by time
log_entries.sort(key=lambda x: x["timestamp"])
log_start_time = log_entries[0]["timestamp"] if log_entries else 0
start_time = time.time()

@events.init.add_listener
def on_locust_init(environment, **_kwargs):
    if isinstance(environment.runner, MasterRunner):
        print("Running in distributed mode")

class LogReplayUser(HttpUser):
    wait_time = between(1, 2)

    def on_start(self):
        self.log_index = 0
        self.user_creds = credentials.pop() if credentials else {}
        self.csrf_token = self.get_csrf_token()
        if self.csrf_token:
            self.login()

    def get_csrf_token(self):
        try:
            res = self.client.get("https://test1.indiaicpc.in/login", allow_redirects=True)
            token = re.search(r'name="_csrf_token" value="(.+?)"', res.text)
            return token.group(1) if token else None
        except RequestException as e:
            print(f"❌ CSRF token error: {e}")
            return None

    def login(self):
        try:
            res = self.client.post("https://test1.indiaicpc.in/login", data={
                "_csrf_token": self.csrf_token,
                "_username": self.user_creds.get("Username"),
                "_password": self.user_creds.get("Password")
            }, allow_redirects=True)

            if res.status_code == 200:
                print(f"✅ Login successful: {self.user_creds.get('Username')}")
            else:
                print(f"❌ Login failed: {res.status_code} - {self.user_creds.get('Username')}")
        except RequestException as e:
            print(f"❌ Login exception: {e}")

    @task
    def replay_logs(self):
        if self.log_index >= len(log_entries):
            return

        log_entry = log_entries[self.log_index]
        now = time.time()
        elapsed = now - start_time
        target_elapsed = log_entry["timestamp"] - log_start_time

        if elapsed < target_elapsed:
            time.sleep(target_elapsed - elapsed)

        method = log_entry["method"]
        url = re.sub(r"https://contest\.indiaicpc\.in(:443)?", "https://test1.indiaicpc.in", log_entry["url"])

        try:
            if method == "GET":
                res = self.client.get(url)
            elif method == "POST":
                res = self.client.post(url)
            print(f"{method} {url} => {res.status_code}")
        except RequestException as e:
            print(f"❗ Request error: {e}")

        self.log_index += 1
    