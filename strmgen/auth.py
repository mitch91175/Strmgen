
import requests
from typing import Optional
from config import config

API_SESSION = requests.Session()

def get_access_token() -> Optional[str]:
    if not config.token_url:
        raise ValueError("Missing 'token_url'")
    url = f"{config.api_base}/{config.token_url.lstrip('/')}"
    if not config.username or not config.password:
        raise ValueError("Missing username/password in config")
    try:
        r = API_SESSION.post(
            url,
            json={"username": config.username, "password": config.password},
            timeout=10
        )
        r.raise_for_status()
        tokens = r.json()
        config.access = tokens.get("access")
        config.refresh = tokens.get("refresh")
        return config.access
    except requests.RequestException:
        return None

def refresh_access_token_if_needed() -> Optional[str]:
    access = config.access
    if not access:
        return get_access_token()
    headers = {"Authorization": f"Bearer {access}"}
    try:
        r = API_SESSION.get(f"{config.api_base}/api/core/settings/", headers=headers, timeout=10)
        if r.status_code == 401:
            return get_access_token()
        return access
    except requests.RequestException:
        return get_access_token()
