# config.py
# 负责读写配置：站点、百度 token、DeepSeek key 等
# 配置存在 backend/.env（不进版本库），用 python-dotenv 加载
import os
from dotenv import load_dotenv, set_key

import providers

ENV_PATH = os.path.join(os.path.dirname(__file__), ".env")
# 首次加载（.env 不存在也不报错）
load_dotenv(ENV_PATH, override=False)

# 配置项默认值，新增平台/配置只要在这里加 key
DEFAULTS = {
    "BAIDU_SITE": "",          # 百度搜索资源平台里添加的已备案站点
    "BAIDU_TOKEN": "",         # 百度主动推送 token
    "IMAGE_API_BASE": "",      # OpenAI 兼容图像接口地址，留空则只生成提示词
    "IMAGE_API_KEY": "",       # 图像接口 key
    "IMAGE_MODEL": "default",  # 图像模型名
}
# 每个 AI 服务商的密钥变量（从 providers 动态生成，加服务商不用改这里）
for _p in providers.list_providers():
    DEFAULTS.setdefault(_p["key_env"], "")

# 属于密钥的字段：绝不向前端明文回显，只返回“是否已配置”
SECRET_KEYS = {"BAIDU_TOKEN", "IMAGE_API_KEY"} | providers.key_envs()

import httpx

def test_connection(kind: str, model: str = "", api_base: str = "", key: str = ""):
    """测试密钥/接口是否可用，返回 {ok, message}。

    kind 传服务商 key（deepseek/kimi/oilama…）或 "image"。
    model / api_base / key 传了就用传的（「自定义」服务商和改过模型名时用）。
    """
    if kind == "image":
        key = key or os.getenv("IMAGE_API_KEY", "")
        url = api_base or os.getenv("IMAGE_API_BASE", "")
        if not url:
            return {"ok": False, "message": "尚未配置图像接口地址，仅生成提示词即可"}
        payload = {"model": model or os.getenv("IMAGE_MODEL", "default"), "prompt": "test", "n": 1}
        return _post(url, key, payload, "图像接口")

    p = providers.get(kind)
    if not p:
        return {"ok": False, "message": f"未知服务商 {kind}"}
    url = api_base or p["api_base"]
    model = model or providers.default_model(kind)
    key = key or os.getenv(p["key_env"], "")
    # 本地服务（Ollama/LM Studio）不要 Key，不校验
    if not key and p["group"] != "local":
        return {"ok": False, "message": f"还没填 {p['name']} 的 API Key"}
    if not url:
        return {"ok": False, "message": "接口地址为空，请填写"}
    payload = {"model": model, "messages": [{"role": "user", "content": "回复 ok 即可"}], "max_tokens": 5}
    return _post(url, key, payload, f"{p['name']} / {model}")


def _post(url, key, payload, label):
    headers = {"Content-Type": "application/json"}
    if key:
        headers["Authorization"] = f"Bearer {key}"
    try:
        resp = httpx.post(url, headers=headers, json=payload, timeout=25)
        if resp.status_code == 200:
            return {"ok": True, "message": f"{label} 连接成功"}
        # 把服务商的报错原样带回去，方便用户判断是 Key 错还是模型名过期
        return {"ok": False, "message": f"HTTP {resp.status_code}：{resp.text[:240]}"}
    except Exception as e:
        return {"ok": False, "message": f"连不上（{type(e).__name__}）：{str(e)[:200]}"}

def get_config(mask_secrets=True):
    # mask_secrets=True  → 给前端展示，密钥只回“***已配置***”
    # mask_secrets=False → 后端内部真正调用时用（必须拿真实值！）
    out = {}
    for k in DEFAULTS:
        v = os.getenv(k, DEFAULTS[k]) or ""
        if k in SECRET_KEYS and mask_secrets:
            # 脱敏占位，绝不返回明文
            out[k] = "***已配置***" if v else ""
            out[k + "_configured"] = bool(v)
        else:
            out[k] = v
    return out

def save_secret(k: str, v: str):
    """单独写一个密钥到 .env，并立即生效（不用重启服务）。空值不写。"""
    if k not in DEFAULTS or not v:
        return False
    set_key(ENV_PATH, k, str(v))
    os.environ[k] = str(v)
    return True


def save_config(data: dict):
    # 只保存白名单内的 key，避免把奇怪字段写进 .env
    # 规则：空值、或仍是脱敏占位串 = 用户没改密钥，跳过不覆盖
    for k, v in data.items():
        if k not in DEFAULTS:
            continue
        if v in (None, "", "***已配置***"):
            continue
        set_key(ENV_PATH, k, str(v))
    load_dotenv(ENV_PATH, override=True)
    return get_config()
