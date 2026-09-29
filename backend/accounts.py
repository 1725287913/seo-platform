# accounts.py
# 多账号矩阵：每个平台可登记多个账号（用于半自动发布时选择目标账号）
import json, os, uuid

DATA = os.path.join(os.path.dirname(__file__), "data", "accounts.json")
if not os.path.exists(DATA):
    json.dump([], open(DATA, "w", encoding="utf-8"))


def list_accounts(platform=None):
    arr = json.load(open(DATA, encoding="utf-8"))
    if platform:
        arr = [a for a in arr if a["platform"] == platform]
    return arr


def _blank_preset():
    """发布预设：这个账号发文时默认带上的东西，省得每次重填。"""
    return {"tags": "", "category": "", "visibility": "", "cover": "", "extra": ""}


def add_account(platform, name, url="", note="", is_default=False, preset=None):
    arr = list_accounts()
    # 若设为默认，先清掉同平台其它默认
    if is_default:
        for a in arr:
            if a["platform"] == platform:
                a["is_default"] = False
    item = {"id": str(uuid.uuid4())[:8], "platform": platform,
            "name": name, "url": url, "note": note, "is_default": bool(is_default),
            "preset": {**_blank_preset(), **(preset or {})}}
    # 该平台第一个账号自动成为默认
    if not any(a["platform"] == platform for a in arr):
        item["is_default"] = True
    arr.append(item)
    json.dump(arr, open(DATA, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
    return item


def update_account(aid, d: dict):
    """改账号信息或发布预设。"""
    arr = list_accounts()
    for a in arr:
        if a["id"] == aid:
            for k in ("name", "url", "note"):
                if d.get(k) is not None:
                    a[k] = d[k]
            if isinstance(d.get("preset"), dict):
                a["preset"] = {**a.get("preset", _blank_preset()), **d["preset"]}
            json.dump(arr, open(DATA, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
            return a
    return {"error": "not_found", "message": "账号不存在"}


def get_preset(platform, name):
    """出稿/发布时按平台+账号名取预设，取不到返回空。"""
    for a in list_accounts(platform):
        if a["name"] == name:
            return a.get("preset") or _blank_preset()
    return _blank_preset()


def set_default(aid):
    """把某账号设为所在平台的默认账号（同平台其余取消默认）。"""
    arr = list_accounts()
    target = next((a for a in arr if a["id"] == aid), None)
    if not target:
        return {"error": "not_found", "message": "账号不存在"}
    for a in arr:
        a["is_default"] = (a["id"] == aid)
    json.dump(arr, open(DATA, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
    return {"ok": True}


def del_account(aid):
    arr = [a for a in list_accounts() if a["id"] != aid]
    # 若删掉的是默认，把同平台第一个设为默认
    deleted = next((a for a in list_accounts() if a["id"] == aid), None)
    if deleted and deleted.get("is_default"):
        for a in arr:
            if a["platform"] == deleted["platform"]:
                a["is_default"] = True
                break
    json.dump(arr, open(DATA, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
    return {"ok": True}
