
import fnmatch
import requests
from pathlib import Path
from config import config, load_skip_cache, save_skip_cache
from auth import refresh_access_token_if_needed
from streams import fetch_streams_by_group_name
from processors import process_24_7, process_movie, process_tv
from utils import is_tv_show
from log import setup_logger
logger = setup_logger(__name__)

def main():
    load_skip_cache()
    token = refresh_access_token_if_needed()
    headers = {"Authorization": f"Bearer {token}"} if token else {}

    groups = requests.Session().get(f"{config.api_base}/api/channels/streams/groups/", headers=headers, timeout=10).json()
    patterns = config.channel_groups

    for grp in filter(lambda g: any(fnmatch.fnmatch(g, p) for p in patterns), groups):
        logger.info("🔍 Processing group: %s", grp)
        streams = fetch_streams_by_group_name(grp, headers)
        for s in streams:
            base = config.stream_base_url if config.stream_base_url.startswith("http") else f"{config.api_base}/{config.stream_base_url}"
            url = base + s["stream_hash"]
            sid = s["id"]
            name = s["name"]

            if "24/7" in grp or "24-7" in grp:
                process_24_7(name, sid, Path(config.output_root), grp, headers, url)
            elif is_tv_show(name):
                process_tv(name, sid, Path(config.output_root), grp, headers, url)
            elif "Movies" in grp:
                process_movie(name, sid, Path(config.output_root), grp, headers, url)
            # else:
            #     from .utils import target_folder, clean_name
            #     fld = target_folder(Path(config.output_root), grp)
            #     from .streams import write_strm_file
            #     write_strm_file(fld / f"{clean_name(name)}.strm", sid, headers, url)

    save_skip_cache()

if __name__ == '__main__':
    main()
