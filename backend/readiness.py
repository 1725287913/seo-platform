# readiness.py
# 百度闭环「准备就绪」诊断：一键检查要跑通百度到底还缺什么，缺哪步就告诉你下一步去做什么。
#
# 百度闭环的完整链路（缺任何一环都推不成功）：
#   有网站（域名+备案） → 页面能公网访问 → 百度搜索资源平台验证站点 → 拿到推送 token
#   → 平台生成文章并导出静态页 → 上传到网站 → 主动推送 URL → 百度收录 → 出排名
import os, glob
import httpx
import config
import articles

# 明显是占位/本地的域名，不算真站点
PLACEHOLDER = ("example.com", "localhost", "127.0.0.1", "your-domain", "test.com", "xxx.com")


def _ok(key, name, detail, fix=""):
    return {"key": key, "name": name, "status": "ok", "detail": detail, "fix": fix}


def _fail(key, name, detail, fix=""):
    return {"key": key, "name": name, "status": "fail", "detail": detail, "fix": fix}


def _warn(key, name, detail, fix=""):
    return {"key": key, "name": name, "status": "warn", "detail": detail, "fix": fix}


def _manual(key, name, detail, fix=""):
    return {"key": key, "name": name, "status": "manual", "detail": detail, "fix": fix}


def _html_count():
    d = os.path.join(os.path.dirname(__file__), "data", "html")
    return len(glob.glob(os.path.join(d, "*.html")))


def check(reach_timeout=6):
    """跑一遍全部检查，返回清单 + 下一步该干嘛。"""
    cfg = config.get_config(mask_secrets=False)
    site = (cfg.get("BAIDU_SITE") or "").strip()
    token = (cfg.get("BAIDU_TOKEN") or "").strip()
    items = []

    # ① 有没有一个真实的网站域名 —— 这是整条链路的起点
    site_clean = site.replace("http://", "").replace("https://", "").rstrip("/")
    is_placeholder = (not site_clean) or any(p in site_clean.lower() for p in PLACEHOLDER)
    if not site_clean:
        items.append(_fail("site", "网站域名",
                           "还没填站点域名",
                           "先有一个网站：买域名（约 50~80 元/年）→ 备案 → 解析到服务器。"
                           "还没有网站时，百度推送这步物理上做不了，因为百度要抓一个公网地址。"))
    elif is_placeholder:
        items.append(_fail("site", "网站域名",
                           f"当前是占位域名 {site_clean}，不是你的真实网站",
                           "换成你自己的域名，比如 www.你的品牌.com。example.com 是文档示例，推送必然失败。"))
    else:
        items.append(_ok("site", "网站域名", f"已填 {site_clean}"))

    # ② 网站现在能不能打开（能公网访问才谈得上收录）
    if is_placeholder:
        items.append(_warn("reachable", "站点可访问",
                           "域名还没配好，跳过连通性检测",
                           "填了真实域名后重新点一次诊断"))
    else:
        try:
            r = httpx.get(f"https://{site_clean}", timeout=reach_timeout, follow_redirects=True)
            if r.status_code == 200:
                items.append(_ok("reachable", "站点可访问", f"HTTP 200，页面能正常打开"))
            else:
                items.append(_warn("reachable", "站点可访问",
                                   f"返回 HTTP {r.status_code}",
                                   "确认域名解析已生效、网站程序已启动、服务器 80/443 端口放行"))
        except Exception as e:
            items.append(_warn("reachable", "站点可访问",
                               f"打不开（{type(e).__name__}）",
                               "域名没解析 / 服务器没起 / 未备案被拦，三者之一。先在浏览器里能打开再回来"))

    # ③ ICP 备案（百度对境内服务器站点硬性要求）
    items.append(_manual("icp", "ICP 备案",
                         "境内服务器必须备案，未备案百度不收",
                         "在阿里云/腾讯云控制台提交备案，免费，一般 7~20 个工作日。"
                         "用中国香港/海外服务器可免备案，但国内收录速度明显更慢"))

    # ④ 百度推送 token
    token_fake = bool(token) and (
        len(token) < 16 or any(c in token for c in "你的示例xxx占位请填写中文") or
        not all(c.isalnum() for c in token))
    if token and not token_fake:
        items.append(_ok("token", "百度推送 Token", f"已配置（{token[:6]}…）"))
    elif token_fake:
        items.append(_fail("token", "百度推送 Token",
                           f"看起来是占位值（{token[:12]}），不是真的 token",
                           "真实的 token 是一串 16 位以上的字母数字。去 ziyuan.baidu.com → "
                           "普通收录 → 主动推送里复制粘贴，别手打"))
    else:
        items.append(_fail("token", "百度推送 Token",
                           "还没填 token",
                           "登录 ziyuan.baidu.com（百度搜索资源平台）→ 添加并验证你的站点 → "
                           "普通收录 → 主动推送 → 复制那串 token 贴到这里"))

    # ⑤ 有没有内容可推（文章库）
    arts = articles.list_articles()
    if arts:
        pushed = sum(1 for a in arts if a.get("status") == "pushed")
        items.append(_ok("content", "内容储备",
                         f"文章库 {len(arts)} 篇（已推送 {pushed} 篇）"))
    else:
        items.append(_warn("content", "内容储备",
                           "文章库还是空的",
                           "先去「AI 创作」出一篇稿并存草稿，有内容才谈得上推送"))

    # ⑥ 有没有导出过 SEO 静态页
    n = _html_count()
    if n:
        items.append(_ok("export", "SEO 静态页", f"已导出 {n} 个 HTML 页面"))
    else:
        items.append(_warn("export", "SEO 静态页",
                           "还没导出过页面",
                           "在「AI 创作」生成文章后点「发布 / 推送百度」，会把文章导出成带 TDK 的 HTML，"
                           "这个文件要上传到你的网站根目录"))

    # ⑦ 站点根目录的 robots.txt / sitemap.xml（收录加速项）
    items.append(_manual("sitemap", "robots.txt / sitemap.xml",
                         "建议在网站根目录放这两个文件，收录会快很多",
                         "robots.txt 里放一行 Sitemap: https://你的域名/sitemap.xml；"
                         "sitemap.xml 每行一个文章地址，百度会定期来抓"))

    # ⑧ 真推一次（可选，会消耗当天配额）
    items.append(_manual("push_test", "实际推送测试",
                         "前面的都好了之后，点「测试推送」真发一条给百度看返回",
                         "百度返回 {\"success\":1} 就是成功。返回 401=token 错，"
                         "403/other=站点未验证或未备案，over quota=当天 10 条配额用完"))

    # ---------- 汇总 ----------
    fails = [i for i in items if i["status"] == "fail"]
    warns = [i for i in items if i["status"] == "warn"]
    done = [i for i in items if i["status"] == "ok"]
    # 前 3 项（域名/可访问/token）是硬性门槛
    ready = not fails and not any(i["key"] == "reachable" and i["status"] != "ok" for i in items)

    if fails:
        nxt = fails[0]["fix"] or fails[0]["detail"]
    elif warns:
        nxt = warns[0]["fix"] or warns[0]["detail"]
    else:
        nxt = "全绿了 —— 可以出稿 → 导出 → 推百度，完整跑一遍了"

    return {
        "ready": ready,
        "passed": len(done),
        "total": len([i for i in items if i["status"] != "manual"]),
        "items": items,
        "next_step": nxt,
        "site": site_clean,
    }
