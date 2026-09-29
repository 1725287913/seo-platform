# writing.py
# 「写作配置」的单一事实来源：所有可调项的选项定义 + 把配置翻译成 prompt。
#
# 设计原则：这里定义什么，前端就能调什么。想加一个可调项，只改这个文件：
#   1) 在 OPTIONS 里加一组 {key, name, note, items}
#   2) 在 build_prompt() 里加一行把它翻译成人话喂给模型
# 前端通过 GET /api/writing-options 自动拿到全部选项，不用改前端代码。
import re

# ---------- 可调项定义（前端「写作配置」面板就是照着这个渲染的）----------
OPTIONS = [
    {
        "key": "style", "name": "文章风格", "type": "select", "default": "soft",
        "note": "决定整篇的调性，选完下面会显示这个风格的写法要点",
        "items": [
            {"key": "soft", "name": "软文推广", "note": "痛点切入，自然种草，不生硬推销"},
            {"key": "guide", "name": "干货科普", "note": "知识密度高，条理清晰，少废话"},
            {"key": "news", "name": "新闻资讯", "note": "客观第三人称陈述，不带主观推销"},
            {"key": "story", "name": "故事叙述", "note": "用真实经历串场，代入感强"},
            {"key": "review", "name": "对比评测", "note": "多维度客观对比，说清优劣再给建议"},
            {"key": "faq", "name": "问答合集", "note": "一问一答，贴着真实搜索问法写"},
            {"key": "report", "name": "行业观察", "note": "讲趋势、讲数据、讲原因，偏专业"},
            {"key": "promo", "name": "促销活动", "note": "突出优惠力度与行动号召"},
            {"key": "custom", "name": "自定义", "note": "用下面的「自定义补充要求」自己定风格"},
        ],
    },
    {
        "key": "audience", "name": "目标受众", "type": "select", "default": "",
        "note": "写给谁看，决定用词深浅和举例方式",
        "items": [
            {"key": "", "name": "不限（通用受众）", "note": "谁看都能读，不预设背景"},
            {"key": "本地居民", "name": "本地居民", "note": "强调本地地名、距离、到店体验"},
            {"key": "新手小白", "name": "新手小白", "note": "少用术语，多解释，多打比方"},
            {"key": "有经验的从业者", "name": "有经验的从业者", "note": "可以讲细节和行业门道"},
            {"key": "企业采购决策人", "name": "企业采购决策人", "note": "关注成本、合规、售后与交付"},
            {"key": "家庭用户", "name": "家庭用户", "note": "关注安全、省心、性价比"},
            {"key": "价格敏感型", "name": "价格敏感型", "note": "把价格构成和怎么省钱讲透"},
            {"key": "学生党", "name": "学生党", "note": "预算有限，语气轻松"},
        ],
    },
    {
        "key": "industry", "name": "行业领域", "type": "text", "default": "",
        "note": "比如「家政保洁」「装修」「汽车保养」——填了模型举例会更贴行业，不填则自动从关键词推断",
    },
    {
        "key": "word_count", "name": "文章字数", "type": "slider", "default": 1200,
        "min": 300, "max": 3000, "step": 100,
        "note": "0 = 不限字数；建议 SEO 文章 1000~2000 字，太短百度容易判为内容稀薄",
    },
    {
        "key": "language", "name": "生成语言", "type": "segment", "default": "zh-Hans",
        "note": "标题与正文的输出语言",
        "items": [
            {"key": "zh-Hans", "name": "简体中文"},
            {"key": "zh-Hant", "name": "繁体中文"},
            {"key": "en", "name": "English"},
            {"key": "ja", "name": "日本語"},
        ],
    },
    {
        "key": "title_kw", "name": "标题必含关键词", "type": "text", "default": "",
        "note": "逗号分隔，标题里必须出现这些词，比如「南京保洁,上门」",
    },
    {
        "key": "structure", "name": "结构模板（自由填写）", "type": "textarea", "default": "",
        "note": "自定义文章骨架，比如「痛点→原因→方案→效果→行动号召」。填了会覆盖上面选的模板",
    },
    {
        "key": "custom", "name": "自定义补充要求", "type": "textarea", "default": "",
        "note": "想让它怎么写就写在这，会原样追加成写作要求。比如「必须提到我们是本地门店，不能提竞品名」",
    },
    {
        "key": "temperature", "name": "创意度", "type": "slider", "default": 0.8,
        "min": 0.1, "max": 1.5, "step": 0.1,
        "note": "低=稳定保守（适合干货/资讯），高=更活更有想法（适合故事/种草）",
    },
    {
        "key": "deai", "name": "自动去 AI 味", "type": "switch", "default": True,
        "note": "开启后会追加去 AI 味的改写要求，读起来更像真人分享，降低被百度判为机器稿的概率",
    },
    {
        "key": "use_knowledge", "name": "调用知识库", "type": "switch", "default": True,
        "note": "关闭则不使用知识库检索结果，只用关键词和参考资料",
    },
    {
        "key": "generic", "name": "通用写法（不针对平台）", "type": "switch", "default": False,
        "note": "开启后不套用平台调性，写成一篇到哪都能发的通用稿",
    },
]

