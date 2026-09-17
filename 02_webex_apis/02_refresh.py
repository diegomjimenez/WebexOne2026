"""
Webex One 2026 - Troubleshoot and Manage Your Organization with an AI Assistant

- Diego Manuel Jimenez Moreno
- Mo Eyad Musallam

Test the TokenManager class to refresh the Service App token.
"""

import logging
from token_manager import TokenManager

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

if __name__ == "__main__":
    print("Testing TokenManager...")
    manager = TokenManager()
    
    # Force a refresh by calling refresh() directly instead of get_token()
    new_token = manager.refresh()
    
    print("\n--- Token Refreshed ---")
    print(f"New Access Token: {new_token[:15]}... (truncated)")
    print("\nYour .env file has been automatically updated!")
