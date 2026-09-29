# models.py
# 「当前生效的模型」管理。用户激活过的服务商会落在这里，出稿时按生效项调用。
# 密钥统一存 .env（由 config 管），这里只存接口地址、模型名、用哪个密钥变量。
import json, os
import httpx

import providers

DATA = os.path.join(os.path.dirname(__file__), "data", "models.json")

# 首次启动的默认清单：DeepSeek 官方新模型名
# ⚠️ DeepSeek 已于 2026-07-24 停用 deepseek-chat / deepseek-reasoner，
#    现在对应 deepseek-flash（快、便宜）和 deepseek-v4-pro（强、贵 3 倍）。
DEFAULT_MODELS = [
    {
        "id": "deepseek", "label": "DeepSeek 深度求索 · deepseek-flash", "provider": "deepseek",
        "api_base": "https://api.deepseek.com/chat/completions", "key_env": "DEEPSEEK_API_KEY",
        "model_name": "deepseek-flash", "active": True,
    },
]

# 已经停用的老模型名 → 新名。启动时自动迁移，免得用户拿旧名字调不通。
LEGACY_MODEL_NAMES = {
    "deepseek-chat": "deepseek-flash",
    "deepseek-reasoner": "deepseek-v4-pro",
}


def _read():
    if not os.path.exists(DATA):
        _write([dict(m) for m in DEFAULT_MODELS])
        return [dict(m) for m in DEFAULT_MODELS]
    try:
        return json.load(open(DATA, encoding="utf-8"))
    except Exception:
        return [dict(m) for m in DEFAULT_MODELS]


def _write(arr):
    json.dump(arr, open(DATA, "w", encoding="utf-8"), ensure_ascii=False, indent=2)


def migrate():
    """把老的模型条目升级成「按服务商一条」的形态，返回是否改动过。"""
    arr = _read()
    changed, out = False, []
    for m in arr:
        pid = m.get("provider") if m.get("provider") in {p["key"] for p in providers.list_providers()} else None
        # 老的 deepseek-chat / deepseek-reasoner → 归到 deepseek 服务商名下
        if m.get("model_name") in LEGACY_MODEL_NAMES or m.get("id") in LEGACY_MODEL_NAMES:
            m["id"] = "deepseek"
            m["provider"] = "deepseek"
            m["key_env"] = "DEEPSEEK_API_KEY"
            m["model_name"] = LEGACY_MODEL_NAMES.get(m.get("model_name") or m.get("id"), "deepseek-flash")
            m["label"] = f"DeepSeek 深度求索 · {m['model_name']}"
            changed = True
        elif not pid:
            # 认不出服务商的（用户手加的），统一标成 custom，保留原值不动
            m["provider"] = "custom"
            changed = True
        # 同 id 去重，保留 active 的那条
        dup = next((x for x in out if x["id"] == m["id"]), None)
        if dup:
            dup["active"] = dup.get("active") or m.get("active")
            changed = True
            continue
        out.append(m)
    if not any(x.get("active") for x in out) and out:
        out[0]["active"] = True
    if changed:
        _write(out)
    return changed


def list_models():
    return _read()


def get_active():
    arr = _read()
    return next((m for m in arr if m.get("active")), arr[0] if arr else None)


def set_active(mid):
    arr = _read()
    if not any(m["id"] == mid for m in arr):
        return {"error": "not_found", "message": f"模型 {mid} 不存在"}
    for m in arr:
        m["active"] = (m["id"] == mid)
    _write(arr)
    return {"ok": True, "active": mid}


