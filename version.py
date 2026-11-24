"""NCZ Forge sürüm bilgisi ve güncelleme denetimi."""

from __future__ import annotations
import json
import re
import urllib.request
from typing import Optional, Tuple

__version__ = "1.1.1"
REPO = "evrek4/ncz-forge"
RELEASES_URL = f"https://github.com/{REPO}/releases/latest"
_API_LATEST = f"https://api.github.com/repos/{REPO}/releases/latest"


def _parse(v: str) -> Tuple[int, ...]:
    nums = re.findall(r"\d+", v or "")
    return tuple(int(n) for n in nums[:3]) or (0,)


def is_newer(remote: str, local: str = __version__) -> bool:
    return _parse(remote) > _parse(local)


def check_for_update(timeout: float = 5.0) -> Optional[str]:
    """GitHub'daki son sürüm etiketi bu sürümden yeniyse etiketi döndürür; aksi halde None. Hata olursa sessizce None."""
    try:
        req = urllib.request.Request(_API_LATEST, headers={"Accept": "application/vnd.github+json", "User-Agent": "NCZ-Forge"})
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            tag = json.load(resp).get("tag_name", "")
        return tag if tag and is_newer(tag) else None
    except Exception:
        return None
