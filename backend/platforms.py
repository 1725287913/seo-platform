# platforms.py
# 全量平台注册表（数据驱动，不写死在逻辑里）
# 来源：对标 ALQQ/ALPP 的 20+ 平台能力，按合规红线做了分级：
#   - website 类（如百度自建站）：走官方 API，可全自动（auto）
#   - social 类（小红书/微博/抖音等）：模拟登录违规、有封号风险，本工具只做半自动引导（semi）
# 加平台 = 在这里加一条字典即可，前端 /api/platforms 自动渲染 tab，generate 自动用对应调性。

# 每个平台字段：
#   key            唯一标识
#   name           显示名
#   emoji          图标
#   type           website | social
#   mode           auto（全自动，仅百度）| semi（半自动引导，其余平台）
#   category       分类，用于前端分组
#   content        支持的内容形态：article / image / video
#   prompt         该平台写作调性（人设），出稿时拼进 system 指令
#   publish_url     半自动发布引导链接（去哪发）
PLATFORMS = [
    {
        "key": "baidu", "name": "百度", "emoji": "🔍", "type": "website", "mode": "auto",
        "category": "搜索引擎", "content": ["article"],
        "prompt": (
            "你是一名资深 SEO 内容写手，专门为『百度搜索』创作高质量、可被收录的文章。\n"
            "要求：\n"
            "1) 标题和小标题清晰，且与正文高度一致，严禁标题党；\n"
            "2) 正文必须有真实的信息增量、逻辑清晰、分段合理、可读性强；\n"
            "3) 关键词自然分布，密度约 3%，绝不堆砌；\n"
            "4) 必须基于用户提供的『真实参考资料』写作，不得编造数据或事实；\n"
            "5) 文末必须包含声明：『本内容由AI辅助生成，已人工校验』（百度 AIGC 收录规范要求）。\n"
            "请用 Markdown 输出，包含 # 标题、## 小标题 与正文段落，不要使用代码块包裹。"
        ),
        "publish_url": "https://ziyuan.baidu.com",
    },
    {
        "key": "toutiao", "name": "今日头条", "emoji": "📰", "type": "social", "mode": "semi",
        "category": "资讯", "content": ["article"],
        "prompt": (
            "你是一名今日头条爆文写手。要求：标题有吸引力但不夸张、开门见山；正文信息密度高、"
            "分段短、带小标题；语气客观有态度，适当加入数据或观点；结尾可引导讨论。"
            "严禁编造新闻事实，必须基于真实参考资料。输出 Markdown。"
        ),
        "publish_url": "https://mp.toutiao.com",
    },
    {
        "key": "baijiahao", "name": "百家号", "emoji": "🅱️", "type": "social", "mode": "semi",
        "category": "资讯", "content": ["article"],
        "prompt": (
            "你是百家号优质创作者。要求：结构清晰（引言-正文-总结）、语言通俗、适当配小标题；"
            "内容需有原创观点与信息增量，符合百度搜索收录偏好；结尾加『本内容由AI辅助生成，已人工校验』。"
            "输出 Markdown。"
        ),
        "publish_url": "https://baijiahao.baidu.com",
    },
    {
        "key": "weixin", "name": "公众号", "emoji": "💬", "type": "social", "mode": "semi",
        "category": "图文", "content": ["article"],
        "prompt": (
            "你是微信公众号资深编辑。要求：标题克制有质感、不标题党；开头有钩子；正文娓娓道来、"
            "段落短小、善用金句；语气亲切像朋友分享；结尾引导关注。基于真实资料，不夸大。"
            "输出 Markdown。"
        ),
        "publish_url": "https://mp.weixin.qq.com",
    },
    {
        "key": "zhihu", "name": "知乎", "emoji": "🧠", "type": "social", "mode": "semi",
        "category": "问答", "content": ["article"],
        "prompt": (
            "你是知乎高赞答主。要求：用『谢邀/先说结论』式开场；逻辑严密、分点论证、有论据；"
            "专业且有个人见解，适度抖机灵；避免情绪化与绝对化表述。基于真实资料作答。输出 Markdown。"
        ),
        "publish_url": "https://www.zhihu.com",
    },
    {
        "key": "xiaohongshu", "name": "小红书", "emoji": "📕", "type": "social", "mode": "semi",
        "category": "种草", "content": ["article", "image"],
        "prompt": (
            "你是小红书爆款博主。要求：标题带情绪/数字/痛点（如『3个方法搞定XX』）；正文口语化、"
            "大量换行、善用 emoji、加 1~3 个相关话题标签（#）；语气像闺蜜安利；结尾抛互动问题。"
            "严禁使用『最/第一/国家级』等违禁词。基于真实资料，不夸大功效。输出 Markdown。"
        ),
        "publish_url": "https://creator.xiaohongshu.com",
    },
    {
        "key": "weibo", "name": "微博", "emoji": "🐦", "type": "social", "mode": "semi",
        "category": "动态", "content": ["article"],
        "prompt": (
            "你是微博话题达人。要求：短平快、140字内说清重点；带 1~2 个 #话题#；语气鲜活有网感；"
            "可抛观点或资讯。基于真实资料，不造谣不引战。输出纯文本（不要 Markdown 标题）。"
        ),
        "publish_url": "https://weibo.com",
    },
    {
        "key": "douyin", "name": "抖音", "emoji": "🎵", "type": "social", "mode": "semi",
        "category": "短视频", "content": ["video", "article"],
        "prompt": (
            "你为抖音短视频写口播脚本。要求：前3秒抓眼球（冲突/疑问/反差）；口语化、节奏快、"
            "每句短；给出分镜提示；结尾引导点赞关注。基于真实资料，不夸大。输出含『【分镜】』与『【口播】』两节。"
        ),
        "publish_url": "https://creator.douyin.com",
    },
    {
        "key": "kuaishou", "name": "快手", "emoji": "⚡", "type": "social", "mode": "semi",
        "category": "短视频", "content": ["video"],
        "prompt": (
            "你为快手短视频写接地气口播稿。要求：老铁风格、真诚直接、痛点开场；口语化强；"
            "给出分镜与口播。基于真实资料。输出含『【分镜】』『【口播】』两节。"
        ),
        "publish_url": "https://cp.kuaishou.com",
    },
    {
        "key": "shipinhao", "name": "视频号", "emoji": "📺", "type": "social", "mode": "semi",
        "category": "短视频", "content": ["video"],
        "prompt": (
            "你为微信视频号写口播脚本。要求：开头点明价值；语言简洁有温度；适合转发朋友圈；"
            "给出分镜与口播。基于真实资料。输出含『【分镜】』『【口播】』两节。"
        ),
        "publish_url": "https://channels.weixin.qq.com",
    },
    {
        "key": "bilibili", "name": "B站", "emoji": "📼", "type": "social", "mode": "semi",
        "category": "中长视频", "content": ["video", "article"],
        "prompt": (
            "你是 B 站 UP 主。要求：标题有梗但不低俗；开头抛出看点；正文信息扎实、有梗有干货；"
            "结尾求三连。基于真实资料。输出含『【脚本要点】』与『【正文/文案】』两节。"
        ),
        "publish_url": "https://member.bilibili.com",
    },
    {
        "key": "sohu", "name": "搜狐号", "emoji": "🦊", "type": "social", "mode": "semi",
        "category": "资讯", "content": ["article"],
        "prompt": (
            "你是搜狐号作者。要求：结构清晰、语言平实、信息完整；适合门户读者；结尾加『本内容由AI辅助生成，已人工校验』。"
            "基于真实资料。输出 Markdown。"
        ),
        "publish_url": "https://mp.sohu.com",
    },
    {
        "key": "wangyi", "name": "网易号", "emoji": "🌊", "type": "social", "mode": "semi",
        "category": "资讯", "content": ["article"],
        "prompt": (
            "你是网易号作者。要求：观点鲜明、逻辑清楚、语言流畅；适合新闻资讯读者；"
            "基于真实资料。输出 Markdown。"
        ),
        "publish_url": "https://mp.163.com",
    },
    {
        "key": "jianshu", "name": "简书", "emoji": "📖", "type": "social", "mode": "semi",
        "category": "图文", "content": ["article"],
        "prompt": (
            "你是简书创作者。要求：文艺克制、重表达与思考；段落适中；适合随笔与干货混合；"
            "基于真实资料。输出 Markdown。"
        ),
        "publish_url": "https://www.jianshu.com",
    },
    {
        "key": "qiehao", "name": "企鹅号", "emoji": "🐧", "type": "social", "mode": "semi",
        "category": "资讯", "content": ["article"],
        "prompt": (
            "你是企鹅号（腾讯内容开放平台）作者。要求：结构清晰、通俗易懂、信息完整；"
            "基于真实资料。输出 Markdown。"
        ),
        "publish_url": "https://om.qq.com",
    },
    {
        "key": "dayu", "name": "大鱼号", "emoji": "🐟", "type": "social", "mode": "semi",
        "category": "资讯", "content": ["article"],
        "prompt": (
            "你是大鱼号（UC）作者。要求：标题吸睛不夸大；正文信息完整、分段清晰；"
            "基于真实资料。输出 Markdown。"
        ),
        "publish_url": "https://mp.dayu.com",
    },
    {
        "key": "douban", "name": "豆瓣", "emoji": "🟢", "type": "social", "mode": "semi",
        "category": "图文", "content": ["article"],
        "prompt": (
            "你是豆瓣写作者。要求：文艺、有个人视角、重感受与思考；避免营销腔；"
            "基于真实资料。输出 Markdown。"
        ),
        "publish_url": "https://www.douban.com",
    },
    {
        "key": "csdn", "name": "CSDN", "emoji": "💻", "type": "social", "mode": "semi",
        "category": "技术", "content": ["article"],
        "prompt": (
            "你是 CSDN 技术博主。要求：结构严谨（背景-方案-步骤-总结）；代码与文字结合；"
            "面向开发者、术语准确；基于真实资料。输出 Markdown（可含代码块）。"
        ),
        "publish_url": "https://editor.csdn.net",
    },
    {
        "key": "xueqiu", "name": "雪球", "emoji": "📈", "type": "social", "mode": "semi",
        "category": "财经", "content": ["article"],
        "prompt": (
            "你是雪球财经作者。要求：观点清晰、有数据支撑、风险提示到位；不荐股、不夸大收益；"
            "基于真实资料。输出 Markdown。"
        ),
        "publish_url": "https://xueqiu.com",
    },
]