def activate_provider(pid, model_name="", api_base="", key=""):
    """一键配置：选服务商 → 填 Key → 自动建模型并设为生效。"""
    import config
    p = providers.get(pid)
    if not p:
        return {"error": "unknown_provider", "message": f"未知服务商 {pid}"}
    model_name = (model_name or providers.default_model(pid) or "").strip()
    api_base = (api_base or p["api_base"] or "").strip()
    if not model_name:
        return {"error": "no_model", "message": "请填写模型名"}
    if not api_base:
        return {"error": "no_base", "message": "请填写接口地址"}
    # 填了新 Key 就写入 .env（留空表示沿用已存的，不清空）
    if key:
        config.save_secret(p["key_env"], key)

    arr = _read()
    item = next((x for x in arr if x["id"] == pid), None)
    if item:
        item.update({"api_base": api_base, "model_name": model_name, "key_env": p["key_env"],
                     "provider": pid, "label": f"{p['name']} · {model_name}"})
    else:
        item = {"id": pid, "label": f"{p['name']} · {model_name}", "provider": pid,
                "api_base": api_base, "key_env": p["key_env"], "model_name": model_name}
        arr.append(item)
    for x in arr:
        x["active"] = (x["id"] == pid)
    _write(arr)
    return {"ok": True, "model": item,
            "key_configured": bool(os.getenv(p["key_env"], "") or key)}


def add_model(m):
    """手动添加一个自定义模型。"""
    arr = _read()
    mid = (m.get("id") or m.get("model_name") or "").strip()
    if not mid:
        return {"error": "no_id", "message": "请填写模型标识"}
    if any(x["id"] == mid for x in arr):
        return {"error": "dup", "message": f"已存在 id={mid}"}
    item = {
        "id": mid, "label": m.get("label") or mid, "provider": m.get("provider", "custom"),
        "api_base": m.get("api_base", ""), "key_env": m.get("key_env", "CUSTOM_API_KEY"),
        "model_name": m.get("model_name", mid), "active": bool(m.get("active", False)),
    }
    arr.append(item)
    _write(arr)
    return item


def delete_model(mid):
    arr = [m for m in _read() if m["id"] != mid]
    if not any(m["active"] for m in arr) and arr:
        arr[0]["active"] = True
    _write(arr)
    return {"ok": True}


def resolve(model_id=None):
    """返回调用要用的信息：{id, api_base, api_key, model_name, provider, key_env}。"""
    arr = _read()
    m = next((x for x in arr if x["id"] == model_id), None) if model_id else get_active()
    if not m:
        return None
    return {
        "id": m["id"], "api_base": m["api_base"], "api_key": os.getenv(m["key_env"], "") or "",
        "model_name": m["model_name"], "provider": m.get("provider", ""), "key_env": m["key_env"],
    }


def test_model(mid=None):
    """测试连通性，返回 {ok, message}。"""
    info = resolve(mid)
    if not info:
        return {"ok": False, "message": "还没有可用模型，请先在「API 密钥」页选一个服务商"}
    if not info["api_key"] and info.get("provider") not in ("ollama", "lmstudio"):
        return {"ok": False, "message": f"还没填密钥（{info['key_env']}）"}
    if not info["api_base"]:
        return {"ok": False, "message": "接口地址为空"}
    try:
        headers = {"Content-Type": "application/json"}
        if info["api_key"]:
            headers["Authorization"] = f"Bearer {info['api_key']}"
        resp = httpx.post(info["api_base"], headers=headers,
                          json={"model": info["model_name"],
                                "messages": [{"role": "user", "content": "回复 ok 即可"}], "max_tokens": 64},
                          timeout=25)
        if resp.status_code != 200:
            return {"ok": False, "message": f"HTTP {resp.status_code}：{resp.text[:240]}"}
        # ⚠️ 有的厂商（智谱就是）把「404 / 鉴权失败」也包在 HTTP 200 里返回，
        #    只看状态码会报出假的「连接成功」。必须 body 里真的有 choices 才算通。
        try:
            data = resp.json()
        except Exception:
            data = None
        if not isinstance(data, dict) or "choices" not in data:
            err = data.get("error") if isinstance(data, dict) else None
            msg = (err.get("message") or str(err)) if isinstance(err, dict) else err
            if not msg:
                msg = (data.get("msg") if isinstance(data, dict) else None) or resp.text[:200]
            return {"ok": False, "message": f"接口没返回有效回复：{msg}（检查接口地址和模型名）"}
        return {"ok": True, "message": f"连接成功（{info['model_name']}）"}
    except Exception as e:
        return {"ok": False, "message": f"连不上（{type(e).__name__}）：{str(e)[:200]}"}
