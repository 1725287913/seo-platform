# snippets.py
# 素材库：存随手收集的短素材/灵感/金句/数据片段，写作台可一键填进「真实参考资料」。
# 内容中心和它共享数据，避免素材散落在微信收藏里。
import json, os, time, uuid

DATA = os.path.join(os.path.dirname(__file__), "data", "snippets.json")


def _read():
    if not os.path.exists(DATA):
        json.dump([], open(DATA, "w", encoding="utf-8"))
        return []
    return json.load(open(DATA, encoding="utf-8"))


def _write(arr):
    json.dump(arr, open(DATA, "w", encoding="utf-8"), ensure_ascii=False, indent=2)


def list_snippets(platform: str = "", tag: str = ""):
    arr = _read()
    if platform:
        arr = [x for x in arr if x.get("platform") in (platform, "")]
    if tag:
        arr = [x for x in arr if tag in (x.get("tags") or "")]
    return arr


def add_snippet(s: dict):
    arr = _read()
    content = (s.get("content") or "").strip()
    if not content:
        return {"error": "empty", "message": "素材内容不能为空"}
    item = {
        "id": str(uuid.uuid4())[:8],
        "title": (s.get("title") or content[:16]).strip(),
        "content": content,
        "tags": s.get("tags", ""),
        "platform": s.get("platform", ""),   # 空=通用素材
        "created_at": time.strftime("%Y-%m-%d %H:%M"),
    }
    arr.insert(0, item)
    _write(arr)
    return item


def del_snippet(sid):
    _write([x for x in _read() if x.get("id") != sid])
    return {"ok": True}
