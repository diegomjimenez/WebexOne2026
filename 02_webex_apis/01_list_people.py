"""
Webex One 2026 - Troubleshoot and Manage Your Organization with an AI Assistant

- Diego Manuel Jimenez Moreno
- Mo Eyad Musallam
"""
# Step 01 - list people in the organization. Same shape as the Developer Portal snippet, token from .env.

import os
import sys
import requests
from dotenv import load_dotenv

load_dotenv()
token = os.getenv("ACCESS_TOKEN")

if not token:
    sys.exit("ACCESS_TOKEN is not set. Copy it into your .env file (see Getting Started).")

url = "https://webexapis.com/v1/people"
headers = {
    "Authorization": f"Bearer {token}"
}

response = requests.get(url, headers=headers, params={"max": 5})
print(response.json())
