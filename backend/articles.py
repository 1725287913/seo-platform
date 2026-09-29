# articles.py
# 文章存储：用本地 JSON 文件（data/articles.json），零依赖、便于查看。
# 后期可无缝换成数据库，只需改这个文件内部实现。
import os, time, json, re
import markdown as _md

DATA_FILE = os.path.join(os.path.dirname(__file__), "data", "articles.json")
# 生成的 SEO 静态页存放目录（方便你下载 / 部署到自己服务器）
HTML_DIR = os.path.join(os.path.dirname(__file__), "data", "html")
os.makedirs(HTML_DIR, exist_ok=True)

def _read():
    if not os.path.exists(DATA_FILE):
        return []
    with open(DATA_FILE, encoding="utf-8") as f:
        return json.load(f)

def _write(items):
    os.makedirs(os.path.dirname(DATA_FILE), exist_ok=True)
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(items, f, ensure_ascii=False, indent=2)

def list_articles():
    return _read()

# 文章状态：draft(草稿) / generated(已生成) / checked(已过违禁词) / published(已发布)
def add_article(article: dict):
    items = _read()
    article = dict(article)  # 不修改入参
    article["id"] = str(int(time.time() * 1000))
    article.setdefault("status", "draft")
    article.setdefault("platform", "baidu")
    article.setdefault("title", "")
    article.setdefault("content", "")
    article.setdefault("cover_prompt", "")     # 配图方案
    article.setdefault("account", "")          # 半自动发布目标账号
    article.setdefault("topic", "")            # 关联热点选题
    article.setdefault("created_at", time.strftime("%Y-%m-%d %H:%M"))
    items.insert(0, article)
    _write(items)
    return article

TRASH = os.path.join(os.path.dirname(__file__), "data", "articles_trash.json")


def _read_trash():
    if not os.path.exists(TRASH):
        return []
    try:
        return json.load(open(TRASH, encoding="utf-8"))
    except Exception:
        return []


def _write_trash(arr):
    json.dump(arr, open(TRASH, "w", encoding="utf-8"), ensure_ascii=False, indent=2)


def delete_article(aid: str):
    """删除文章 —— 先进回收站，误删可以捞回来。"""
    import datetime
    items, gone = [], None
    for a in _read():
        if a.get("id") == aid:
            gone = a
        else:
            items.append(a)
    _write(items)
    if gone:
        gone["_deleted_at"] = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
        trash = [t for t in _read_trash() if t.get("id") != aid]
        trash.insert(0, gone)
        _write_trash(trash[:200])   # 只留最近 200 条，免得文件无限涨
    return {"ok": True, "deleted": bool(gone)}


def list_trash():
    return _read_trash()


def restore_article(aid: str):
    """从回收站恢复。"""
    trash = _read_trash()
    item = next((t for t in trash if t.get("id") == aid), None)
    if not item:
        return {"error": "not_found", "message": "回收站里没有这篇"}
    item.pop("_deleted_at", None)
    arr = _read()
    if not any(a.get("id") == aid for a in arr):
        arr.append(item)
        _write(arr)
    _write_trash([t for t in trash if t.get("id") != aid])
    return {"ok": True, "article": item}


def purge_trash():
    """彻底清空回收站。"""
    _write_trash([])
    return {"ok": True}

def update_status(aid: str, status: str):
    items = _read()
    for a in items:
        if a.get("id") == aid:
            a["status"] = status
    _write(items)


# ---------- 文章 → SEO 静态页（打通百度真闭环用）----------

def slug(aid: str):
    """文章对应的静态页文件名，固定 seo-{id}.html，避免中文 URL 编码问题。"""
    return f"seo-{aid}.html"


def build_article_url(aid: str, site: str):
    """根据站点域名拼出文章的线上 URL。site 形如 www.example.com（可带 http）。"""
    site = (site or "").strip()
    if not site:
        return ""
    site = site.replace("http://", "").replace("https://", "").rstrip("/")
    return f"https://{site}/{slug(aid)}"


def _strip_first_heading(md: str):
    """去掉正文开头的第一个 # 标题行（页面 h1 用数据库的 title，避免重复 h1）。"""
    out, skipped = [], False
    for ln in md.split("\n"):
        if not skipped and ln.strip().startswith("# "):
            skipped = True
            continue
        out.append(ln)
    return "\n".join(out)


def _extract_summary(md: str, n: int = 120):
    """取正文第一个非空段落作为 description / 摘要。"""
    for para in md.split("\n"):
        p = re.sub(r"[#>*\-\s]", "", para).strip()
        if p:
            return p[:n]
    return ""


def to_seo_html(article: dict, site: str):
    """把一篇文章渲染成符合百度 SEO 规范的完整 HTML 页面。"""
    aid = article.get("id", "")
    title = article.get("title") or "(无标题)"
    md = article.get("content") or ""
    body_md = _strip_first_heading(md)
    body_html = _md.markdown(body_md, extensions=["extra"]) if body_md else ""
    summary = _extract_summary(md)
    keywords = article.get("keyword") or title
    date = article.get("created_at", time.strftime("%Y-%m-%d"))
    jsonld = {
        "@context": "https://schema.org",
        "@type": "Article",
        "headline": title,
        "description": summary,
        "datePublished": date,
        "author": {"@type": "Person", "name": "AI 内容中台"},
    }
    # 转义双引号，防止破坏 HTML 属性
    esc = lambda s: str(s).replace('"', "&quot;")

    html = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>{esc(title)} - 我的SEO测试站</title>
  <meta name="description" content="{esc(summary)}">
  <meta name="keywords" content="{esc(keywords)}">
  <script type="application/ld+json">
{json.dumps(jsonld, ensure_ascii=False, indent=2)}
  </script>
</head>
<body>
  <article>
    <h1>{esc(title)}</h1>
    <p>{esc(summary)}</p>
    {body_html}
    <p style="color:#888;font-size:13px;">声明：本内容由 AI 辅助生成，已人工校验。</p>
  </article>
</body>
</html>"""
    return html


def export_article_html(aid: str, site: str):
    """生成 SEO HTML 并写入 data/html/seo-{id}.html，返回字符串/路径/URL。"""
    items = _read()
    art = next((a for a in items if a.get("id") == aid), None)
    if not art:
        return {"error": "not_found", "message": f"文章 {aid} 不存在"}
    html = to_seo_html(art, site)
    path = os.path.join(HTML_DIR, slug(aid))
    with open(path, "w", encoding="utf-8") as f:
        f.write(html)
    return {"ok": True, "html": html, "file": path, "url": build_article_url(aid, site),
            "slug": slug(aid)}
