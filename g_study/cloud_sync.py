"""端末をまたいで学習履歴を共有する。"""

from __future__ import annotations

import html
import http.cookiejar
import json
import random
import re
import string
import urllib.error
import urllib.parse
import urllib.request

from .progress import _normalize, load_progress_bytes, progress_bytes

UA = "Mozilla/5.0 GKenteiSync/1.0"
RENTRY = "https://rentry.co"
DPASTE = "https://dpaste.com/api/v2/"
APP_MARK = "gk"


def normalize_sync_id(value: str) -> str:
    text = str(value or "").strip().lower()
    text = text.replace("https://rentry.co/", "").replace("http://rentry.co/", "")
    text = text.strip("/").split("?")[0]
    return re.sub(r"[^a-z0-9-]", "", text)


def _new_sync_id() -> str:
    alphabet = string.ascii_lowercase + string.digits
    return "gk" + "".join(random.choice(alphabet) for _ in range(10))


def _new_edit_code() -> str:
    alphabet = string.ascii_letters + string.digits
    return "".join(random.choice(alphabet) for _ in range(12))


def _open(url: str, data: bytes | None = None, method: str = "GET", headers: dict | None = None, timeout: int = 18):
    h = {"User-Agent": UA, "Accept": "*/*"}
    if headers:
        h.update(headers)
    req = urllib.request.Request(url, data=data, method=method, headers=h)
    return urllib.request.urlopen(req, timeout=timeout)


def _rentry_session():
    jar = http.cookiejar.CookieJar()
    opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(jar))
    req = urllib.request.Request(RENTRY + "/", headers={"User-Agent": UA})
    with opener.open(req, timeout=18) as resp:
        page = resp.read().decode("utf-8", "replace")
    match = re.search(r'name=["\']csrfmiddlewaretoken["\'] value=["\']([^"\']+)', page)
    token = (match.group(1) if match else "") or next((c.value for c in jar if c.name == "csrftoken"), "")
    return opener, token


def _rentry_post(path: str, fields: dict) -> dict:
    opener, token = _rentry_session()
    fields = dict(fields)
    fields["csrfmiddlewaretoken"] = token
    req = urllib.request.Request(
        RENTRY + path,
        data=urllib.parse.urlencode(fields).encode(),
        method="POST",
        headers={
            "User-Agent": UA,
            "Content-Type": "application/x-www-form-urlencoded",
            "Referer": RENTRY + "/",
        },
    )
    try:
        with opener.open(req, timeout=18) as resp:
            return json.loads(resp.read().decode("utf-8", "replace"))
    except urllib.error.HTTPError as exc:
        try:
            return json.loads(exc.read().decode("utf-8", "replace"))
        except Exception:
            raise RuntimeError(f"rentry HTTP {exc.code}") from exc


def _dpaste_create(data: dict) -> str:
    raw = progress_bytes(data).decode("utf-8")
    body = urllib.parse.urlencode(
        {"content": raw, "lexer": "json", "expiry_days": "365", "title": "g-kentei"}
    ).encode()
    with _open(
        DPASTE,
        data=body,
        method="POST",
        headers={"Content-Type": "application/x-www-form-urlencoded", "Accept": "text/plain"},
    ) as resp:
        loc = resp.read().decode("utf-8", "replace").strip()
    ident = loc.rstrip("/").split("/")[-1]
    if not ident:
        raise RuntimeError("dpaste id missing")
    return ident


def _dpaste_fetch(ident: str) -> dict:
    url = f"https://dpaste.com/{ident}.txt"
    with _open(url) as resp:
        return load_progress_bytes(resp.read())


def _pointer(paste_id: str, edit_code: str) -> str:
    return json.dumps({"a": APP_MARK, "p": paste_id, "e": edit_code}, ensure_ascii=False, separators=(",", ":"))


def _parse_pointer(text: str) -> dict | None:
    try:
        data = json.loads(html.unescape(text).strip())
    except json.JSONDecodeError:
        return None
    if not isinstance(data, dict):
        return None
    if data.get("a") != APP_MARK or not data.get("p"):
        return None
    return data


def _rentry_read_pointer(sync_id: str) -> dict | None:
    with _open(f"{RENTRY}/{sync_id}") as resp:
        page = resp.read().decode("utf-8", "replace")
    for pattern in (r"<title>(.*?)</title>", r'name="description" content="([^"]*)"'):
        match = re.search(pattern, page, re.S)
        if not match:
            continue
        found = _parse_pointer(match.group(1))
        if found:
            return found
    return None


def _rentry_create(sync_id: str, edit_code: str, paste_id: str) -> None:
    result = _rentry_post(
        "/api/new",
        {"url": sync_id, "edit_code": edit_code, "text": _pointer(paste_id, edit_code)},
    )
    if str(result.get("status")) != "200":
        raise RuntimeError(result.get("content") or result.get("errors") or "rentry create failed")


def _rentry_edit(sync_id: str, edit_code: str, paste_id: str) -> None:
    result = _rentry_post(
        f"/api/edit/{sync_id}",
        {"edit_code": edit_code, "text": _pointer(paste_id, edit_code)},
    )
    if str(result.get("status")) != "200":
        raise RuntimeError(result.get("content") or result.get("errors") or "rentry edit failed")


def create_sync(data: dict) -> dict:
    payload = _normalize(data)
    last_error = ""
    for _ in range(6):
        sync_id = _new_sync_id()
        edit_code = _new_edit_code()
        payload["sync_id"] = sync_id
        payload["sync_edit"] = edit_code
        try:
            paste_id = _dpaste_create(payload)
            _rentry_create(sync_id, edit_code, paste_id)
            return payload
        except Exception as exc:
            last_error = str(exc)
            continue
    raise RuntimeError(last_error or "引き継ぎコードを発行できませんでした")


def pull_sync(sync_id: str) -> dict | None:
    code = normalize_sync_id(sync_id)
    if not code:
        return None
    pointer = _rentry_read_pointer(code)
    if not pointer:
        return None
    remote = _dpaste_fetch(str(pointer["p"]))
    remote["sync_id"] = code
    remote["sync_edit"] = str(pointer.get("e") or remote.get("sync_edit") or "")
    return _normalize(remote)


def push_sync(data: dict) -> dict:
    payload = _normalize(data)
    sync_id = normalize_sync_id(str(payload.get("sync_id") or ""))
    edit_code = str(payload.get("sync_edit") or "")
    if not sync_id or not edit_code:
        return payload
    payload["sync_id"] = sync_id
    payload["sync_edit"] = edit_code
    paste_id = _dpaste_create(payload)
    _rentry_edit(sync_id, edit_code, paste_id)
    return payload
