from pathlib import Path

import requests
import tomllib


SECRETS_FILE = Path(".streamlit/secrets.toml")
API_URL = "https://api.hackmd.io/v1/me"


def load_token():
    if not SECRETS_FILE.exists():
        raise FileNotFoundError("Missing .streamlit/secrets.toml")

    secrets = tomllib.loads(SECRETS_FILE.read_text(encoding="utf-8"))
    token = secrets.get("HACKMD_API_TOKEN")

    if not token:
        raise KeyError("HACKMD_API_TOKEN not found in .streamlit/secrets.toml")

    return token


headers = {
    "Authorization": f"Bearer {load_token()}",
    "Accept": "application/json",
}

response = requests.get(API_URL, headers=headers, timeout=30)

print("Status:", response.status_code)
print("Response:", response.text)
