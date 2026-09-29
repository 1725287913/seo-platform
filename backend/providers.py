# providers.py
# AI 服务商注册表：用户只需选服务商 + 填 Key，地址和模型名自动带出来。
# 全部按 OpenAI 兼容格式调用（国内主流厂商 2026 年基本都兼容），所以一套代码通吃。
#
# 字段说明：
#   key        服务商唯一标识
#   name       显示名
#   short      卡片上的短标（做 logo 用，1~2 个字符）
#   group      cn=国内直连 / global=海外 / local=本地免注册
#   api_base   完整的 chat/completions 地址
#   key_env    密钥写到 .env 里的变量名
#   models     可选模型（第一个是默认值）；用户也可以自己改
#   site       申请 Key 的地址
#   note       给用户看的提示
#
# ⚠️ 模型名会随厂商更新而变（DeepSeek 就在 2026-07 停用了 deepseek-chat）。
#    所以界面上模型名是「下拉可选 + 可手输」，报 model not found 时去官网复制当前名称即可。

PROVIDERS = [
    # ---------------- 国内直连（推荐，不用梯子） ----------------
    {
        "key": "deepseek", "name": "DeepSeek 深度求索", "short": "DS", "group": "cn",
        "api_base": "https://api.deepseek.com/chat/completions",
        "key_env": "DEEPSEEK_API_KEY",
        "models": ["deepseek-flash", "deepseek-v4-pro"],
        "site": "https://platform.deepseek.com",
        "note": "中文写作最划算，便宜量大，SEO 出稿首选",
    },
    {
        "key": "siliconflow", "name": "硅基流动 SiliconFlow", "short": "SF", "group": "cn",
        "api_base": "https://api.siliconflow.cn/v1/chat/completions",
        "key_env": "SILICONFLOW_API_KEY",
        "models": ["deepseek-ai/DeepSeek-V3", "Qwen/Qwen2.5-72B-Instruct"],
        "site": "https://cloud.siliconflow.cn",
        "note": "一个 Key 用几十个开源模型，模型名要写「厂商/模型」全称；新用户送 ¥16 额度，控制台里标价 0 的模型可免费用",
    },
    {
        "key": "moonshot", "name": "月之暗面 Kimi", "short": "KM", "group": "cn",
        "api_base": "https://api.moonshot.cn/v1/chat/completions",
        "key_env": "MOONSHOT_API_KEY",
        "models": ["kimi-k2.6", "moonshot-v1-32k"],
        "site": "https://platform.moonshot.cn",
        "note": "长文本理解强，适合把长资料喂进去改写",
    },
    # ★ 测试期首选：国内直连 + 有长期免费模型，注册只要手机号
    {
        "key": "zhipu", "name": "智谱 AI GLM", "short": "GL", "group": "cn",
        "api_base": "https://open.bigmodel.cn/api/paas/v4/chat/completions",
        "key_env": "ZHIPU_API_KEY",
        "models": ["glm-4.5-flash", "glm-4.7-flash", "glm-4-flash", "glm-5.3"],
        "site": "https://open.bigmodel.cn",
        "note": "★免费：glm-4.5-flash / glm-4.7-flash / glm-4-flash 都是 0 元，限 1 并发、忙时报 429 需重试；glm-5.3 是旗舰按量收费（约 ¥8/百万输入），别误选",
    },
    {
        "key": "dashscope", "name": "阿里云百炼（通义千问）", "short": "QW", "group": "cn",
        "api_base": "https://dashscope.aliyuncs.com/compatible-mode/v1/chat/completions",
        "key_env": "DASHSCOPE_API_KEY",
        "models": ["qwen3.6-plus", "qwen-plus"],
        "site": "https://bailian.console.aliyun.com",
        "note": "新用户有免费额度，稳定",
    },
    {
        "key": "qianfan", "name": "百度千帆（文心一言）", "short": "WX", "group": "cn",
        "api_base": "https://qianfan.baidubce.com/v2/chat/completions",
        "key_env": "QIANFAN_API_KEY",
        "models": ["ernie-5.0", "ernie-4.0-turbo-8k"],
        "site": "https://console.bce.baidu.com/qianfan",
        "note": "做百度 SEO 的话，文心的语感更贴百度",
    },
    {
        "key": "volc", "name": "火山方舟（豆包）", "short": "DB", "group": "cn",
        "api_base": "https://ark.cn-beijing.volces.com/api/v3/chat/completions",
        "key_env": "VOLC_API_KEY",
        "models": ["doubao-seed-2-0-pro"],
        "site": "https://console.volcengine.com/ark",
        "note": "模型名要填「接入点 ID」（形如 ep-xxxx），不是模型名，去控制台创建",
    },
    {
        "key": "minimax", "name": "MiniMax", "short": "MM", "group": "cn",
        "api_base": "https://api.minimaxi.com/v1/chat/completions",
        "key_env": "MINIMAX_API_KEY",
        "models": ["MiniMax-M2.7"],
        "site": "https://platform.minimaxi.com",
        "note": "长文生成速度较快",
    },

    # ---------------- 海外（需能访问外网） ----------------
    {
        "key": "openai", "name": "OpenAI", "short": "OA", "group": "global",
        "api_base": "https://api.openai.com/v1/chat/completions",
        "key_env": "OPENAI_API_KEY",
        "models": ["gpt-4o-mini", "gpt-4o"],
        "site": "https://platform.openai.com/api-keys",
        "note": "需海外网络环境；国内直连会超时",
    },
    {
        "key": "gemini", "name": "Google Gemini", "short": "GM", "group": "global",
        "api_base": "https://generativelanguage.googleapis.com/v1beta/openai/chat/completions",
        "key_env": "GEMINI_API_KEY",
        "models": ["gemini-2.5-flash", "gemini-2.5-pro"],
        "site": "https://aistudio.google.com/apikey",
        "note": "有免费额度，需海外网络环境",
    },
    {
        "key": "groq", "name": "Groq", "short": "GQ", "group": "global",
        "api_base": "https://api.groq.com/openai/v1/chat/completions",
        "key_env": "GROQ_API_KEY",
        "models": ["llama-3.3-70b-versatile"],
        "site": "https://console.groq.com/keys",
        "note": "免费额度大、速度极快，需海外网络环境",
    },
    {
        "key": "openrouter", "name": "OpenRouter", "short": "OR", "group": "global",
        "api_base": "https://openrouter.ai/api/v1/chat/completions",
        "key_env": "OPENROUTER_API_KEY",
        "models": ["deepseek/deepseek-chat"],
        "site": "https://openrouter.ai/keys",
        "note": "一个 Key 调上百个模型，模型名格式「厂商/模型」；带 :free 后缀的模型免费（约 50 次/天）",
    },
    {
        "key": "zai", "name": "Z.ai（智谱国际站）", "short": "ZA", "group": "global",
        "api_base": "https://api.z.ai/api/paas/v4/chat/completions",
        "key_env": "ZAI_API_KEY",
        "models": ["glm-4.7-flash", "glm-4.5-flash"],
        "site": "https://z.ai/model-api",
        "note": "★只需邮箱注册，不用手机号也不用实名；glm-4.7-flash 永久 $0 免费（限 1 并发）。⚠️ 和国内 bigmodel.cn 的 Key 不通用，两边账号分开；国内访问速度可能不如国内站",
    },
    {
        "key": "githubmodels", "name": "GitHub Models", "short": "GH", "group": "global",
        "api_base": "https://models.github.ai/inference/chat/completions",
        "key_env": "GITHUB_MODELS_API_KEY",
        "models": ["openai/gpt-4.1", "openai/gpt-4o"],
        "site": "https://github.com/settings/tokens",
        "note": "有 GitHub 账号就能免费用 GPT 系：建 PAT 令牌时勾上 models:read 权限。限 150 次/天，单次输出上限 4K token（约 2500 字），长文会被截断",
    },

    # ---------------- 本地（完全免注册、免实名、不要网） ----------------
    {
        "key": "ollama", "name": "本地 Ollama", "short": "OL", "group": "local",
        "api_base": "http://localhost:11434/v1/chat/completions",
        "key_env": "OLLAMA_API_KEY",
        "models": ["qwen3:8b", "qwen3:4b"],
        "site": "https://ollama.com/download",
        "note": "★完全免费、不用注册、不联网。先装 Ollama 再 ollama pull qwen3:8b；8GB 显存跑 8b 最舒服（约 5GB）",
    },
    {
        "key": "lmstudio", "name": "本地 LM Studio", "short": "LM", "group": "local",
        "api_base": "http://localhost:1234/v1/chat/completions",
        "key_env": "LMSTUDIO_API_KEY",
        "models": ["local-model"],
        "site": "https://lmstudio.ai",
        "note": "图形界面装本地模型，启动后在设置里打开本地服务",
    },

    # ---------------- 兜底 ----------------
    {
        "key": "custom", "name": "自定义（任何 OpenAI 兼容接口）", "short": "＋", "group": "other",
        "api_base": "", "key_env": "CUSTOM_API_KEY", "models": [],
        "site": "", "note": "自己填接口地址和模型名，任何 OpenAI 兼容服务都能接",
    },
]

