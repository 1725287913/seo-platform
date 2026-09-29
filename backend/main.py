# main.py
# FastAPI 主入口：提供 API + 托管前端静态页
# 启动：在 backend 目录执行  python -m uvicorn main:app --port 8020
import os

# 确保 data 目录存在：从 GitHub 下载的项目里 data/ 是空的（用户数据不进仓库），
# 少了这一步，各模块第一次写文件会因「目录不存在」直接报错。
os.makedirs(os.path.join(os.path.dirname(__file__), "data"), exist_ok=True)

import base64
from fastapi import Body, FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

import config
import banned_words
import baidu_push
import generate
import articles
import images
import topics
import accounts
import schedule
import platforms
import models
import stats
import keywords
import knowledge
import personas
import snippets
import templates
import webhooks
import pipeline
import index_check
import products
import providers
import writing
import presets
import readiness

app = FastAPI(title="SEO 矩阵平台（对标 ALPP · 百度全量测试中）")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], allow_methods=["*"], allow_headers=["*"],
)

# 启动时迁移老配置：DeepSeek 的 deepseek-chat / deepseek-reasoner 已被官方停用
models.migrate()

# ---------- 请求体模型 ----------
class ConfigIn(BaseModel):
    # 只保留站点/配图这类固定项；各家 AI 密钥是动态字段，走 dict 直传
    BAIDU_SITE: str = ""
    BAIDU_TOKEN: str = ""
    IMAGE_API_BASE: str = ""
    IMAGE_API_KEY: str = ""
    IMAGE_MODEL: str = "default"

class TestIn(BaseModel):
    """测试某个服务商/接口是否可用。key 留空则用 .env 里已存的。"""
    kind: str = "deepseek"
    model: str = ""
    api_base: str = ""
    key: str = ""

class ProviderIn(BaseModel):
    """一键配置服务商。"""
    provider: str
    model_name: str = ""
    api_base: str = ""
    key: str = ""

class GenerateIn(BaseModel):
    keyword: str
    platform: str = "baidu"
    model_id: str = ""       # 留空则用「模型中心」当前生效模型
    real_data: str = ""
    topic: str = ""
    template_id: str = ""    # 写作模板（模板市场）
    account: str = ""        # 账号名（用于匹配账号人设）
    product_ids: str = ""    # 关联产品（逗号分隔），留空则按主题自动匹配
    # 写作配置：风格/受众/行业/字数/语言/去AI味/结构/自定义要求/创意度/配图… 见 writing.py
    writing: dict = {}

class SocialIn(BaseModel):
    kind: str = "post"       # post=动态图文 / video=视频脚本
    platform: str = "xiaohongshu"
    keyword: str
    model_id: str = ""
    real_data: str = ""
    account: str = ""
    writing: dict = {}

class PipelineIn(BaseModel):
    keyword: str
    platform: str = "baidu"
    model_id: str = ""
    template_id: str = ""
    real_data: str = ""
    account: str = ""
    product_ids: str = ""
    auto_cover: bool = False
    auto_push: bool = False
    writing: dict = {}

class KeywordIn(BaseModel):
    keyword: str
    group: str = "默认分组"
    intent: str = "信息型"
    difficulty: int = 3
    note: str = ""

class ExpandIn(BaseModel):
    seed: str
    model_id: str = ""
    n: int = 10

class DocIn(BaseModel):
    title: str
    content: str
    tags: str = ""

class DocImportIn(BaseModel):
    filename: str
    content_b64: str          # 文件二进制转 base64（前端 FileReader 读出来）
    tags: str = ""

class ProductIn(BaseModel):
    name: str
    category: str = ""
    selling: str = ""         # 卖点，一行一条
    specs: str = ""
    price: str = ""
    url: str = ""
    image: str = ""
    tags: str = ""

class PersonaIn(BaseModel):
    platform: str = "baidu"
    name: str
    audience: str = ""
    tone: str = ""
    selling: str = ""
    taboo: str = ""
    extra: str = ""

class SnippetIn(BaseModel):
    title: str = ""
    content: str
    tags: str = ""
    platform: str = ""

class TemplateIn(BaseModel):
    name: str
    category: str = "自定义"
    platform: str = ""
    outline: str = ""
    instruction: str = ""

class HookIn(BaseModel):
    name: str = ""
    url: str
    event: str = "all"
    enabled: bool = True

class IndexCheckIn(BaseModel):
    urls: list[str] = []

class CheckIn(BaseModel):
    text: str
    platform: str = ""     # 留空=只查通用词库；填平台 key=额外查该平台专属词

