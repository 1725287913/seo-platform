# distribute.py
# 一键分发中枢：一次操作，把一篇稿子铺到全部目标账号。
# 对标 ALQQ「一键分发至 20+ 平台」与小火花「自动适配各平台格式」。
#
# 合规分级（沿用 platforms.py 里每个平台的 mode）：
#   auto（百度自建站）：真执行 —— 导出 SEO 静态页 + 主动推送，全自动跑完
#   semi（社交平台）  ：绝不代发 —— 模拟登录违反平台 ToS、有封号风险。
#                       这里把稿子按该平台规则改好（裁标题/配标签/转格式）排队，
#                       用户在页面上「复制并打开」两步就发完，比手工复制粘贴快得多。
import json, os, re, time, uuid
import platforms, articles, accounts, config, baidu_push

TASK_FILE = os.path.join(os.path.dirname(__file__), "data", "distribute_tasks.json")
MAX_TASKS = 400


def _read():
    if not os.path.exists(TASK_FILE):
        return []
    try:
        return json.load(open(TASK_FILE, encoding="utf-8"))
    except Exception:
        return []


def _write(arr):
    json.dump(arr[-MAX_TASKS:], open(TASK_FILE, "w", encoding="utf-8"),
              ensure_ascii=False, indent=2)


# ---------- 可分发目标（前端勾选列表就是照它渲染的）----------

def targets():
    """列出全部可分发目标：自动通道（百度）+ 已绑定的账号。"""
    cfg = config.get_config(mask_secrets=False)
    site = (cfg.get("BAIDU_SITE") or "").strip()
    token = (cfg.get("BAIDU_TOKEN") or "").strip()
    # 占位值识别：没配真域名/真 token 时，百度通道标成不可用并说明原因
    bad = (not site) or (not token) or ("example.com" in site) or ("localhost" in site) \
        or ("127.0.0.1" in site) or ("你的" in site) or ("你的" in token) or len(token) < 16
    auto = [{
        "id": "auto:baidu", "platform": "baidu", "platform_name": "百度",
        "emoji": platforms.get_platform("baidu")["emoji"],
        "name": "百度主动推送（自建站）", "mode": "auto",
        "available": not bad,
        "reason": "" if not bad else "还没配真实域名与推送 Token，去「站点配置」看体检清单",
        "publish_url": "https://ziyuan.baidu.com",
        "is_default": True,
    }]
    accts = []
    for a in accounts.list_accounts():
        p = platforms.get_platform(a["platform"])
        accts.append({
            "id": "acct:" + a["id"], "account_id": a["id"],
            "platform": a["platform"], "platform_name": p["name"], "emoji": p["emoji"],
            "name": a["name"], "mode": p["mode"], "available": True, "reason": "",
            "publish_url": p["publish_url"], "is_default": a.get("is_default", False),
            "note": a.get("note", ""), "format": platforms.get_format(a["platform"]),
        })
    # 默认账号排前面，方便一眼看出主推哪个号
    accts.sort(key=lambda x: (not x["is_default"], x["platform_name"]))
    return {"auto": auto, "accounts": accts}


# ---------- 平台适配：把同一篇稿子改成各家能直接用的形态 ----------

# 做标签时丢掉这些没有信息量的词
TAG_STOP = {"的", "了", "和", "与", "及", "在", "是", "有", "为", "对", "从", "到",
            "把", "被", "让", "给", "用", "这", "那", "如何", "怎么", "什么", "哪些",
            "一个", "一种", "可以", "需要", "必须", "应该", "我们", "你们", "他们"}


def _cut_title(text, limit):
    """标题超长裁到最后一个完整断点，不硬切半个词。返回 (标题, 是否裁过)。"""
    t = (text or "").strip().replace("\n", " ")
    if limit <= 0 or len(t) <= limit:
        return t, False
    cut = t[:limit]
    # 取最靠后的那个断点，而不是碰到的第一个（否则会丢掉半截信息）
    best = -1
    for sep in ("，", "。", "！", "？", "、", "；", "：", " ", "｜", "|", "（", "("):
        i = cut.rfind(sep)
        if i > best:
            best = i
    if best >= int(limit * 0.55):
        cut = cut[:best]
    return cut.rstrip("，。！？、；： "), True


