# presets.py
# 写作配置预设：把一整套写作配置（风格/受众/字数/语言/配图…）存成一个命名预设，
# 下次一键载入，不同客户/不同行业各存一套，不用每次重新调。
import json, os, time, uuid

DATA = os.path.join(os.path.dirname(__file__), "data", "presets.json")


def _read():
    if not os.path.exists(DATA):
        json.dump([], open(DATA, "w", encoding="utf-8"))
        return []
    try:
        return json.load(open(DATA, encoding="utf-8"))
    except Exception:
        return []


def _write(arr):
    json.dump(arr, open(DATA, "w", encoding="utf-8"), ensure_ascii=False, indent=2)


def list_presets():
    return _read()


def get_preset(pid):
    return next((p for p in _read() if p.get("id") == pid), None)


def add_preset(name, config, platform=""):
    """保存一套写作配置。同名则覆盖，避免存出一堆重名预设。"""
    name = (name or "").strip()
    if not name:
        return {"error": "empty", "message": "预设名不能为空"}
    arr = _read()
    item = {
        "id": "pre-" + str(uuid.uuid4())[:6],
        "name": name,
        "platform": platform or "",
        "config": config or {},
        "updated_at": time.strftime("%Y-%m-%d %H:%M"),
    }
    old = next((p for p in arr if p.get("name") == name), None)
    if old:
        old.update({"config": item["config"], "updated_at": item["updated_at"],
                    "platform": item["platform"]})
        _write(arr)
        return old
    arr.insert(0, item)
    _write(arr)
    return item


def del_preset(pid):
    _write([p for p in _read() if p.get("id") != pid])
    return {"ok": True}