class WordIn(BaseModel):
    word: str
    platform: str = ""     # 留空=加进通用词库；否则加进平台专属词库

class PushIn(BaseModel):
    platform: str = "baidu"
    urls: list[str] = []

class ImageIn(BaseModel):
    keyword: str
    platform: str = "baidu"
    article_text: str = ""
    writing: dict = {}     # 写作配置里的「图片策略 / 配图密度」

class TopicIn(BaseModel):
    keyword: str
    source: str = ""
    note: str = ""

class AccountIn(BaseModel):
    platform: str
    name: str
    url: str = ""
    note: str = ""
    is_default: bool = False

class ScheduleIn(BaseModel):
    article_id: str = ""
    platform: str = "baidu"
    account: str = ""
    planned_at: str = ""
    note: str = ""

class ModelIn(BaseModel):
    id: str = ""
    label: str = ""
    provider: str = "openai-compatible"
    api_base: str = ""
    key_env: str = "DEEPSEEK_API_KEY"
    model_name: str = ""
    active: bool = False

# ---------- 配置 ----------
@app.get("/api/config")
def get_config():
    return config.get_config()

@app.post("/api/config")
def post_config(c: dict):
    # 收 dict 而非固定模型：各家 AI 的密钥变量是动态的，save_config 内部按白名单过滤
    return config.save_config(c)

@app.post("/api/config/test")
def api_test(t: TestIn):
    return config.test_connection(t.kind, t.model, t.api_base, t.key)

# ---------- 百度闭环就绪诊断 ----------
@app.get("/api/baidu-readiness")
def api_baidu_readiness():
    """一键体检：要跑通百度，现在还缺什么、下一步该做什么。"""
    return readiness.check()

# ---------- AI 服务商（选一家就自动配好地址和模型）----------
@app.get("/api/providers")
def api_providers():
    cfg = config.get_config(mask_secrets=True)
    active = models.get_active() or {}
    out = []
    for p in providers.list_providers():
        item = dict(p)
        item["key_configured"] = bool(cfg.get(p["key_env"] + "_configured"))
        item["is_active"] = (active.get("provider") == p["key"])
        out.append(item)
    return {"providers": out, "groups": providers.GROUPS, "active": active}

@app.post("/api/providers/activate")
def api_activate_provider(x: ProviderIn):
    return models.activate_provider(x.provider, x.model_name, x.api_base, x.key)

# ---------- 平台注册表（全量，前端据此渲染 tab）----------
@app.get("/api/platforms")
def api_platforms():
    return {"platforms": platforms.list_platforms()}

# ---------- 模型中心 ----------
@app.get("/api/models")
def api_models():
    return {"models": models.list_models(), "active": (models.get_active() or {}).get("id")}

@app.post("/api/models")
def api_add_model(m: ModelIn):
    return models.add_model(m.model_dump())

@app.delete("/api/models/{mid}")
def api_del_model(mid: str):
    return models.delete_model(mid)

@app.post("/api/models/active")
def api_set_active(body: dict):
    return models.set_active(body.get("id", ""))

@app.post("/api/models/test")
def api_test_model(body: dict):
    return models.test_model(body.get("id"))

# ---------- AI 出稿 ----------
@app.post("/api/generate")
def api_generate(g: GenerateIn):
    # 必须拿真实密钥（mask_secrets=False），不能用脱敏版
    return generate.generate_article(
        g.keyword, g.platform, g.model_id or None, g.real_data, g.topic,
        g.template_id, g.account, product_ids=g.product_ids, writing_cfg=g.writing
    )

@app.post("/api/generate/social")
def api_generate_social(s: SocialIn):
    """社媒短内容：动态图文 / 视频脚本。"""
    return generate.generate_social(s.kind, s.platform, s.keyword,
                                    s.model_id or None, s.real_data, s.account,
                                    writing_cfg=s.writing)

# ---------- 写作配置 / 配置预设 ----------
@app.get("/api/writing-options")
def api_writing_options():
    """所有可调写作项的定义 —— 前端「写作配置」面板照着它渲染，后端加一项前端自动出现。"""
    return {"options": writing.OPTIONS, "image_options": writing.IMAGE_OPTIONS,
            "defaults": writing.defaults()}

@app.get("/api/presets")
def api_presets():
    return {"presets": presets.list_presets()}

@app.post("/api/presets")
def api_add_preset(body: dict = Body(...)):
    """保存当前写作配置为预设（同名覆盖）。"""
    return presets.add_preset(body.get("name", ""), body.get("config", {}),
                              body.get("platform", ""))

