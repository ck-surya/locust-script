import requests
import re

s = requests.Session()
res = s.get("https://icpc.rooknroll.in/login")
token = re.search(r'name="_csrf_token" value="(.+?)"', res.text).group(1)

res = s.post("https://icpc.rooknroll.in/login", data={
    "_csrf_token": token,
    "_username": "icpc24pc20017",
    "_password": "XZ8-rm3k6LE2kI9dMm8a-0B7XR7M5F03"
})

print(res.status_code)
print("Logged in!" if "DOMjudge" in res.text else "Login failed")
