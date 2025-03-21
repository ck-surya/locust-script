import time
import csv
import re
from datetime import datetime
from locust import HttpUser, task, between, events
from locust.runners import MasterRunner
from requests.exceptions import RequestException

# Load user credentials
with open("../config/credentials.csv", "r") as f:
    reader = csv.DictReader(f)
    credentials = list(reader)

# Load log data
log_entries = []
with open("logfile.txt", "r") as f:
    for line in f:
        match = re.search(r"(\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\.\d+Z).*?\"(\w+) (https?://\S+) HTTP", line)
        if match:
            timestamp, method, url = match.groups()
            log_entries.append({
                "timestamp": datetime.strptime(timestamp, "%Y-%m-%dT%H:%M:%S.%fZ").timestamp(),
                "method": method,
                "url": url
            })

# Sort log entries by timestamp
log_entries.sort(key=lambda x: x["timestamp"])

# Reference start time for syncing requests
start_time = time.time()
log_start_time = log_entries[0]["timestamp"]

@events.init.add_listener
def on_locust_init(environment, **_kwargs):
    if isinstance(environment.runner, MasterRunner):
        print("Running in distributed mode")

class LogReplayUser(HttpUser):
    wait_time = between(1, 3)  # Ensures controlled pacing

    def on_start(self):
        """Assign a unique credential to each user & login."""
        self.log_index = 0
        if credentials:
            self.user_creds = credentials.pop()
            self.csrf_token = self.get_csrf_token()
            if self.csrf_token:
                self.login()

    def get_csrf_token(self):
        """Extract CSRF token from the login page."""
        try:
            response = self.client.get("https://test1.indiaicpc.in/login", allow_redirects=True)
            match = re.search(r'name="_csrf_token" value="(.+?)"', response.text)
            return match.group(1) if match else None
        except RequestException as e:
            print(f"CSRF Fetch Error: {e}")
            return None

    def login(self):
        """Log in using extracted CSRF token."""
        try:
            login_response = self.client.post("https://test1.indiaicpc.in/login", {
                "_csrf_token": self.csrf_token,
                "_username": self.user_creds["Username"],
                "_password": self.user_creds["Password"]
            }, allow_redirects=True)

            if login_response.status_code == 200:
                print(f"Login Success: {self.user_creds['Username']}")
            else:
                print(f"Login Failed: {self.user_creds['Username']} - {login_response.status_code}")
        except RequestException as e:
            print(f"Login Error: {e}")

    @task
    def replay_logs(self):
        """Replay the log file, ensuring correct request timing."""
        if self.log_index >= len(log_entries):
            return  # Stop if all logs are replayed

        log_entry = log_entries[self.log_index]
        current_time = time.time()
        elapsed_time = current_time - start_time
        expected_time = log_entry["timestamp"] - log_start_time

        # Wait until the correct time to send the request
        if elapsed_time < expected_time:
            time.sleep(expected_time - elapsed_time)

        # Perform authenticated request
        method = log_entry["method"]
        url = log_entry["url"]
        try:
            if method == "GET":
                response = self.client.get(url)
            elif method == "POST":
                response = self.client.post(url)

            print(f"{method} {url} - Status: {response.status_code}")

        except RequestException as e:
            print(f"Request Error: {e}")

        self.log_index += 1  # Move to the next log entry
