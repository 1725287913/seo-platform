# index_check.py
# 百度收录检测：用 site: 语法查文章 URL 是否被百度收录。
# 注意：百度对外部请求有反爬（可能弹安全验证），检测结果仅供参考，最终以百度站长平台为准。
import json, os, re, time
from urllib.parse import urlparse
import httpx

UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/122.0 Safari/537.36")

NOTE = ("百度对外部程序查询有反爬限制，若结果全是「未知」，请用百度站长平台的"
        "「索引量 / 抓取诊断」核对，数据更权威。")


def _domain(url: str):
    try:
        return urlparse(url if url.startswith("http") else "https://" + url).netloc
    except Exception:
        return ""


def check_one(url: str):
    """查单个 URL：返回 {url, status: indexed|not_indexed|unknown, detail}。"""
    domain = _domain(url)
    if not domain:
        return {"url": url, "status": "unknown", "detail": "URL 格式不对"}
    try:
        r = httpx.get(
            "https://www.baidu.com/s",
            params={"wd": f"site:{url}"},
            headers={"User-Agent": UA, "Accept-Language": "zh-CN,zh;q=0.9"},
            timeout=15,
            follow_redirects=True,
        )
        text = r.text
    except Exception as e:
        return {"url": url, "status": "unknown", "detail": f"请求失败：{str(e)[:60]}"}

    # 反爬/验证页
    if "安全验证" in text or "网络不给力" in text or r.status_code != 200:
        return {"url": url, "status": "unknown",
                "detail": f"百度返回验证页（HTTP {r.status_code}），无法判定"}

    # 没有收录时百度会出现这些文案
    if "没有找到" in text or "很抱歉" in text or "未找到" in text:
        return {"url": url, "status": "not_indexed", "detail": "百度未收录该页面"}

    # 结果里出现该域名 → 认为已收录
    if domain in text:
        # 尽量把命中的标题抠出来，方便人工核对
        m = re.search(r"<h3[^>]*>(.*?)</h3>", text, re.S)
        title = re.sub(r"<[^>]+>", "", m.group(1)).strip() if m else ""
        return {"url": url, "status": "indexed", "detail": title[:60] or "已收录"}

    return {"url": url, "status": "not_indexed", "detail": "结果中未出现该 URL"}


def check(urls: list):
    """批量检测（建议一次不超过 10 条，避免触发反爬）。结果会落盘，供数据中心统计收录率。"""
    urls = [u for u in (urls or []) if u and u.strip()]
    if not urls:
        return {"error": "empty", "message": "没有要检测的 URL"}
    results = [check_one(u.strip()) for u in urls[:10]]
    _save(results)
    indexed = sum(1 for r in results if r["status"] == "indexed")
    return {"results": results, "indexed": indexed, "total": len(results), "note": NOTE}


# ---------- 结果落盘（最近 200 条，按 URL 去重保留最新） ----------
HIST_FILE = os.path.join(os.path.dirname(__file__), "data", "index_check.json")


def _save(results: list):
    hist = history()
    for r in results:
        hist = [h for h in hist if h.get("url") != r["url"]]
        hist.append({**r, "time": time.strftime("%Y-%m-%d %H:%M")})
    json.dump(hist[-200:], open(HIST_FILE, "w", encoding="utf-8"), ensure_ascii=False, indent=2)


def history():
    if not os.path.exists(HIST_FILE):
        return []
    try:
        return json.load(open(HIST_FILE, encoding="utf-8"))
    except Exception:
        return []
