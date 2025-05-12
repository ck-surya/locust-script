from locust import HttpUser, task, between, LoadTestShape, events
from requests.exceptions import RequestException
import random
import re
import threading
import csv

# ---- Load Credentials Thread-Safe ----
credentials = []
cred_lock = threading.Lock()

with open("credentials.csv", newline='') as csvfile:
    reader = csv.DictReader(csvfile)
    for row in reader:
        credentials.append({"Username": row["Username"], "Password": row["Password"]})

def get_credential():
    with cred_lock:
        return credentials.pop() if credentials else {"Username": "", "Password": ""}


class LogReplayUser(HttpUser):
    wait_time = between(0.1, 0.5)

    def on_start(self):
        self.user_creds = get_credential()
        self.csrf_token = self.get_csrf_token()
        if self.csrf_token:
            self.login()
        else:
            print(f"❌ CSRF token not found for user {self.user_creds.get('Username')}")

    def get_csrf_token(self):
        try:
            res = self.client.get("/login", allow_redirects=True)
            token = re.search(r'name="_csrf_token" value="(.+?)"', res.text)
            return token.group(1) if token else None
        except RequestException as e:
            print(f"❌ CSRF token error: {e}")
            return None

    def login(self):
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

    @task
    def make_request(self):
        # Send a request as an authenticated user
        url = random.choice(["/team", "/"])  # Add your endpoints here
        try:
            response = self.client.get(url)
            print(f"➡️  {url} - {response.status_code}")
        except RequestException as e:
            print(f"❌ Request failed for {url}: {e}")


class StepLoadShape(LoadTestShape):
    """
    Ramps users every 5 seconds:
    0–5s: 100 users
    5–10s: 200 users
    10–15s: 300 users
    """
    def tick(self):
        run_time = self.get_run_time()

        if run_time < 5:
            return (100, 20)
        elif run_time < 10:
            return (200, 40)
        elif run_time < 15:
            return (300, 60)
        elif run_time < 20:
            return (400, 80)
        elif run_time < 25:
            return (500, 100)
        elif run_time < 30:
            return (600, 120)
        elif run_time < 35:
            return (700, 140)
        elif run_time < 40:
            return (800, 160)
        elif run_time < 45:
            return (900, 180)
        else:
            return None