def _to_plain(md):
    """Markdown → 纯文本（微博/小红书这类不吃 # 与 ** 的平台）。"""
    out = []
    for line in (md or "").split("\n"):
        t = re.sub(r"^#{1,6}\s*", "", line.strip())
        t = re.sub(r"^\s*[-*+]\s+", "· ", t)
        t = re.sub(r"^\s*>\s?", "", t)
        t = t.replace("**", "").replace("__", "")
        t = re.sub(r"\[(.+?)\]\((.+?)\)", r"\1", t)
        out.append(t)
    return re.sub(r"\n{3,}", "\n\n", "\n".join(out)).strip()


# 剥掉这些尾巴，长短语才能变成像样的话题标签
TAIL_WORDS = ("怎么选", "哪家好", "多少钱", "怎么样", "多少钱", "价格", "费用", "收费",
              "推荐", "排名", "排行", "公司", "哪家", "如何", "方法", "攻略", "指南",
              "注意事项", "是什么", "有哪些", "靠谱吗")


def _as_tag(chunk):
    """把一个短语收拾成话题标签：剥掉 emoji/标点与疑问词，长度压到 2~8 字。"""
    # 先去干净：只留中文、字母、数字，emoji 和标点都不要（话题标签里带 emoji 很怪）
    c = re.sub(r"[^\u4e00-\u9fa5A-Za-z0-9]", "", chunk or "")
    for _ in range(3):
        if 2 <= len(c) <= 8:
            return c
        hit = False
        for w in TAIL_WORDS:
            if c.endswith(w) and len(c) > len(w) + 1:
                c, hit = c[:-len(w)], True
                break
        if not hit:
            break
    return c if 2 <= len(c) <= 8 else ""


def _gen_tags(article, n, preset_tags=""):
    """挑 n 个话题标签：优先账号预设，其次从标题、小标题里摘核心词。"""
    if n <= 0:
        return []

    preset = []
    for chunk in re.split(r"[,，#\s、，]+", preset_tags or ""):
        chunk = chunk.strip()
        if 2 <= len(chunk) <= 12:
            preset.append(chunk)

    title_words = []
    for chunk in re.split(r"[，。！？、；：\s（）()《》【】\[\]:：|｜/\\-]+",
                          article.get("title") or ""):
        t = _as_tag(chunk)
        if t and t not in TAG_STOP:
            title_words.append(t)

    heads = []
    for line in (article.get("content") or "").split("\n"):
        if line.startswith("## "):
            t = _as_tag(line[3:])
            if t and t not in TAG_STOP:
                heads.append(t)

    # 预设最准 → 标题核心词 → 小标题；同级短的优先（短词更像话题）
    ordered = preset + sorted(title_words, key=len) + sorted(heads, key=len)
    seen, out = set(), []
    for c in ordered:
        if c not in seen:
            seen.add(c)
            out.append(c)
        if len(out) >= n:
            break
    return out


def _strip_h1(md):
    """去掉正文开头的一级标题 —— 标题已经单独给出来了，避免粘出去重复一遍。"""
    out, done = [], False
    for ln in (md or "").split("\n"):
        if not done and ln.strip().startswith("# "):
            done = True
            continue
        out.append(ln)
    return "\n".join(out).strip()


def _truncate(text, limit):
    """超长正文裁到最后一个句末标点，别在句子中间断。返回 (文本, 是否裁过)。"""
    if limit <= 0 or len(text) <= limit:
        return text, False
    cut = text[:limit]
    best = max((cut.rfind(s) for s in "。！？\n"), default=-1)
    if best >= int(limit * 0.5):
        cut = cut[:best + 1]
    return cut.rstrip(), True


