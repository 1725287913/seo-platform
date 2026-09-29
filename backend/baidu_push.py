# baidu_push.py
# 百度主动推送（普通收录）API 封装
# 这是「测试期唯一打通的推送通道」，社交平台以后在这里加 handler 即可，不写死
import httpx, json, os, time

PUSH_API = "http://data.zz.baidu.com/urls"
LOG_FILE = os.path.join(os.path.dirname(__file__), "data", "push_log.json")
if not os.path.exists(LOG_FILE):
    json.dump([], open(LOG_FILE, "w", encoding="utf-8"))


def _log(platform, urls, result):
    """把每次推送结果写入 push_log.json，供「数据中心」统计。"""
    try:
        arr = json.load(open(LOG_FILE, encoding="utf-8"))
    except Exception:
        arr = []
    ok = isinstance(result, dict) and ("success" in result) and not result.get("error")
    arr.append({
        "time": time.strftime("%Y-%m-%d %H:%M:%S"),
        "platform": platform,
        "count": len(urls),
        "success": bool(ok),
        "detail": result,
    })
    # 只保留最近 200 条
    json.dump(arr[-200:], open(LOG_FILE, "w", encoding="utf-8"), ensure_ascii=False, indent=2)


def get_log():
    try:
        return json.load(open(LOG_FILE, encoding="utf-8"))
    except Exception:
        return []

def push_baidu(site: str, token: str, urls: list):
    """把 urls（每行一个）推送给百度。
    返回百度原始 JSON，例如成功 {"success":2,...} 或失败 {"error":401,...}
    """
    if not site or not token:
        return {"error": "missing_config",
                "message": "缺少 BAIDU_SITE 或 BAIDU_TOKEN，请先在「站点配置」填写"}
    if not urls:
        return {"error": "empty", "message": "没有要推送的 URL"}

    # 百度要求 body 是纯文本、URL 用换行分隔（不是 JSON）
    urls_text = "\n".join(urls)
    try:
        resp = httpx.post(
            PUSH_API,
            params={"site": site, "token": token},
            data=urls_text,
            headers={"Content-Type": "text/plain"},
            timeout=10,
        )
        result = resp.json()
        _log("baidu", urls, result)
        return result
    except Exception as e:
        err = {"error": "request_failed", "message": str(e)}
        _log("baidu", urls, err)
        return err

# 推送处理器注册表：以后加平台（如以后要做合规的 Google Indexing）只需往这里加
# 注意：小红书/微博/贴吧的「自动发布」违反平台 ToS、有封号风险，这里刻意不做
PUSH_HANDLERS = {
    "baidu": push_baidu,
}
