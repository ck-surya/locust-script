# Impact Document: Log-Based Traffic Simulation using Locust

## **Objective**
The goal of this document is to outline the impact, methodology, and expected outcomes of using log files to simulate real-world traffic loads on a server using Locust. This process helps in accurately replicating user behavior based on historical data, ensuring precise performance testing.

---

## **1. Overview of Log-Based Traffic Simulation**
Traditionally, Locust simulations are configured manually with predefined users (`--users`) and spawn rates (`--spawn-rate`). Instead, we propose dynamically extracting these values from server logs to:
- Maintain real-world request timing.
- Use actual user data for authentication and request execution.
- Simulate server load as close to production as possible.

---

## **2. Process Flow**
### **Step 1: Extracting Data from Logs**
- Read log files containing request timestamps, IP addresses, request URLs, and user agents.
- Extract unique users based on IP addresses to determine the total number of `users`.
- Identify request frequency to compute the `spawn_rate` dynamically.
- Parse CSRF tokens where required for authentication.

### **Step 2: Preprocessing & Configuration**
- Precompute `users` and `spawn_rate` from log analysis.
- Organize user credentials for login scenarios.
- Store extracted CSRF tokens for session continuity.

### **Step 3: Running Locust with Dynamic Parameters**
- Configure Locust to use dynamically extracted `users` and `spawn_rate`.
- Ensure login sessions are correctly managed by using pre-extracted CSRF tokens.
- Use Locust to execute GET/POST requests based on extracted request sequences and timestamps.

---

## **3. Script Implementation**

### **Log Analysis Script**
Extract `users` and `spawn_rate` dynamically:
```python
import re
from collections import defaultdict

def analyze_logs(log_file):
    unique_ips = set()
    requests_per_second = defaultdict(int)

    with open(log_file, "r") as f:
        for line in f:
            match = re.search(r'(\d+\.\d+\.\d+\.\d+):\d+ .* (\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2})', line)
            if match:
                ip, timestamp = match.groups()
                unique_ips.add(ip)
                requests_per_second[timestamp] += 1

    max_spawn_rate = max(requests_per_second.values(), default=1)
    return len(unique_ips), max_spawn_rate

users, spawn_rate = analyze_logs("path/to/logfile.log")
print(f"Determined Users: {users}, Spawn Rate: {spawn_rate}")
```

### **Locust Execution Script**
```python
from locust import HttpUser, task, between
import subprocess

# Run log analysis to determine test parameters
users, spawn_rate = analyze_logs("path/to/logfile.log")

class WebsiteUser(HttpUser):
    wait_time = between(1, 3)
    
    @task
    def login_request(self):
        self.client.get("/login")

if __name__ == "__main__":
    subprocess.run(["locust", "--users", str(users), "--spawn-rate", str(spawn_rate)])
```

---

## **4. Expected Outcomes**
### **Benefits**
- **Realistic Load Testing**: The test mimics actual user behavior and server stress.
- **Adaptive Scaling**: The system adjusts to historical peak loads dynamically.
- **Better Debugging & Optimization**: Performance issues can be diagnosed with data-driven insights.

### **Challenges & Considerations**
- **Log Format Consistency**: Parsing logic must align with log file structure.
- **CSRF Token Handling**: Sessions need to persist for accurate authentication.
- **Large Log File Processing**: Optimization techniques (e.g., batching) may be needed for high-volume logs.

---

## **5. Conclusion**
This approach significantly enhances the reliability of performance testing by accurately simulating production-like traffic. By dynamically setting `users` and `spawn_rate` based on real-world logs, we ensure a scalable and adaptive load testing framework.

