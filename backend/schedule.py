# schedule.py
# 定时发布：合规范围内不做「自动代发」（违规封号），只记录计划 + 到点提醒（半自动）。
import json, os, uuid
import datetime

DATA = os.path.join(os.path.dirname(__file__), "data", "schedule.json")
if not os.path.exists(DATA):
    json.dump([], open(DATA, "w", encoding="utf-8"))


def list_schedule(status=None):
    arr = json.load(open(DATA, encoding="utf-8"))
    if status:
        arr = [s for s in arr if s["status"] == status]
    return arr


def add_schedule(article_id, platform, account="", planned_at="", note=""):
    arr = list_schedule()
    item = {"id": str(uuid.uuid4())[:8], "article_id": article_id,
            "platform": platform, "account": account,
            "planned_at": planned_at, "status": "pending", "note": note,
            "created_at": _now()}
    arr.append(item)
    json.dump(arr, open(DATA, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
    return item


def done_schedule(sid):
    arr = list_schedule()
    for s in arr:
        if s["id"] == sid:
            s["status"] = "done"
    json.dump(arr, open(DATA, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
    return {"ok": True}


def del_schedule(sid):
    arr = [s for s in list_schedule() if s["id"] != sid]
    json.dump(arr, open(DATA, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
    return {"ok": True}


def due_list():
    """返回已到点（plan_at <= 现在）且未完成的计划，供『待发布提醒』。"""
    now = datetime.datetime.now()
    out = []
    for s in list_schedule("pending"):
        try:
            t = datetime.datetime.strptime(s["planned_at"], "%Y-%m-%dT%H:%M")
        except Exception:
            continue
        if t <= now:
            out.append(s)
    return out


def _now():
    return datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
