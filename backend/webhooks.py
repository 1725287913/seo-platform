# webhooks.py
# 接口 / Webhook：事件发生时把数据 POST 到自定义地址，方便以后接自己的发布通道、飞书通知等。
# 事件：article_created(存稿) / article_pushed(百度推送成功) / pipeline_done(流水线跑完)
import json, os, time, uuid
import httpx

DATA = os.path.join(os.path.dirname(__file__), "data", "webhooks.json")

EVENTS = {
    "article_created": "文章保存时",
    "article_pushed": "百度推送成功时",
    "pipeline_done": "一键流水线完成时",
    "all": "全部事件",
}


def _read():
    if not os.path.exists(DATA):
        json.dump([], open(DATA, "w", encoding="utf-8"))
        return []
    return json.load(open(DATA, encoding="utf-8"))


def _write(arr):
    json.dump(arr, open(DATA, "w", encoding="utf-8"), ensure_ascii=False, indent=2)


def list_hooks():
    return _read()


def add_hook(h: dict):
    arr = _read()
    url = (h.get("url") or "").strip()
    if not url.startswith("http"):
        return {"error": "bad_url", "message": "地址需以 http/https 开头"}
    item = {
        "id": str(uuid.uuid4())[:8],
        "name": h.get("name") or url[:24],
        "url": url,
        "event": h.get("event") or "all",
        "enabled": bool(h.get("enabled", True)),
        "last_status": "",           # 最近一次调用结果
        "last_time": "",
        "created_at": time.strftime("%Y-%m-%d %H:%M"),
    }
    arr.insert(0, item)
    _write(arr)
    return item


def toggle_hook(hid: str):
    arr = _read()
    for x in arr:
        if x.get("id") == hid:
            x["enabled"] = not x.get("enabled", True)
    _write(arr)
    return {"ok": True}


def del_hook(hid: str):
    _write([x for x in _read() if x.get("id") != hid])
    return {"ok": True}


def fire(event: str, payload: dict):
    """触发事件：给所有订阅该事件且启用的地址发 POST。返回每个地址的结果。"""
    results = []
    arr = _read()
    changed = False
    for h in arr:
        if not h.get("enabled"):
            continue
        if h.get("event") not in (event, "all"):
            continue
        body = {"event": event, "time": time.strftime("%Y-%m-%d %H:%M:%S"), "data": payload}
        try:
            r = httpx.post(h["url"], json=body, timeout=15)
            status = f"HTTP {r.status_code}"
            ok = r.status_code < 400
        except Exception as e:
            status = f"失败：{str(e)[:60]}"
            ok = False
        h["last_status"] = status
        h["last_time"] = time.strftime("%Y-%m-%d %H:%M")
        changed = True
        results.append({"name": h["name"], "url": h["url"], "ok": ok, "status": status})
    if changed:
        _write(arr)
    return results


def test_hook(hid: str):
    """测试单个地址连通性（发一条 ping）。"""
    h = next((x for x in _read() if x.get("id") == hid), None)
    if not h:
        return {"ok": False, "message": "该地址不存在"}
    try:
        r = httpx.post(h["url"], json={"event": "test", "time": time.strftime("%Y-%m-%d %H:%M:%S"),
                                       "data": {"message": "来自 SEO 矩阵平台的测试"}}, timeout=15)
        return {"ok": r.status_code < 400, "message": f"HTTP {r.status_code}"}
    except Exception as e:
        return {"ok": False, "message": str(e)}