def adapt(article, platform_key, preset_tags=""):
    """把一篇文章按目标平台的规则改好，返回可直接粘贴的形态。"""
    fmt = platforms.get_format(platform_key)
    p = platforms.get_platform(platform_key)
    title, cut = _cut_title(article.get("title") or "", fmt["title_max"])

    body_md = _strip_h1(article.get("content") or "")
    body = _to_plain(body_md) if fmt["body"] == "plain" else body_md
    body, cut_body = _truncate(body, fmt.get("body_max", 0))
    tags = _gen_tags(article, fmt["tags"], preset_tags)

    warn = []
    if cut:
        warn.append(f"原题超 {fmt['title_max']} 字上限，已自动裁短")
    if cut_body:
        warn.append(f"正文超该平台 {fmt['body_max']} 字上限，已裁到句末（这类平台不适合发长文）")
    if fmt["body"] == "script" and "【" not in body_md:
        warn.append("该平台是视频平台，当前是图文稿，建议到「视频发布」重出一版口播脚本")

    return {
        "platform": platform_key, "platform_name": p["name"], "emoji": p["emoji"],
        "title": title, "body": body, "tags": tags,
        "title_max": fmt["title_max"], "body_max": fmt.get("body_max", 0),
        "body_mode": fmt["body"], "body_chars": len(body),
        "format_note": fmt["note"], "warnings": warn,
        "publish_url": p["publish_url"], "mode": p["mode"],
        "copy_text": _compose_copy(title, body, tags, p["key"]),
    }


def _compose_copy(title, body, tags, platform_key):
    """拼出「粘到发布框里就是成品」的那段文本。"""
    tag_line = " ".join("#" + t for t in tags) if tags else ""
    if platform_key == "weibo":
        # 微博：正文里带话题，不重复标题
        return (body + (" " + tag_line if tag_line else "")).strip()
    parts = [title] if title else []
    if body:
        parts.append(body)
    if tag_line:
        parts.append(tag_line)
    return "\n\n".join(parts)


def preview(aid, platform_key="", preset_tags=""):
    """分发前先看各平台会被改造成什么样。"""
    art = next((a for a in articles.list_articles() if a.get("id") == aid), None)
    if not art:
        return {"error": "not_found", "message": "文章不存在"}
    keys = [platform_key] if platform_key else [p["key"] for p in platforms.PLATFORMS]
    return {"article": {"id": art["id"], "title": art.get("title", ""),
                        "platform": art.get("platform", ""),
                        "chars": len(art.get("content") or "")},
            "items": [adapt(art, k, preset_tags) for k in keys]}


# ---------- 一键分发 ----------

def run(aid, target_ids, extra_tags=""):
    """一键分发：把一篇文章铺到全部选中的目标。

    自动目标当场执行并记录结果；半自动目标生成适配稿排队等人工确认。
    """
    art = next((a for a in articles.list_articles() if a.get("id") == aid), None)
    if not art:
        return {"error": "not_found", "message": "文章不存在"}
    target_ids = [t for t in (target_ids or []) if t]
    if not target_ids:
        return {"error": "no_target", "message": "请至少勾选一个分发目标"}

    pool = {}
    for t in targets()["auto"] + targets()["accounts"]:
        pool[t["id"]] = t

    batch = time.strftime("%Y%m%d%H%M%S")
    now = time.strftime("%Y-%m-%d %H:%M:%S")
    results = []
    for tid in target_ids:
        t = pool.get(tid)
        if not t:
            continue
        r = _do_baidu(art, t) if t["mode"] == "auto" else _queue_semi(art, t, extra_tags)
        r.update({"batch": batch, "article_id": art["id"],
                  "article_title": art.get("title", ""), "target_id": tid,
                  "created_at": now})
        results.append(r)

    _write(_read() + results)
    ok = sum(1 for r in results if r["status"] in ("done", "pending"))
    return {"ok": True, "batch": batch, "count": len(results), "succeeded": ok,
            "tasks": results}


def _do_baidu(art, t):
    """百度通道：导出 SEO 静态页 → 主动推送，全自动。"""
    base = {"id": str(uuid.uuid4())[:8], "kind": "auto", "platform": "baidu",
            "platform_name": "百度", "account_name": "百度主动推送", "mode": "auto"}
    if not t.get("available"):
        return {**base, "status": "failed", "detail": t.get("reason") or "站点未配置"}

    cfg = config.get_config(mask_secrets=False)
    site = (cfg.get("BAIDU_SITE") or "").strip()
    token = (cfg.get("BAIDU_TOKEN") or "").strip()

    exp = articles.export_article_html(art["id"], site)
    if exp.get("error"):
        return {**base, "status": "failed", "detail": exp.get("message", "导出静态页失败")}
    url = exp.get("url") or ""

    res = baidu_push.push_baidu(site, token, [url] if url else [])
    if isinstance(res, dict) and res.get("error"):
        return {**base, "status": "failed", "url": url,
                "detail": f"{res.get('error')}：{res.get('message') or res}"}
    return {**base, "status": "done", "url": url,
            "detail": "已推送，百度原始返回：" + json.dumps(res, ensure_ascii=False)[:140]}


