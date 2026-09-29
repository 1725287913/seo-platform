# topics.py
# 热点选题：管理选题库（JSON 存储）+ 可选 AI 推荐相关热点
import json, os, uuid
import httpx

DATA = os.path.join(os.path.dirname(__file__), "data", "topics.json")

if not os.path.exists(DATA):
    json.dump([], open(DATA, "w", encoding="utf-8"))


def list_topics():
    return json.load(open(DATA, encoding="utf-8"))


def add_topic(keyword, source="", note=""):
    arr = list_topics()
    item = {"id": str(uuid.uuid4())[:8], "keyword": keyword,
            "source": source, "note": note, "created_at": _now()}
    arr.insert(0, item)
    json.dump(arr, open(DATA, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
    return item


def del_topic(tid):
    arr = [t for t in list_topics() if t["id"] != tid]
    json.dump(arr, open(DATA, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
    return {"ok": True}


def recommend(seed, api_key="", model="", api_base=""):
    """基于种子词推荐热点选题。不传参就用「当前生效的模型」（跟出稿走同一套配置）。"""
    if not (api_key and api_base and model):
        import models
        info = models.resolve() or {}
        api_key = api_key or info.get("api_key", "")
        api_base = api_base or info.get("api_base", "")
        model = model or info.get("model_name", "")
    if not api_key:
        return {"error": "missing_key", "message": "还没配置 AI 密钥，请到「API 密钥」页选一个服务商并填写"}
    try:
        resp = httpx.post(
            api_base,
            headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
            json={
                "model": model,
                "messages": [
                    {"role": "system", "content": "你是内容选题策划，基于给定领域给出 8 个有流量潜力的中文选题，每行一个，只输出选题标题不要编号和解释。"},
                    {"role": "user", "content": f"领域/种子词：{seed}"},
                ],
                "temperature": 0.9,
            },
            timeout=60,
        )
        data = resp.json()
        if "error" in data:
            return {"error": "api_error", "message": data.get("error", {}).get("message", str(data))}
        text = data["choices"][0]["message"]["content"]
        items = [l.strip().lstrip("0123456789.、- ") for l in text.split("\n") if l.strip()]
        return {"topics": items[:8]}
    except Exception as e:
        return {"error": "request_failed", "message": str(e)}


def _now():
    import datetime
    return datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
