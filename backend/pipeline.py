# pipeline.py
# 一键流水线：关键词 → 出稿 → 违禁词检测 → 存草稿 → 配图 → 导出静态页 → 推送百度。
# 每一步都记进 steps，前端按步骤展示，哪步失败一眼能看到。
import generate
import banned_words
import articles
import images
import baidu_push
import config
import webhooks


def _title_of(md: str, keyword: str):
    """取正文第一个 # 标题作为文章标题，取不到就用关键词。"""
    for line in (md or "").split("\n"):
        if line.strip().startswith("# "):
            return line.strip()[2:].strip()
    return keyword


def run(keyword, platform="baidu", model_id=None, template_id="", real_data="",
        account="", auto_cover=False, auto_push=False, product_ids="", writing_cfg=None):
    steps = []
    cfg = config.get_config(mask_secrets=False)
    site = cfg.get("BAIDU_SITE", "")
    token = cfg.get("BAIDU_TOKEN", "")

    # ① 出稿
    gen = generate.generate_article(keyword, platform, model_id, real_data,
                                    "", template_id, account, product_ids=product_ids,
                                    writing_cfg=writing_cfg)
    if gen.get("error"):
        steps.append({"name": "AI 出稿", "ok": False, "detail": gen.get("message", "失败")})
        return {"ok": False, "steps": steps}
    content = gen["content"]
    used = gen.get("used", {})
    extra = []
    if used.get("writing"):
        extra.append("写作配置：" + used["writing"])
    if used.get("persona"):
        extra.append("已套人设")
    if used.get("template"):
        extra.append("已套模板")
    if used.get("knowledge"):
        extra.append("已注入知识库资料")
    if used.get("products"):
        extra.append("已注入产品：" + "、".join(used["products"]))
    steps.append({"name": "AI 出稿", "ok": True,
                  "detail": f"模型 {gen.get('model','')}，{len(content)} 字"
                            + ("（" + "、".join(extra) + "）" if extra else "")})

    # ② 违禁词检测（按平台叠加专属词库）
    matches = banned_words.check_text(content, platform)
    words = sorted({m["word"] for m in matches})
    steps.append({"name": "违禁词检测", "ok": not matches,
                  "detail": ("命中 " + "、".join(words[:8])) if matches else "未检出违禁词"})

    # ③ 存草稿
    art = articles.add_article({
        "title": _title_of(content, keyword),
        "content": content,
        "keyword": keyword,
        "platform": platform,
        "account": account,
        "model": gen.get("model", ""),
        "status": "checked" if not matches else "draft",
    })
    steps.append({"name": "保存草稿", "ok": True, "detail": f"文章 ID {art['id']}"})

    # ④ 配图方案（可选，需要配图接口 Key）
    if auto_cover:
        img = images.generate_cover(keyword, platform, content,
                                    cfg.get("IMAGE_API_BASE", ""), cfg.get("IMAGE_API_KEY", ""),
                                    cfg.get("IMAGE_MODEL", "default"),
                                    note_cfg=writing_cfg)
        ok = not img.get("error")
        plan = img.get("image_plan") or {}
        hint = f"（{plan.get('strategy_name','')}，建议 {plan.get('count','')} 张）" if plan else ""
        steps.append({"name": "配图方案", "ok": ok,
                      "detail": ("已生成" + hint) if ok else img.get("message", "未配置配图 Key，已跳过")})

    # ⑤ 导出 SEO 静态页（需要先配站点域名）
    url = ""
    if site:
        exp = articles.export_article_html(art["id"], site)
        url = exp.get("url", "")
        steps.append({"name": "导出 SEO 静态页", "ok": True,
                      "detail": f"{exp.get('slug','')} → {url}"})
    else:
        steps.append({"name": "导出 SEO 静态页", "ok": False,
                      "detail": "未配置 BAIDU_SITE（站点域名），已跳过"})

    # ⑥ 推送百度（可选）
    push = None
    if auto_push:
        if not (site and token) or not url:
            steps.append({"name": "推送百度", "ok": False,
                          "detail": "缺少域名/Token 或 URL，已跳过（在「站点配置」补齐）"})
        else:
            push = baidu_push.push_baidu(site, token, [url])
            ok = bool(push.get("success")) and not push.get("error")
            if ok:
                articles.update_status(art["id"], "pushed")
            steps.append({"name": "推送百度", "ok": ok,
                          "detail": push.get("message") or push.get("summary") or str(push)[:120]})

    result = {"ok": all(s["ok"] for s in steps[:3]), "steps": steps,
              "article_id": art["id"], "title": art["title"], "url": url,
              "matches": matches, "push": push}

    # ⑦ 触发 Webhook（不阻塞主流程，失败也只记在 steps 之后的字段里）
    hooks = webhooks.fire("pipeline_done", {
        "article_id": art["id"], "title": art["title"], "platform": platform,
        "keyword": keyword, "url": url, "violation_words": words,
    })
    if hooks:
        result["webhooks"] = hooks
    return result