def _queue_semi(art, t, extra_tags=""):
    """社媒通道：按平台规则生成适配稿排队，等用户一键复制粘贴。"""
    preset = next((a.get("preset") or {} for a in accounts.list_accounts()
                   if a["id"] == t.get("account_id")), {})
    tags = ",".join([x for x in (extra_tags or "", preset.get("tags", "")) if x])
    ad = adapt(art, t["platform"], tags)
    return {
        "id": str(uuid.uuid4())[:8], "kind": "semi",
        "platform": t["platform"], "platform_name": t["platform_name"],
        "account_id": t.get("account_id", ""), "account_name": t["name"], "mode": "semi",
        "status": "pending", "title": ad["title"], "body": ad["body"],
        "tags": ad["tags"], "copy_text": ad["copy_text"],
        "publish_url": ad["publish_url"], "warnings": ad["warnings"],
        "format_note": ad["format_note"],
        "detail": "已按该平台规则改好，复制粘贴即可（平台不允许代发，见合规说明）",
    }


# ---------- 任务队列 ----------

def list_tasks(batch="", status="", limit=120):
    arr = _read()
    if batch:
        arr = [t for t in arr if t.get("batch") == batch]
    if status:
        arr = [t for t in arr if t.get("status") == status]
    # 新的排前面
    return list(reversed(arr))[:limit]


def get_task(tid):
    return next((t for t in _read() if t.get("id") == tid), None)


def mark_done(tid, url=""):
    """把半自动任务标记成「已发布」。"""
    arr = _read()
    hit = None
    for t in arr:
        if t.get("id") == tid:
            t["status"] = "done"
            t["done_at"] = time.strftime("%Y-%m-%d %H:%M:%S")
            if url:
                t["url"] = url
            hit = t
    if not hit:
        return {"error": "not_found", "message": "任务不存在"}
    _write(arr)
    return {"ok": True, "task": hit}


def mark_pending(tid):
    """撤销「已发布」标记。"""
    arr = _read()
    hit = None
    for t in arr:
        if t.get("id") == tid:
            t["status"] = "pending"
            t.pop("done_at", None)
            hit = t
    if not hit:
        return {"error": "not_found", "message": "任务不存在"}
    _write(arr)
    return {"ok": True, "task": hit}


def retry(tid):
    """重试失败的任务（目前只有百度通道会失败）。"""
    t = get_task(tid)
    if not t:
        return {"error": "not_found", "message": "任务不存在"}
    if t.get("kind") != "auto":
        return {"error": "not_auto", "message": "半自动任务无需重试，直接复制发布即可"}
    art = next((a for a in articles.list_articles() if a.get("id") == t["article_id"]), None)
    if not art:
        return {"error": "not_found", "message": "文章已不在了"}
    target = next((x for x in targets()["auto"] if x["id"] == t.get("target_id")), None)
    if not target:
        return {"error": "not_found", "message": "目标不存在"}
    r = _do_baidu(art, target)
    arr = _read()
    for i, x in enumerate(arr):
        if x.get("id") == tid:
            r.update({k: x.get(k) for k in ("batch", "article_id", "article_title",
                                            "target_id", "created_at")})
            arr[i] = r
    _write(arr)
    return {"ok": True, "task": r}


def clear(batch=""):
    """清空分发记录（可按批次清）。"""
    if batch:
        _write([t for t in _read() if t.get("batch") != batch])
    else:
        _write([])
    return {"ok": True}


def summary():
    """给仪表盘用的分发统计。"""
    arr = _read()
    return {
        "total": len(arr),
        "done": sum(1 for t in arr if t.get("status") == "done"),
        "pending": sum(1 for t in arr if t.get("status") == "pending"),
        "failed": sum(1 for t in arr if t.get("status") == "failed"),
        "by_platform": _count_by(arr, "platform_name"),
    }


def _count_by(arr, field):
    out = {}
    for t in arr:
        k = t.get(field) or "未知"
        out[k] = out.get(k, 0) + 1
    return [{"name": k, "count": v} for k, v in
            sorted(out.items(), key=lambda x: -x[1])]
