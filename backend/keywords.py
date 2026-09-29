# keywords.py
# 关键词 / 产品库：管理要做的词（分组、搜索意图、难度、备注），可作为批量创作的输入源。
# 支持 AI 拓展：给一个种子词，让模型给出相关长尾词，勾选后入库。
import json, os, re, time, uuid
import httpx
import models

DATA = os.path.join(os.path.dirname(__file__), "data", "keywords.json")

# 搜索意图分类（做 SEO 时决定写什么类型的内容）
INTENTS = ["信息型", "导航型", "交易型", "本地型"]


def _read():
    if not os.path.exists(DATA):
        json.dump([], open(DATA, "w", encoding="utf-8"))
        return []
    return json.load(open(DATA, encoding="utf-8"))


def _write(arr):
    json.dump(arr, open(DATA, "w", encoding="utf-8"), ensure_ascii=False, indent=2)


def list_keywords():
    return _read()


def add_keyword(k: dict):
    """新增关键词；重复词直接返回已存在的（避免库里堆重复项）。"""
    arr = _read()
    kw = (k.get("keyword") or "").strip()
    if not kw:
        return {"error": "empty", "message": "关键词不能为空"}
    if any(x.get("keyword") == kw for x in arr):
        return {"error": "dup", "message": f"「{kw}」已在词库中"}
    item = {
        "id": str(uuid.uuid4())[:8],
        "keyword": kw,
        "group": k.get("group") or "默认分组",
        "intent": k.get("intent") or "信息型",
        "difficulty": int(k.get("difficulty") or 3),   # 1 好做 ~ 5 难做
        "note": k.get("note", ""),
        "created_at": time.strftime("%Y-%m-%d %H:%M"),
    }
    arr.insert(0, item)
    _write(arr)
    return item


def update_keyword(kid: str, patch: dict):
    arr = _read()
    for x in arr:
        if x.get("id") == kid:
            for f in ("keyword", "group", "intent", "note"):
                if f in patch and patch[f] is not None:
                    x[f] = patch[f]
            if patch.get("difficulty") is not None:
                x["difficulty"] = int(patch["difficulty"])
    _write(arr)
    return {"ok": True}


def del_keyword(kid: str):
    _write([x for x in _read() if x.get("id") != kid])
    return {"ok": True}


def groups():
    """返回全部分组名（含每个分组的数量），给前端下拉用。"""
    out = {}
    for x in _read():
        g = x.get("group") or "默认分组"
        out[g] = out.get(g, 0) + 1
    return out


def expand(seed: str, model_id: str = None, n: int = 10):
    """AI 拓展：基于种子词生成相关长尾词（不落库，前端勾选后再入库）。
    让模型按「关键词|意图|难度」的简单分隔格式输出，避免 JSON 解析踩坑。
    """
    seed = (seed or "").strip()
    if not seed:
        return {"error": "empty", "message": "请先输入种子词"}
    info = models.resolve(model_id)
    if not info:
        return {"error": "no_model", "message": "没有可用模型，请先在「模型中心」启用一个"}
    if not info["api_key"]:
        return {"error": "missing_key",
                "message": f"模型 {info['model_name']} 的密钥（{info['key_env']}）未配置"}

    system = (
        "你是中文 SEO 关键词分析师。根据用户给的种子词，输出相关搜索词（长尾词）。"
        f"严格每行一条，格式：关键词|意图|难度。意图只能从 {INTENTS} 里选，难度是 1-5 的数字。"
        "不要序号、不要解释、不要表头，只输出数据行。"
    )
    try:
        resp = httpx.post(
            info["api_base"],
            headers={"Authorization": f"Bearer {info['api_key']}", "Content-Type": "application/json"},
            json={"model": info["model_name"],
                  "messages": [{"role": "system", "content": system},
                               {"role": "user", "content": f"种子词：{seed}\n输出 {n} 条"}],
                  "temperature": 0.9},
            timeout=60,
        )
        data = resp.json()
        if "error" in data:
            return {"error": "api_error", "message": data.get("error", {}).get("message", str(data))}
        text = data["choices"][0]["message"]["content"]
        items = []
        for line in text.split("\n"):
            line = re.sub(r"^\s*[\d]+[.、)]\s*", "", line).strip()   # 去掉可能的序号
            if not line:
                continue
            parts = [p.strip() for p in line.split("|")]
            kw = parts[0]
            if not kw:
                continue
            intent = parts[1] if len(parts) > 1 and parts[1] in INTENTS else "信息型"
            diff = 3
            if len(parts) > 2 and parts[2][:1].isdigit():
                diff = max(1, min(5, int(parts[2][0])))
            items.append({"keyword": kw, "intent": intent, "difficulty": diff})
        return {"keywords": items[:n], "seed": seed}
    except Exception as e:
        return {"error": "request_failed", "message": str(e)}
