
import requests

from pathlib import Path
from typing import List
from urllib.parse import quote_plus
from config import config
from utils import safe_mkdir
from utils import setup_logger
logger = setup_logger(__name__)

API_SESSION = requests.Session()

def fetch_streams_by_group_name(group_name: str, headers: dict) -> List[dict]:
    out, page = [], 1
    enc = quote_plus(group_name)
    while True:
        url = f"{config.api_base}/api/channels/streams/?page={page}&page_size=250&ordering=name&channel_group={enc}"
        r = API_SESSION.get(url, headers=headers, timeout=10)
        if not r.ok:
            logger.error("[STRM] ❌ Error fetching streams for group '%s': %d", group_name, r.status_code)
            break
        data = r.json()
        out.extend(data.get("results", []))
        if not data.get("next"):
            break
        page += 1
    return out

    
def is_stream_alive(stream_id: int, headers: dict, timeout: int = 5) -> bool:
    if config.skip_stream_check:
        return True
    try:
        r = API_SESSION.get(f"{config.api_base}/api/channels/streams/{stream_id}/", headers=headers, timeout=timeout)
        r.raise_for_status()
        url = r.json().get("url")
        return bool(url and API_SESSION.head(url, timeout=timeout).ok)
    except:
        return False

def write_strm_file(path: Path, stream_id: int, headers: dict, stream_url: str) -> bool:
    if path.exists():
        logger.info("[STRM] ⚠️ .strm already exists, reusing: %s", path)
        return True
    if not is_stream_alive(stream_id, headers):
        logger.warning("[STRM] ⚠️ Stream #%d unreachable, skipping", stream_id)
        return False
    safe_mkdir(path.parent)
    path.write_text(stream_url, encoding="utf-8")
    logger.info("[STRM] ✅ Wrote .strm: %s → %s", path, stream_url)
    return True


