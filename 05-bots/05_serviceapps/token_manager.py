"""Token manager: handles automatic refreshing of Service App tokens."""

import os
import time
import logging
import requests
from dotenv import load_dotenv, set_key

log = logging.getLogger("token-manager")

class TokenManager:
    def __init__(self, env_path=".env"):
        self.env_path = env_path
        load_dotenv(self.env_path)
        
        self.client_id = os.getenv("CLIENT_ID")
        self.client_secret = os.getenv("CLIENT_SECRET")
        self.refresh_token_val = os.getenv("REFRESH_TOKEN")
        self.access_token = os.getenv("ACCESS_TOKEN")
        self.expires_at = 0 

    def get_token(self):
        """Returns a valid access token, refreshing it if necessary."""
        # If we have a token and it hasn't expired (with a 60s safety buffer)
        if self.access_token and time.time() < self.expires_at:
            return self.access_token
        
        # Otherwise, refresh the token
        return self.refresh()

    def refresh(self):
        """Forces a token refresh via the Webex API."""
        log.info("Refreshing Service App token...")
        if not all([self.client_id, self.client_secret, self.refresh_token_val]):
            raise ValueError("Missing CLIENT_ID, CLIENT_SECRET, or REFRESH_TOKEN in environment.")

        url = "https://webexapis.com/v1/access_token"
        payload = {
            'grant_type': 'refresh_token',
            'refresh_token': self.refresh_token_val,
            'client_id': self.client_id,
            'client_secret': self.client_secret,
        }
        headers = {
            'Content-type': 'application/x-www-form-urlencoded'
        }

        # This is the raw REST API call to Webex to exchange the refresh token
        response = requests.post(url, headers=headers, data=payload)
        
        if response.status_code == 200:
            token_data = response.json()
            self.access_token = token_data['access_token']
            
            # Calculate expiration time (subtract 60 seconds for safety buffer)
            self.expires_at = time.time() + token_data['expires_in'] - 60
            
            # If a new refresh token is provided, update it
            if 'refresh_token' in token_data:
                self.refresh_token_val = token_data['refresh_token']
                set_key(self.env_path, "REFRESH_TOKEN", self.refresh_token_val)

            # Update the access token in the .env file for persistence
            set_key(self.env_path, "ACCESS_TOKEN", self.access_token)
            
            log.info("Token refreshed successfully.")
            return self.access_token
        else:
            raise Exception(f"Failed to refresh token: {response.status_code} - {response.text}")
