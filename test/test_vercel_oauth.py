import urllib.request
import urllib.parse
import re

url = "https://hire-wise-xi.vercel.app/auth/google/login"
req = urllib.request.Request(url, method="GET")

try:
    response = urllib.request.urlopen(req)
except urllib.error.HTTPError as e:
    # 302 redirect is expected, urllib might throw HTTPError for it or follow it
    pass
except Exception as e:
    print("Error:", e)

# Let's use curl to follow redirects and see cookies
import subprocess
result = subprocess.run(['curl', '-s', '-i', url], capture_output=True, text=True)
print("Headers from Vercel:")
print(result.stdout)