@app.delete("/api/presets/{pid}")
def api_del_preset(pid: str):
    return presets.del_preset(pid)

# ---------- 一键流水线 ----------
@app.post("/api/pipeline/run")
def api_pipeline(p: PipelineIn):
    return pipeline.run(p.keyword, p.platform, p.model_id or None, p.template_id,
                        p.real_data, p.account, p.auto_cover, p.auto_push, p.product_ids,
                        writing_cfg=p.writing)

# ---------- 关键词 / 产品库 ----------
@app.get("/api/keywords")
def api_keywords():
    return {"keywords": keywords.list_keywords(), "groups": keywords.groups(),
            "intents": keywords.INTENTS}

@app.post("/api/keywords")
def api_add_keyword(k: KeywordIn):
    return keywords.add_keyword(k.dict())

@app.put("/api/keywords/{kid}")
def api_update_keyword(kid: str, patch: dict = Body(...)):
    return keywords.update_keyword(kid, patch)

@app.delete("/api/keywords/{kid}")
def api_del_keyword(kid: str):
    return keywords.del_keyword(kid)

@app.post("/api/keywords/expand")
def api_expand_keywords(e: ExpandIn):
    return keywords.expand(e.seed, e.model_id or None, e.n)

# ---------- 产品库 ----------
@app.get("/api/products")
def api_products(category: str = "", q: str = ""):
    return {"products": products.list_products(category, q),
            "categories": products.categories()}

@app.post("/api/products")
def api_add_product(p: ProductIn):
    return products.add_product(p.dict())

@app.put("/api/products/{pid}")
def api_update_product(pid: str, patch: dict = Body(...)):
    # 用 dict 接：只改传过来的字段，前端改一个价格不用把整个产品都回传
    return products.update_product(pid, patch)

@app.delete("/api/products/{pid}")
def api_del_product(pid: str):
    return products.del_product(pid)

@app.get("/api/products/match")
def api_match_products(q: str = "", ids: str = ""):
    """预览：出稿时会给模型注入哪几个产品的哪些卖点。"""
    ctx, meta = products.build_context(q, ids)
    return {"context": ctx, "products": meta}

# ---------- 知识库 ----------
@app.get("/api/knowledge")
def api_knowledge():
    return {"docs": knowledge.list_docs()}

@app.get("/api/knowledge/search")
def api_knowledge_search(q: str = "", top: int = 3):
    """检索测试：看看出稿时会给模型注入哪些段落。"""
    return {"hits": knowledge.search(q, top)}

@app.get("/api/knowledge/{did}")
def api_knowledge_doc(did: str):
    return knowledge.get_doc(did) or {"error": "not_found"}

@app.post("/api/knowledge")
def api_add_doc(d: DocIn):
    return knowledge.add_doc(d.dict())

@app.post("/api/knowledge/import")
def api_import_doc(d: DocImportIn):
    """导入文件建库：支持 PDF / docx / xlsx / txt / md / csv。"""
    try:
        raw = base64.b64decode(d.content_b64)
    except Exception:
        return {"error": "bad_b64", "message": "文件内容不是合法的 base64"}
    return knowledge.import_file(d.filename, raw, d.tags)

@app.delete("/api/knowledge/{did}")
def api_del_doc(did: str):
    return knowledge.del_doc(did)

# ---------- 账号定位（人设） ----------
@app.get("/api/personas")
def api_personas():
    return {"personas": personas.list_personas()}

@app.post("/api/personas")
def api_add_persona(p: PersonaIn):
    return personas.add_persona(p.dict())

@app.put("/api/personas/{pid}")
def api_update_persona(pid: str, patch: dict = Body(...)):
    return personas.update_persona(pid, patch)

@app.delete("/api/personas/{pid}")
def api_del_persona(pid: str):
    return personas.del_persona(pid)

# ---------- 素材库（内容中心） ----------
@app.get("/api/snippets")
def api_snippets(platform: str = "", tag: str = ""):
    return {"snippets": snippets.list_snippets(platform, tag)}

@app.post("/api/snippets")
def api_add_snippet(s: SnippetIn):
    return snippets.add_snippet(s.dict())

@app.delete("/api/snippets/{sid}")
def api_del_snippet(sid: str):
    return snippets.del_snippet(sid)

# ---------- 模板市场 ----------
@app.get("/api/templates")
def api_templates(platform: str = ""):
    return {"templates": templates.list_templates(platform)}