# ---------- 发布格式规则（一键分发时按这里自动适配，对标小火花「自动适配各平台格式」）----------
# 一篇稿子分发到 N 个平台，每个平台的要求都不一样：标题长度、标签数量、正文形态。
# 这里定义规则，distribute.py 照着把同一篇稿子裁成各家"能直接粘进去"的形态。
#   title_max  标题字数上限（超出自动裁，裁到最后一个完整词）
#   body_max   正文形态的字数上限（0 = 不限；超了会裁到句末并在页面上提醒）
#   tags       建议话题标签数（0 = 不要标签）
#   body       markdown（保留结构）| plain（去格式，适合微博这类）| script（口播脚本）
FORMAT = {
    "baidu":       {"title_max": 30, "body_max": 0,   "tags": 0,  "body": "markdown", "note": "标题 30 字内，正文保留小标题"},
    "toutiao":     {"title_max": 30, "body_max": 0,   "tags": 0,  "body": "markdown", "note": "标题 30 字内，段落要短"},
    "baijiahao":   {"title_max": 40, "body_max": 0,   "tags": 0,  "body": "markdown", "note": "标题 8~40 字"},
    "weixin":      {"title_max": 64, "body_max": 0,   "tags": 0,  "body": "markdown", "note": "标题 64 字内，正文建议配图"},
    "zhihu":       {"title_max": 50, "body_max": 0,   "tags": 3,  "body": "markdown", "note": "可加 3 个话题"},
    "xiaohongshu": {"title_max": 20, "body_max": 900, "tags": 5,  "body": "plain",    "note": "标题 20 字内！正文多换行，末尾挂 5 个话题"},
    "weibo":       {"title_max": 30, "body_max": 110, "tags": 2,  "body": "plain",    "note": "整条 140 字内，带 1~2 个 #话题#"},
    "douyin":      {"title_max": 55, "body_max": 200, "tags": 5,  "body": "script",   "note": "文案 55 字内，口播脚本另存"},
    "kuaishou":    {"title_max": 55, "body_max": 200, "tags": 3,  "body": "script",   "note": "文案 55 字内"},
    "shipinhao":   {"title_max": 22, "body_max": 300, "tags": 3,  "body": "script",   "note": "文案 22 字内（很短）"},
    "bilibili":    {"title_max": 80, "body_max": 0,   "tags": 10, "body": "markdown", "note": "标题 80 字内，标签可挂 10 个"},
    "sohu":        {"title_max": 30, "body_max": 0,   "tags": 0,  "body": "markdown", "note": "标题 30 字内"},
    "wangyi":      {"title_max": 30, "body_max": 0,   "tags": 0,  "body": "markdown", "note": "标题 30 字内"},
    "jianshu":     {"title_max": 50, "body_max": 0,   "tags": 4,  "body": "markdown", "note": "可加 4 个专题/标签"},
    "qiehao":      {"title_max": 30, "body_max": 0,   "tags": 0,  "body": "markdown", "note": "标题 30 字内"},
    "dayu":        {"title_max": 30, "body_max": 0,   "tags": 0,  "body": "markdown", "note": "标题 30 字内"},
    "douban":      {"title_max": 50, "body_max": 0,   "tags": 3,  "body": "markdown", "note": "可加 3 个标签"},
    "csdn":        {"title_max": 60, "body_max": 0,   "tags": 5,  "body": "markdown", "note": "可加 5 个标签，保留代码块"},
    "xueqiu":      {"title_max": 40, "body_max": 0,   "tags": 2,  "body": "markdown", "note": "可加 2 个 $股票代码$ 标签"},
}

# 兜底规则：FORMAT 里没写的平台按这个来
FORMAT_DEFAULT = {"title_max": 30, "body_max": 0, "tags": 0, "body": "markdown", "note": ""}


def get_format(key):
    """取某平台的发布格式规则（没有就用兜底）。"""
    return FORMAT.get(key, FORMAT_DEFAULT)


def get_platform(key):
    """按 key 取平台配置，找不到返回百度（兜底）。"""
    for p in PLATFORMS:
        if p["key"] == key:
            return p
    return PLATFORMS[0]


def get_prompt(key):
    """取某平台的写作调性指令（出稿用）。"""
    return get_platform(key)["prompt"]


def list_platforms():
    """返回前端用的精简列表（含 mode 用于决定是否显示『敬请期待』）。"""
    return [
        {
            "key": p["key"], "name": p["name"], "emoji": p["emoji"],
            "type": p["type"], "mode": p["mode"], "category": p["category"],
            "content": p["content"], "publish_url": p["publish_url"],
            "format": get_format(p["key"]),   # 一键分发时按它适配标题/标签/正文
            "enabled": True,  # 全部可点；auto 才走真推送，semi 走半自动引导
        }
        for p in PLATFORMS
    ]
