# generate.py
# AI 出稿：调用大模型生成各平台文章 / 社媒短文案 / 视频脚本。
# 可叠加：平台调性 + 账号人设 + 写作配置 + 写作模板 + 知识库检索结果 + 产品卖点。
import httpx
import platforms
import models
import personas
import templates
import knowledge
import products
import writing

# 通用「去 AI 味 + 合规」追加指令（由写作配置里的「自动去 AI 味」开关控制）
ANTI_AI_FLAVOR = (
    "请尽量去掉『AI 味』：少用『首先/其次/综上所述』等套路词，少用排比口号，"
    "多用具体细节、真实案例、口语化表达，让文章读起来像真人有经验的分享。"
    "不得编造数据、不得出现『最/第一/国家级』等违禁极限词。"
)

# 通用写法（不针对平台）时用的基础人设
GENERIC_SYSTEM = "你是一位资深中文内容编辑，擅长写既对搜索引擎友好、又对读者真正有用的文章。"

# 社媒短内容：动态（图文短文案）
SOCIAL_POST_PROMPT = (
    "你是社媒运营。写一条可直接发布的短文案：开头一句抓人，中间 3~5 个短句亮点，"
    "结尾一句互动引导，最后给 5~8 个话题标签（用 # 开头）。"
    "短句换行排版，口语化，禁止出现微信/加微/引流等站外导流词。"
)

# 社媒短内容：视频脚本
SOCIAL_VIDEO_PROMPT = (
    "你是短视频编导。输出一份可直接开拍的脚本：\n"
    "1) 标题（含钩子）\n2) 前 3 秒开场白\n3) 分段口播稿（每段标出【画面对应建议】）\n"
    "4) 结尾引导（关注/评论）\n5) 5 个备选标题\n"
    "口播要口语化、有节奏，别写书面语。"
)


def _call_model(info, system, user, temperature=0.8, timeout=90):
    """统一调用 OpenAI 兼容端点，返回 {content, model} 或 {error, message}。"""
    try:
        resp = httpx.post(
            info["api_base"],
            headers={"Authorization": f"Bearer {info['api_key']}", "Content-Type": "application/json"},
            json={
                "model": info["model_name"],
                "messages": [
                    {"role": "system", "content": system},
                    {"role": "user", "content": user},
                ],
                "temperature": temperature,
            },
            timeout=timeout,
        )
        data = resp.json()
        # 有的厂商（智谱）出错时不用 error 字段，而是 {"code":500,"msg":"..."}，一并认出来
        if not isinstance(data, dict) or "choices" not in data:
            err = data.get("error") if isinstance(data, dict) else None
            msg = (err.get("message") or str(err)) if isinstance(err, dict) else err
            if not msg:
                msg = (data.get("msg") if isinstance(data, dict) else None) or str(data)
            return {"error": "api_error", "message": msg}
        return {"content": data["choices"][0]["message"].get("content") or "",
                "model": info["model_name"]}
    except Exception as e:
        return {"error": "request_failed", "message": str(e)}


def _resolve_or_error(model_id=None):
    info = models.resolve(model_id)
    if not info:
        return None, {"error": "no_model", "message": "没有可用模型，请先在「模型中心」添加或启用一个模型"}
    if not info["api_key"]:
        return None, {"error": "missing_key",
                      "message": f"模型 {info['model_name']} 所需的密钥（{info['key_env']}）未配置，请到「API 密钥」页填写"}
    return info, None


def generate_article(keyword, platform="baidu", model_id=None, real_data="",
                     topic="", template_id="", account="", use_knowledge=True,
                     product_ids="", writing_cfg=None):
    """生成平台文章。

    叠加顺序：平台调性 → 账号人设 → 写作配置 → 写作模板 → 知识库资料 → 产品卖点。
    writing_cfg 是「写作配置」面板传过来的字典（风格/受众/字数/语言/去AI味…），
    可调项定义见 writing.py 的 OPTIONS。
    """
    info, err = _resolve_or_error(model_id)
    if err:
        return err

    # 写作配置先洗净（丢未知字段、夹紧数值范围）
    cfg = writing.normalize(writing_cfg)

    # 「通用写法」开启时不套平台调性
    system = GENERIC_SYSTEM if cfg.get("generic") else platforms.get_prompt(platform)

    p = personas.build_prompt(platform, account)
    if p:
        system += "\n\n" + p

    # 结构：自由填写的结构优先；没填才用模板市场的模板
    tpl_text = ""
    if not cfg.get("structure"):
        tpl_text = templates.build_prompt(template_id)
        if tpl_text:
            system += "\n\n" + tpl_text

    w = writing.build_prompt(cfg)
    if w:
        system += "\n\n" + w

    user = f"写作主题：{keyword}\n"
    if topic:
        user += f"关联热点/话题：{topic}\n"

    # 知识库检索 + 产品库匹配：都作为「真实参考资料」喂给模型
    kb = ""
    if use_knowledge and cfg.get("use_knowledge", True):
        kb = knowledge.build_context(f"{keyword} {topic}")
    prod_ctx, prod_meta = products.build_context(f"{keyword} {topic}", product_ids)
    if kb or prod_ctx or real_data:
        user += "\n以下是真实参考资料（必须基于它写，不得虚构）：\n"
        if kb:
            user += kb + "\n"
        if prod_ctx:
            user += prod_ctx + "\n"
        if real_data:
            user += real_data + "\n"

    if cfg.get("deai", True):
        user += f"\n{ANTI_AI_FLAVOR}\n"
    user += "\n请直接输出文章正文。"

    out = _call_model(info, system, user, temperature=cfg.get("temperature", 0.8))
    if out.get("error"):
        return out
    out["used"] = {
        "persona": bool(p),
        "template": tpl_text.split("\n")[0].strip("【】") if tpl_text else "",
        "knowledge": bool(kb),
        "products": [x["name"] for x in prod_meta],
        "writing": _used_writing(cfg),
    }
    out["writing"] = cfg
    return out


