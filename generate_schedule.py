import json

def generate_schedule(json_path):
    with open(json_path, "r") as f:
        log_data = json.load(f)

    schedule = []

    for time_slot, methods in sorted(log_data.items()):
        requests = []
        total_users = 0

        for method, method_data in methods.items():
            for url, info in method_data["url_list"].items():
                count = info["count"]
                total_users += count
                requests.append({
                    "method": method,
                    "url": url,
                    "count": count
                })

        spawn_rate = max(1, total_users // 10)  # adjust as needed

        schedule.append({
            "timestamp": time_slot,
            "users": total_users,
            "spawn_rate": spawn_rate,
            "requests": requests
        })

    with open("traffic_schedule.json", "w") as f:
        json.dump(schedule, f, indent=4)

    print("✅ Traffic schedule generated: traffic_schedule.json")

if __name__ == "__main__":
    generate_schedule("url_processed_logs_IST.json")