# 分组标题（前端按这个顺序展示）
GROUPS = [
    {"key": "cn", "label": "国内直连", "desc": "不用梯子，注册即用（多数需国内手机号）"},
    {"key": "global", "label": "海外服务", "desc": "需要能访问外网"},
    {"key": "local", "label": "本地运行", "desc": "完全免费，不用注册、不填 Key"},
    {"key": "other", "label": "其它", "desc": "手动填写接口"},
]


def list_providers():
    """给前端用：全部服务商（不含任何密钥）。"""
    return PROVIDERS


def get(pid):
    return next((p for p in PROVIDERS if p["key"] == pid), None)


def key_envs():
    """所有服务商的密钥变量名，config 用它动态生成白名单。"""
    return {p["key_env"] for p in PROVIDERS}


def key_env_of(pid):
    p = get(pid)
    return p["key_env"] if p else ""


def default_model(pid):
    p = get(pid)
    return (p["models"] or [""])[0] if p else ""


def guess_provider(api_base):
    """按接口地址反推服务商 key（迁移老配置用，反查不到返回 None）。"""
    if not api_base:
        return None
    host = api_base.split("//")[-1].split("/")[0].lower()
    for p in PROVIDERS:
        if p["api_base"] and host in p["api_base"]:
            return p["key"]
    return None
