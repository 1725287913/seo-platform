# templates.py
# 模板市场（对标 ALQQ 的「应用商店」）：写作模板 = 结构大纲 + 额外指令。
# 内置 6 个常用模板，可自定义增删，出稿时选用即可让模型按固定结构写。
import json, os, time, uuid

DATA = os.path.join(os.path.dirname(__file__), "data", "templates.json")

# 内置模板：outline=要求的结构，instruction=额外的写法要求
BUILTIN = [
    {
        "id": "tpl-seo-guide", "name": "SEO 干货教程", "category": "SEO",
        "platform": "",
        "outline": "痛点引入 → 分步骤讲解（3~5 步）→ 常见坑 → 总结",
        "instruction": "面向搜索用户，标题含关键词，小标题用 H2，步骤要具体可执行，最后给一句行动建议。",
        "builtin": True,
    },
    {
        "id": "tpl-local", "name": "本地生活探店/服务", "category": "本地",
        "platform": "",
        "outline": "场景体验 → 细节亮点 → 价格/服务说明 → 适合人群 → 地址指引",
        "instruction": "多用第一人称真实体验细节，写清楚位置和到达方式，不要夸张吹捧。",
        "builtin": True,
    },
    {
        "id": "tpl-review", "name": "产品评测对比", "category": "商业",
        "platform": "",
        "outline": "需求场景 → 对比维度表格 → 各自优劣 → 选购建议",
        "instruction": "至少 3 个对比维度，客观说明缺点，结尾给不同预算/需求的选择建议。",
        "builtin": True,
    },
    {
        "id": "tpl-faq", "name": "FAQ 问答合集", "category": "SEO",
        "platform": "",
        "outline": "开头一句话总结 → 8~12 个问答（问题做小标题）→ 结尾补充",
        "instruction": "问题要贴近真实搜索习惯（怎么办/多少钱/多久/哪个好），每问答案 80~200 字。",
        "builtin": True,
    },
    {
        "id": "tpl-tutorial", "name": "保姆级操作教程", "category": "教程",
        "platform": "",
        "outline": "准备工作 → 分步骤操作 → 效果验证 → 常见报错处理",
        "instruction": "步骤要编号，写清每个动作点哪里、填什么，遇到报错给替代方案。",
        "builtin": True,
    },
    {
        "id": "tpl-social-note", "name": "社媒种草笔记", "category": "社媒",
        "platform": "xiaohongshu",
        "outline": "吸睛开头一句 → 3~5 个亮点短句 → 真实使用感受 → 结尾话题标签",
        "instruction": "短句换行排版，口语化，emoji 适量，结尾给 5~8 个话题标签，禁止出现微信/引流词。",
        "builtin": True,
    },
]


def _read():
    if not os.path.exists(DATA):
        json.dump(BUILTIN, open(DATA, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
        return [dict(t) for t in BUILTIN]
    return json.load(open(DATA, encoding="utf-8"))


def _write(arr):
    json.dump(arr, open(DATA, "w", encoding="utf-8"), ensure_ascii=False, indent=2)


def list_templates(platform: str = ""):
    """平台筛选：通用模板（platform 为空）+ 该平台专属模板。"""
    arr = _read()
    if platform:
        return [t for t in arr if t.get("platform") in ("", platform)]
    return arr


def get(tid: str):
    return next((t for t in _read() if t.get("id") == tid), None)


def add_template(t: dict):
    arr = _read()
    name = (t.get("name") or "").strip()
    if not name:
        return {"error": "empty", "message": "模板名不能为空"}
    item = {
        "id": "tpl-" + str(uuid.uuid4())[:6],
        "name": name,
        "category": t.get("category") or "自定义",
        "platform": t.get("platform", ""),
        "outline": t.get("outline", ""),
        "instruction": t.get("instruction", ""),
        "builtin": False,
        "created_at": time.strftime("%Y-%m-%d %H:%M"),
    }
    arr.append(item)
    _write(arr)
    return item


def update_template(tid: str, patch: dict):
    arr = _read()
    for x in arr:
        if x.get("id") == tid:
            for f in ("name", "category", "platform", "outline", "instruction"):
                if f in patch and patch[f] is not None:
                    x[f] = patch[f]
    _write(arr)
    return {"ok": True}


def del_template(tid: str):
    arr = _read()
    t = next((x for x in arr if x.get("id") == tid), None)
    if t and t.get("builtin"):
        return {"error": "builtin", "message": "内置模板不可删除，可复制一份再改"}
    _write([x for x in arr if x.get("id") != tid])
    return {"ok": True}


def build_prompt(tid: str):
    """把模板转成要加进 prompt 的写作要求。"""
    t = get(tid)
    if not t:
        return ""
    lines = [f"【写作模板：{t['name']}】"]
    if t.get("outline"):
        lines.append(f"结构要求：{t['outline']}")
    if t.get("instruction"):
        lines.append(f"写法要求：{t['instruction']}")
    return "\n".join(lines)