@app.post("/api/templates")
def api_add_template(t: TemplateIn):
    return templates.add_template(t.dict())

@app.put("/api/templates/{tid}")
def api_update_template(tid: str, patch: dict = Body(...)):
    return templates.update_template(tid, patch)

@app.delete("/api/templates/{tid}")
def api_del_template(tid: str):
    return templates.del_template(tid)

# ---------- 接口 / Webhook ----------
@app.get("/api/webhooks")
def api_hooks():
    return {"hooks": webhooks.list_hooks(), "events": webhooks.EVENTS}

@app.post("/api/webhooks")
def api_add_hook(h: HookIn):
    return webhooks.add_hook(h.dict())

@app.post("/api/webhooks/{hid}/toggle")
def api_toggle_hook(hid: str):
    return webhooks.toggle_hook(hid)

@app.post("/api/webhooks/{hid}/test")
def api_test_hook(hid: str):
    return webhooks.test_hook(hid)

@app.delete("/api/webhooks/{hid}")
def api_del_hook(hid: str):
    return webhooks.del_hook(hid)

# ---------- 百度收录检测 ----------
@app.post("/api/index-check")
def api_index_check(c: IndexCheckIn):
    return index_check.check(c.urls)

@app.get("/api/index-check")
def api_index_history():
    return {"history": index_check.history()}

# ---------- 数据中心 ----------
@app.get("/api/datacenter")
def api_datacenter(days: int = 30, platform: str = "", status: str = "", q: str = ""):
    return stats.datacenter(days, platform, status, q)

# ---------- 违禁词 ----------
@app.post("/api/check")
def api_check(c: CheckIn):
    return {"matches": banned_words.check_text(c.text, c.platform or None)}

@app.get("/api/banned-words")
def api_words(platform: str = ""):
    # 带 platform 参数 → 返回合并词库（检测用）；不带 → 返回完整词库结构（管理页用）
    if platform:
        return {"words": banned_words.load_words(platform)}
    return {
        "common": banned_words.load_words(),
        "platform": banned_words.load_platform_words(),
        "tips": banned_words.platform_tips(),
    }

@app.post("/api/banned-words")
def api_add_word(w: WordIn):
    return banned_words.add_word(w.word, w.platform)

@app.delete("/api/banned-words")
def api_del_word(word: str = "", platform: str = ""):
    return banned_words.del_word(word, platform)

# ---------- 配图 ----------
@app.post("/api/images")
def api_images(i: ImageIn):
    cfg = config.get_config(mask_secrets=False)
    return images.generate_cover(
        i.keyword, i.platform, i.article_text,
        cfg["IMAGE_API_BASE"], cfg["IMAGE_API_KEY"], cfg["IMAGE_MODEL"],
        note_cfg=i.writing,
    )

# ---------- 热点选题 ----------
@app.get("/api/topics")
def api_topics():
    return {"topics": topics.list_topics()}

@app.post("/api/topics")
def api_add_topic(t: TopicIn):
    return topics.add_topic(t.keyword, t.source, t.note)

@app.delete("/api/topics/{tid}")
def api_del_topic(tid: str):
    return topics.del_topic(tid)

@app.post("/api/topics/recommend")
def api_recommend(seed: str = ""):
    # 不传密钥/模型：topics 内部会取「当前生效模型」，全局一套配置
    return topics.recommend(seed)

# ---------- 多账号矩阵 ----------
@app.get("/api/accounts")
def api_accounts(platform: str = ""):
    return {"accounts": accounts.list_accounts(platform or None)}

@app.post("/api/accounts")
def api_add_account(a: AccountIn):
    return accounts.add_account(a.platform, a.name, a.url, a.note, a.is_default)

@app.put("/api/accounts/{aid}")
def api_update_account(aid: str, body: dict):
    """改账号信息 / 发布预设（tags·category·visibility·cover·extra）。"""
    return accounts.update_account(aid, body)

@app.post("/api/accounts/default")
def api_set_default(body: dict):
    return accounts.set_default(body.get("id", ""))

@app.delete("/api/accounts/{aid}")
def api_del_account(aid: str):
    return accounts.del_account(aid)

# ---------- 定时发布 / 自动化 ----------
@app.get("/api/schedule")
def api_schedule():
    return {"schedule": schedule.list_schedule()}

@app.get("/api/schedule/due")
def api_due():
    return {"due": schedule.due_list()}

