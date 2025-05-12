from datetime import timedelta
from locust import HttpUser, task, between, LoadTestShape 
from locust import events
import json
import random
import time
import re
import csv
import threading
from requests.exceptions import RequestException

# ---- Load Credentials (Thread-safe) ----
credentials = []
cred_lock = threading.Lock()

test_start_time = None


@events.test_start.add_listener
def on_test_start(environment, **kwargs):
    global test_start_time
    test_start_time = time.time()

with open("credentials.csv", newline='') as csvfile:
    reader = csv.DictReader(csvfile)
    for row in reader:
        credentials.append({"Username": row["Username"], "Password": row["Password"]})

def get_credential():
    with cred_lock:
        return credentials.pop() if credentials else {"Username": "", "Password": ""}

# ---- Load Traffic Schedule ----
with open("traffic_schedule.json") as f:
    TRAFFIC_SCHEDULE = json.load(f)

# ---- Prepare Queue ----
def parse_timestamp_to_offset(timestamp):
    start_str, _ = timestamp.split(" - ")
    hours, minutes = map(int, start_str.split(":"))
    return timedelta(hours=hours, minutes=minutes)

REQUEST_QUEUE = []
for batch in TRAFFIC_SCHEDULE:
    REQUEST_QUEUE.append({
        "offset": parse_timestamp_to_offset(batch["timestamp"]),
        "users": batch["users"],
        "spawn_rate": batch["spawn_rate"],
        "requests": batch["requests"]
    })

print(REQUEST_QUEUE[0]["requests"])  # Example output
#  {'method': 'GET', 'url': '/team/team/9122', 'count': 1}
exit()
# ---- Authenticated Locust User ----
class LogReplayUser(HttpUser):
    wait_time = between(1, 2)

    def on_start(self):
        """Called when a user starts. This is where we can handle authentication and session setup."""
        self.user_creds = get_credential()
        self.csrf_token = self.get_csrf_token()
        if self.csrf_token:
            self.login()
        else:
            print(f"❌ CSRF token not found for user {self.user_creds.get('Username')}")

    def get_csrf_token(self):
        """Retrieves the CSRF token required for login."""
        try:
            res = self.client.get("/login", allow_redirects=True)
            token = re.search(r'name="_csrf_token" value="(.+?)"', res.text)
            return token.group(1) if token else None
        except RequestException as e:
            print(f"❌ CSRF token error: {e}")
            return None

    def login(self):
        """Sends a POST request to log in with credentials."""
        try:
            res = self.client.post("/login", data={
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

    # @task
    def replay_traffic(self):
        """Replays the traffic according to the current batch's schedule."""
        if not self.environment.runner:
            return

        current_batch = self.get_active_batch()
        if current_batch:
            weighted_requests = []
            for req in current_batch["requests"]:
                weighted_requests.extend([req] * req["count"])

            if weighted_requests:
                selected = random.choice(weighted_requests)
                url = selected["url"]
                method = selected["method"]
                if "/ICPC24ONLINE" not in url:
                    try:
                        if method == "GET":
                            res = self.client.get(url)
                        elif method == "POST":
                            res = self.client.post(url, data={})  # Customize if needed
                        else:
                            print(f"⚠️ Unknown method: {method}")
                            return
                        print(f"➡️  {method} {url} - {res.status_code}")
                    except RequestException as e:
                        print(f"❌ Request error: {method} {url} - {e}")
    @task
    def makeRequest(self):
        self.client.get("/team")  # Example request

    def get_active_batch(self):
        global test_start_time
        if not test_start_time:
            return None

        elapsed_time = time.time() - test_start_time

        for batch in REQUEST_QUEUE:
            batch_start = batch["offset"].total_seconds()
            batch_end = batch_start + 300  # 5 minutes

            if batch_start <= elapsed_time < batch_end:
                return batch
        return None

# ---- Load Shape Based on Schedule ----

class StepLoadShape(LoadTestShape):
    def __init__(self):
        super().__init__()
        self.schedule = REQUEST_QUEUE
        self._environment = None  # manually store environment here

    def tick(self):
        elapsed_time = self.get_run_time()

        for batch in self.schedule:
            batch_start = batch["offset"].total_seconds()
            batch_end = batch_start + 300

            if batch_start <= elapsed_time < batch_end:
                users = batch["users"]
                spawn_rate = batch["spawn_rate"]
                print(f"✅ Active Batch | 👥 Users: {users} | 🚀 Spawn rate: {spawn_rate}")
                return (users, spawn_rate)

        print("✅ Load test complete.")
        return None

    def get_run_time(self):
        if not self._environment or not self._environment.runner:
            return 0
        return time.time() - self._environment.runner.start_time

    def on_start(self, environment):
        self._environment = environment

