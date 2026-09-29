# personas.py
# 账号定位（人设）：给每个平台/账号设定受众、语气、卖点、禁用表达，出稿时自动叠加进 prompt。
# 作用：同一平台多个账号能写出不同人设的稿子（比如「官方号」和「个人探店号」）。
import json, os, time, uuid

DATA = os.path.join(os.path.dirname(__file__), "data", "personas.json")


def _read():
    if not os.path.exists(DATA):
        json.dump([], open(DATA, "w", encoding="utf-8"))
        return []
    return json.load(open(DATA, encoding="utf-8"))


def _write(arr):
    json.dump(arr, open(DATA, "w", encoding="utf-8"), ensure_ascii=False, indent=2)


def list_personas():
    return _read()


def add_persona(p: dict):
    arr = _read()
    name = (p.get("name") or "").strip()
    if not name:
        return {"error": "empty", "message": "账号名称不能为空"}
    item = {
        "id": str(uuid.uuid4())[:8],
        "platform": p.get("platform") or "baidu",
        "name": name,
        "audience": p.get("audience", ""),      # 受众是谁
        "tone": p.get("tone", ""),              # 语气风格
        "selling": p.get("selling", ""),        # 主推卖点/业务
        "taboo": p.get("taboo", ""),            # 禁用表达/不可提内容
        "extra": p.get("extra", ""),            # 其它要求（自由补充）
        "created_at": time.strftime("%Y-%m-%d %H:%M"),
    }
    arr.insert(0, item)
    _write(arr)
    return item


def update_persona(pid: str, patch: dict):
    arr = _read()
    for x in arr:
        if x.get("id") == pid:
            for f in ("platform", "name", "audience", "tone", "selling", "taboo", "extra"):
                if f in patch and patch[f] is not None:
                    x[f] = patch[f]
    _write(arr)
    return {"ok": True}


def del_persona(pid: str):
    _write([x for x in _read() if x.get("id") != pid])
    return {"ok": True}


def pick(platform: str, account: str = ""):
    """按平台（可指定账号名）挑一个人设：账号名匹配优先，否则该平台第一个。"""
    arr = [x for x in _read() if x.get("platform") == platform]
    if not arr:
        return None
    if account:
        for x in arr:
            if x.get("name") == account:
                return x
    return arr[0]


def build_prompt(platform: str, account: str = ""):
    """生成要追加到 system 里的人设指令；没人设则返回空串。"""
    p = pick(platform, account)
    if not p:
        return ""
    lines = [f"【账号人设】你正在为账号「{p['name']}」撰稿。"]
    if p.get("audience"):
        lines.append(f"目标受众：{p['audience']}")
    if p.get("tone"):
        lines.append(f"语气风格：{p['tone']}（全文保持这个人设口吻）")
    if p.get("selling"):
        lines.append(f"要自然带出的卖点/业务：{p['selling']}")
    if p.get("taboo"):
        lines.append(f"绝对不能出现的内容/表达：{p['taboo']}")
    if p.get("extra"):
        lines.append(f"其它要求：{p['extra']}")
    return "\n".join(lines)
