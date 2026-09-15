"""
Webex One 2026 - Troubleshoot and Manage Your Organization with an AI Assistant

- Diego Manuel Jimenez Moreno
- Mo Eyad Musallam

Refresh the Service App token.
"""

import os
from dotenv import load_dotenv
import requests

# Load environment variables from the .env file.
load_dotenv()

client_id = os.getenv("CLIENT_ID")
client_secret = os.getenv("CLIENT_SECRET")
refresh_token_val = os.getenv("REFRESH_TOKEN")

if not all([client_id, client_secret, refresh_token_val]):
    raise SystemExit("Please set CLIENT_ID, CLIENT_SECRET, and REFRESH_TOKEN in your .env file")

def refresh_token(client_id, client_secret, refresh_token):
    url = "https://webexapis.com/v1/access_token"

    payload = {
        'grant_type': 'refresh_token',
        'refresh_token': refresh_token,
        'client_id': client_id,
        'client_secret': client_secret,
    }

    headers = {
        'Content-type': 'application/x-www-form-urlencoded'
    }

    response = requests.post(url, headers=headers, data=payload)

    if response.status_code == 200:
        return response.json()
    else:
        raise Exception(f"Failed to refresh token: {response.status_code} - {response.text}")

if __name__ == "__main__":
    print("Refreshing Service App token...")
    token = refresh_token(client_id, client_secret, refresh_token_val)

    print("\n--- New Token Details ---")
    print(f"Access Token: {token['access_token']}")
    print(f"Expires in: {token['expires_in']} seconds")
    print(f"Refresh Token: {token['refresh_token']}")
    print(f"Refresh Token Expires in: {token['refresh_token_expires_in']} seconds")
    print(f"Token Type: {token['token_type']}")

    print("\nUpdate your .env file with the new ACCESS_TOKEN!")