@app.post("/api/schedule")
def api_add_schedule(s: ScheduleIn):
    return schedule.add_schedule(s.article_id, s.platform, s.account, s.planned_at, s.note)

@app.post("/api/schedule/{sid}/done")
def api_done(sid: str):
    return schedule.done_schedule(sid)

@app.delete("/api/schedule/{sid}")
def api_del_schedule(sid: str):
    return schedule.del_schedule(sid)

# ---------- 推送 ----------
@app.post("/api/push")
def api_push(p: PushIn):
    handler = baidu_push.PUSH_HANDLERS.get(p.platform)
    if not handler:
        return {"error": "unsupported",
                "message": f"平台 {p.platform} 暂不支持自动推送（社交平台走半自动引导，见发布页）"}
    if p.platform == "baidu":
        # 同样要拿真实 token，掩码值发到百度必然报 token 无效
        cfg = config.get_config(mask_secrets=False)
        return handler(cfg["BAIDU_SITE"], cfg["BAIDU_TOKEN"], p.urls)
    return handler(p.urls)

# ---------- 文章管理 ----------
@app.get("/api/articles")
def api_articles():
    return articles.list_articles()

@app.post("/api/articles")
def api_add(a: dict):
    art = articles.add_article(a)
    # 存稿事件 → 通知已订阅的接口/Webhook
    webhooks.fire("article_created", {"article_id": art.get("id"), "title": art.get("title"),
                                      "platform": art.get("platform")})
    return art

@app.delete("/api/articles/{aid}")
def api_del(aid: str):
    # 删除只是移进回收站，误删可以恢复
    return articles.delete_article(aid)

# ---------- 回收站（走独立路径，避免和 /api/articles/{aid} 抢匹配）----------
@app.get("/api/trash")
def api_trash():
    return {"trash": articles.list_trash()}

@app.post("/api/trash/{aid}/restore")
def api_restore(aid: str):
    return articles.restore_article(aid)

@app.delete("/api/trash")
def api_purge_trash():
    return articles.purge_trash()

@app.post("/api/articles/{aid}/status")
def api_status(aid: str, body: dict):
    articles.update_status(aid, body.get("status", "pushed"))
    return {"ok": True}

# ---------- 打通百度真闭环：文章 → SEO 静态页 → 自动推送 ----------
@app.post("/api/articles/{aid}/export")
def api_export(aid: str):
    # 生成 SEO HTML 并写入 data/html/seo-{id}.html（供下载/部署到你的域名服务器）
    cfg = config.get_config(mask_secrets=False)
    return articles.export_article_html(aid, cfg.get("BAIDU_SITE", ""))

@app.get("/api/articles/{aid}/url")
def api_article_url(aid: str):
    # 返回该文章拼好的线上 URL，供前端发布弹层自动带出
    cfg = config.get_config(mask_secrets=False)
    url = articles.build_article_url(aid, cfg.get("BAIDU_SITE", ""))
    if not url:
        return {"url": "", "message": "请先在「站点配置」填写 BAIDU_SITE（已备案域名）"}
    return {"url": url}

@app.post("/api/articles/{aid}/push")
def api_push_article(aid: str):
    # 自动拼该文章 URL 并推送给百度（前提是域名+token 已配置）
    cfg = config.get_config(mask_secrets=False)
    site = cfg.get("BAIDU_SITE", "")
    token = cfg.get("BAIDU_TOKEN", "")
    if not site:
        return {"error": "missing_site",
                "message": "请先在「站点配置」填写 BAIDU_SITE（已备案域名）"}
    url = articles.build_article_url(aid, site)
    if not url:
        return {"error": "no_url", "message": "无法生成 URL，请检查 BAIDU_SITE 配置"}
    result = baidu_push.push_baidu(site, token, [url])
    # 推送成功（百度返回 success 且无 error）则把文章状态标记为已推送
    if isinstance(result, dict) and result.get("success") and not result.get("error"):
        articles.update_status(aid, "pushed")
        webhooks.fire("article_pushed", {"article_id": aid, "url": url, "platform": "baidu"})
    return result

# ---------- 统计数据（控制台 / 数据中心）----------
@app.get("/api/stats")
def api_stats():
    return stats.get_stats()

@app.get("/api/push-log")
def api_push_log():
    return {"log": baidu_push.get_log()}

# ---------- 托管前端 ----------
FRONTEND_DIR = os.path.join(os.path.dirname(__file__), "..", "frontend")
if os.path.isdir(FRONTEND_DIR):
    app.mount("/", StaticFiles(directory=FRONTEND_DIR, html=True), name="static")