# 图片策略（配图专用，独立一张卡片）
IMAGE_OPTIONS = [
    {
        "key": "image_strategy", "name": "图片策略", "type": "segment", "default": "mix",
        "note": "出稿后配图时怎么挑图",
        "items": [
            {"key": "mix", "name": "智能混合", "note": "有产品图就搭产品图，没有就用网络配图/AI 生图"},
            {"key": "product", "name": "产品图优先", "note": "只用产品库里的真实图片"},
            {"key": "web", "name": "网络配图", "note": "生成可检索的网络配图关键词"},
            {"key": "ai", "name": "AI 生图", "note": "生成 AI 绘画提示词，交给文生图模型"},
        ],
    },
    {
        "key": "image_density", "name": "配图密度", "type": "segment", "default": "standard",
        "note": "按字数决定配几张图",
        "items": [
            {"key": "few", "name": "少", "note": "约每 800 字一张"},
            {"key": "standard", "name": "标准", "note": "约每 400 字一张"},
            {"key": "many", "name": "多", "note": "约每 200 字一张"},
        ],
    },
    {
        "key": "image_watermark", "name": "配图建议加水印/品牌名", "type": "switch", "default": False,
        "note": "开启后提示词里会带上品牌落款要求",
    },
]

ALL_OPTIONS = OPTIONS + IMAGE_OPTIONS

# 语言 key → 给模型看的说法
LANG_NAME = {"zh-Hans": "简体中文", "zh-Hant": "繁体中文", "en": "英文（English）", "ja": "日文（日本語）"}

# 配图密度 → 多少字一张图
DENSITY_PER = {"few": 800, "standard": 400, "many": 200}


def defaults():
    """所有可调项的默认值，前端初始化 / 后端兜底都用它。"""
    return {o["key"]: o["default"] for o in ALL_OPTIONS}


def _item_of(key, value):
    """在某一组选项里按 key 找条目（用来取它的中文名和人话说明）。"""
    for o in ALL_OPTIONS:
        if o["key"] == key:
            for it in o.get("items") or []:
                if it["key"] == value:
                    return it
    return None


def normalize(cfg: dict):
    """把前端传来的配置洗干净：丢掉不认识的值、类型转对、范围夹紧。"""
    cfg = cfg or {}
    out = defaults()
    known = {o["key"] for o in ALL_OPTIONS}
    for k, v in cfg.items():
        if k not in known:
            continue
        out[k] = v

    # 数值范围夹紧，防止前端乱传把模型搞崩
    try:
        wc = int(float(out.get("word_count") or 0))
    except Exception:
        wc = 1200
    out["word_count"] = max(0, min(3000, wc))
    try:
        tp = float(out.get("temperature") or 0.8)
    except Exception:
        tp = 0.8
    out["temperature"] = max(0.1, min(1.5, round(tp, 2)))

    # 布尔项统一成真布尔
    for k in ("deai", "use_knowledge", "generic", "image_watermark"):
        v = out.get(k)
        out[k] = bool(v) if not isinstance(v, str) else v.lower() in ("1", "true", "yes", "on")
    return out


def build_prompt(cfg: dict):
    """把写作配置翻译成喂给模型的「写作要求」段落。没配任何东西就返回空串。"""
    c = normalize(cfg)
    lines = []

    style = _item_of("style", c["style"])
    if style and c["style"] != "soft":
        lines.append(f"文章风格：{style['name']}（{style['note']}）")

    if c.get("audience"):
        lines.append(f"目标受众：{c['audience']}")

    if c.get("industry"):
        lines.append(f"行业领域：{c['industry']}")

    if c.get("word_count"):
        n = c["word_count"]
        lines.append(f"篇幅要求：全文约 {n} 字（上下浮动不超过 15%），不要为凑字数注水")

    lang = c.get("language")
    if lang and lang != "zh-Hans":
        lines.append(f"输出语言：{LANG_NAME.get(lang, lang)}")

    if c.get("title_kw"):
        words = [w.strip() for w in re.split(r"[,，、\s]+", c["title_kw"]) if w.strip()]
        if words:
            lines.append("标题必须包含这些词：" + "、".join(words))

    if c.get("structure"):
        lines.append("结构要求（按这个骨架写）：" + c["structure"].replace("\n", " → "))

    if c.get("custom"):
        lines.append("自定义要求（必须遵守）：" + c["custom"])

    if not lines:
        return ""
    return "【写作配置】\n" + "\n".join("· " + x for x in lines)


def image_note(cfg: dict, word_count: int = 0):
    """给配图模块看的说明：策略 + 该配几张。"""
    c = normalize(cfg)
    per = DENSITY_PER.get(c.get("image_density", "standard"), 400)
    n = max(1, round((word_count or per) / per)) if word_count else 3
    strat = _item_of("image_strategy", c.get("image_strategy"))
    return {
        "strategy": c.get("image_strategy", "mix"),
        "strategy_name": strat["name"] if strat else "智能混合",
        "count": min(n, 8),
        "watermark": c.get("image_watermark", False),
    }