def _used_writing(cfg):
    """把生效的写作配置翻成人话，给前端展示「这次是按什么配置写的」。"""
    parts = []
    style = next((i for o in writing.OPTIONS if o["key"] == "style"
                  for i in (o.get("items") or []) if i["key"] == cfg.get("style")), None)
    if style:
        parts.append(style["name"])
    if cfg.get("audience"):
        parts.append(f"受众：{cfg['audience']}")
    if cfg.get("word_count"):
        parts.append(f"{cfg['word_count']} 字")
    if cfg.get("language") and cfg["language"] != "zh-Hans":
        parts.append(writing.LANG_NAME.get(cfg["language"], cfg["language"]))
    if cfg.get("industry"):
        parts.append(f"行业：{cfg['industry']}")
    if cfg.get("deai", True):
        parts.append("已去 AI 味")
    if cfg.get("generic"):
        parts.append("通用写法")
    return "、".join(parts)


# ---------- 文章创作页的 AI 助手：对自己写的文字做二次加工 ----------
ASSIST_MODES = {
    "polish":   "把下面这段文字润色通顺：保持原意与全部信息，不要新增事实，不要改标题层级",
    "expand":   "把下面这段文字扩写得更充实：补充具体细节、数字、例子，信息密度要高，禁止写空话套话",
    "shorten":  "把下面这段文字精简：删掉重复与空话，保留全部关键信息",
    "deai":     "去掉下面这段文字的『AI 味』：删掉套路词与排比口号，替换成具体细节和口语化表达，原意不变",
    "seo":      "把下面这段文字改得更符合搜索引擎习惯：核心关键词自然融入标题与小标题，段落清晰，但不要堆砌关键词",
    "continue": "接着下面这段文字继续往下写，保持同样的语气与风格，不要重复已有内容",
    "title":    "根据下面这段文字，给出 5 个标题：一个一行，适合中文搜索与社媒，直接输出标题本身",
    "outline":  "根据下面这段文字，整理出一份文章大纲：用 Markdown 的 ## 二级标题列出来，每条后面用一句话说明要写什么",
}


def assist(text, mode="polish", instruction=""):
    """对用户自己写的文字做润色/扩写/精简/去AI味/续写/起标题。"""
    info, err = _resolve_or_error(None)
    if err:
        return err
    if not (text or "").strip():
        return {"error": "empty", "message": "先把要处理的文字填进来"}

    task = ASSIST_MODES.get(mode) or ASSIST_MODES["polish"]
    system = "你是资深中文内容编辑。直接输出处理后的文字本身，不要解释、不要加任何前后缀说明。"
    user = f"{task}：\n\n{text}"
    if instruction:
        user += f"\n\n额外要求：{instruction}"

    out = _call_model(info, system, user, temperature=0.7)
    if out.get("error"):
        return out
    return {"content": out.get("content") or "", "model": out.get("model"), "mode": mode}


def generate_social(kind, platform, keyword, model_id=None, real_data="", account="",
                    writing_cfg=None):
    """生成社媒短内容。kind: post(动态图文) / video(视频脚本)。"""
    info, err = _resolve_or_error(model_id)
    if err:
        return err

    cfg = writing.normalize(writing_cfg)
    system = platforms.get_prompt(platform) + "\n\n" + (
        SOCIAL_POST_PROMPT if kind == "post" else SOCIAL_VIDEO_PROMPT)
    p = personas.build_prompt(platform, account)
    if p:
        system += "\n\n" + p
    w = writing.build_prompt(cfg)
    if w:
        system += "\n\n" + w

    user = f"主题/关键词：{keyword}\n"
    if real_data:
        user += f"\n真实素材（必须基于它写，不得虚构）：\n{real_data}\n"
    if cfg.get("deai", True):
        user += f"\n{ANTI_AI_FLAVOR}\n"
    user += "\n请直接输出可发布的内容。"

    out = _call_model(info, system, user, temperature=cfg.get("temperature", 0.9))
    if out.get("error"):
        return out
    out["kind"] = kind
    out["writing"] = cfg
    return out
