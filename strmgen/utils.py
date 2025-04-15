
import re
from pathlib import Path
from typing import List, Any
from config import config
from log import setup_logger
logger = setup_logger(__name__)

def sanitize(name: str) -> str:
    # Replace forbidden characters with a space and normalize spacing
    cleaned = re.sub(r'[<>:"/\\|?*]', " ", name)
    return re.sub(r"\s+", " ", cleaned).strip()

def is_tv_show(name: str) -> bool:
    return bool(re.search(r"[Ss]\d{1,2}[Ee]\d{1,2}", name))

def clean_name(name: str, remove_list: List[str] = None) -> str:
    remove = remove_list if remove_list is not None else config.remove_strings
    for sub in remove:
        name = name.replace(sub, "")
    return sanitize(name).strip()

def safe_mkdir(path: Path) -> None:
    if not path.exists():
        logger.info(f"Creating directory: {path}")
    path.mkdir(parents=True, exist_ok=True)

def target_folder(root: Path, *parts: str) -> Path:
    p = root
    for seg in parts:
        p = p / clean_name(seg)
    safe_mkdir(p)
    return p

def write_if(flag: bool, path: Path, writer_fn: Any, *args) -> None:
    if flag and config.write_nfo_only_if_not_exists and path.exists():
        logger.info("[NFO] ⚠️ Skipped (exists): %s", path)
        return
    writer_fn(*args, path)

def ensure_str(srt_data) -> str:
    if isinstance(srt_data, str):
        return srt_data
    return "\n".join(map(str, srt_data))


# ─── NFO Writers ─────────────────────────────────────────────────────────────
def write_nfo(xml: str, path: Path) -> None:
    path.write_text(xml, encoding="utf-8")
    logger.info(f"[NFO] NFO written: {path}")

def write_movie_nfo(meta: dict, path: Path) -> None:
    xml = (
        f"<movie>\n"
        f"  <title>{meta['title']}</title>\n"
        f"  <year>{meta['release_date'][:4]}</year>\n"
        f"  <plot>{meta['overview']}</plot>\n"
        f"  <rating>{meta['vote_average']}</rating>\n"
        f"  <tmdbid>{meta['id']}</tmdbid>\n"
        f"</movie>"
    )
    write_nfo(xml, path)

def write_tvshow_nfo(meta: dict, path: Path) -> None:
    xml = (
        f"<tvshow>\n"
        f"  <title>{meta['name']}</title>\n"
        f"  <plot>{meta['overview']}</plot>\n"
        f"  <rating>{meta['vote_average']}</rating>\n"
        f"  <tmdbid>{meta['id']}</tmdbid>\n"
        f"</tvshow>"
    )
    write_nfo(xml, path)

def write_episode_nfo(meta: dict, path: Path) -> None:
    xml = (
        f"<episodedetails>\n"
        f"  <title>{meta['name']}</title>\n"
        f"  <season>{meta['season_number']}</season>\n"
        f"  <episode>{meta['episode_number']}</episode>\n"
        f"  <plot>{meta['overview']}</plot>\n"
        f"</episodedetails>"
    )
    write_nfo(xml, path)