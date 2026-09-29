# stats.py
# 统计：给「仪表盘 / 数据中心」用的聚合数据。全部从现有 JSON 现算，无额外存储。
import datetime
import articles
import schedule
import accounts
import banned_words
import baidu_push
import config
import models
import providers
import knowledge
import keywords
import index_check
import products


def _parse_day(s: str):
    """把 created_at（'2026-09-29 11:20'）转成 date；解析不了返回 None。"""
    try:
        return datetime.datetime.strptime((s or "")[:10], "%Y-%m-%d").date()
    except Exception:
        return None


def get_stats():
    """仪表盘用的总览（保持原有字段，前端不用改）。"""
    arts = articles.list_articles()
    sched = schedule.list_schedule()
    accs = accounts.list_accounts()
    log = baidu_push.get_log()

    by_status, by_platform = {}, {}
    for a in arts:
        by_status[a.get("status", "draft")] = by_status.get(a.get("status", "draft"), 0) + 1
        by_platform[a.get("platform", "baidu")] = by_platform.get(a.get("platform", "baidu"), 0) + 1

    acc_by_platform = {}
    for a in accs:
        acc_by_platform.setdefault(a["platform"], []).append(a)

    cfg = config.get_config()
    # AI 密钥状态按服务商动态生成（加了新服务商不用改这里）
    key_status = {p["key_env"]: cfg.get(p["key_env"] + "_configured", False)
                  for p in providers.list_providers()}
    key_status["IMAGE_API_KEY"] = cfg.get("IMAGE_API_KEY_configured", False)
    key_status["BAIDU_SITE"] = bool(cfg.get("BAIDU_SITE"))
    key_status["BAIDU_TOKEN"] = cfg.get("BAIDU_TOKEN_configured", False)

    today = datetime.date.today()
    today_arts = [a for a in arts if _parse_day(a.get("created_at")) == today]

    return {
        "articles_total": len(arts),
        "articles_today": len(today_arts),
        "articles_by_status": by_status,
        "articles_by_platform": by_platform,
        "schedule_total": len(sched),
        "schedule_pending": sum(1 for s in sched if s.get("status") == "pending"),
        "schedule_done": sum(1 for s in sched if s.get("status") == "done"),
        "accounts_total": len(accs),
        "accounts_by_platform": {k: len(v) for k, v in acc_by_platform.items()},
        "banned_words_total": len(banned_words.load_words()),
        "knowledge_total": len(knowledge.list_docs()),
        "keywords_total": len(keywords.list_keywords()),
        "products_total": len(products.list_products()),
        "push_total": len(log),
        "push_ok": sum(1 for x in log if x.get("success")),
        "push_fail": sum(1 for x in log if not x.get("success")),
        "key_status": key_status,
        "active_model": (models.get_active() or {}).get("model_name", "—"),
    }


def datacenter(days=30, platform="", status="", q=""):
    """数据中心：带筛选的指标卡 + 平台概览 + 近 N 天趋势。"""
    arts = articles.list_articles()
    log = baidu_push.get_log()
    sched = schedule.list_schedule()

    # 时间范围过滤（days=0 表示全部）
    cutoff = None
    if days and days > 0:
        cutoff = datetime.date.today() - datetime.timedelta(days=days - 1)
    if cutoff:
        arts = [a for a in arts if (_parse_day(a.get("created_at")) or datetime.date(1970, 1, 1)) >= cutoff]
        log = [x for x in log if (_parse_day(x.get("time")) or datetime.date(1970, 1, 1)) >= cutoff]

    if platform:
        arts = [a for a in arts if a.get("platform") == platform]
        log = [x for x in log if x.get("platform", "baidu") == platform]
    if status:
        arts = [a for a in arts if a.get("status") == status]
    if q:
        arts = [a for a in arts if q.lower() in (a.get("title") or "").lower()
                or q.lower() in (a.get("keyword") or "").lower()]

    # 指标卡
    pushed_status = {"published", "pushed"}
    published = sum(1 for a in arts if a.get("status") in pushed_status)
    ok = sum(1 for x in log if x.get("success"))
    fail = len(log) - ok
    rate = round(ok / len(log) * 100) if log else 0

    # 平台概览：每平台的文章数 / 已发布 / 推送成功失败 / 最近推送时间
    overview = {}
    for a in arts:
        p = a.get("platform", "baidu")
        row = overview.setdefault(p, {"platform": p, "articles": 0, "published": 0,
                                      "push_ok": 0, "push_fail": 0, "last_push": ""})
        row["articles"] += 1
        if a.get("status") in pushed_status:
            row["published"] += 1
    for x in log:
        p = x.get("platform", "baidu")
        row = overview.setdefault(p, {"platform": p, "articles": 0, "published": 0,
                                      "push_ok": 0, "push_fail": 0, "last_push": ""})
        if x.get("success"):
            row["push_ok"] += 1
        else:
            row["push_fail"] += 1
        t = x.get("time", "")
        if t > row["last_push"]:
            row["last_push"] = t

    # 趋势：近 N 天每天的文章数 / 推送成功数（days=0 → 取最近 30 天展示）
    span = days if days and days > 0 else 30
    trend = []
    today = datetime.date.today()
    for i in range(span - 1, -1, -1):
        d = today - datetime.timedelta(days=i)
        trend.append({
            "date": d.strftime("%m-%d"),
            "articles": sum(1 for a in arts if _parse_day(a.get("created_at")) == d),
            "push": sum(1 for x in log if _parse_day(x.get("time")) == d and x.get("success")),
        })

    # 收录情况（取最近一次检测结果）
    idx_hist = index_check.history()
    idx_indexed = sum(1 for r in idx_hist if r.get("status") == "indexed")
    idx_total = len(idx_hist)

    return {
        "metrics": {
            "articles": len(arts),
            "published": published,
            "push_ok": ok,
            "push_fail": fail,
            "push_rate": rate,
            "schedule_pending": sum(1 for s in sched if s.get("status") == "pending"),
            "platforms": len(overview),
            "indexed": idx_indexed,
            "index_total": idx_total,
            "active_model": (models.get_active() or {}).get("model_name", "—"),
        },
        "overview": sorted(overview.values(), key=lambda r: -r["articles"]),
        "trend": trend,
    }
