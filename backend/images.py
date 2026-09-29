# images.py
# 配图：按文章生成封面图提示词，并尽可能**直接出图**。
#
# 出图通道按优先级自动挑，不用用户额外配置：
#   ① 自己配的 OpenAI 兼容图 API（.env 里 IMAGE_API_BASE + IMAGE_API_KEY）
#   ② 智谱 CogView —— 直接复用已有的智谱 key，`cogview-3-flash` 免费
# 两个都没有时，只返回提示词（半自动：复制到任意绘图工具出图）。
#
# 出的图一律**下载存到本地** `data/images/`：第三方 URL 会过期，
# 存本地才能保证文章里的图一直在。
import base64
import os
import time
import uuid

import httpx

# 图片落盘目录 + 对外访问前缀
_IMG_DIR = os.path.join(os.path.dirname(__file__), "data", "images")
_URL_PREFIX = "/api/images/file/"

# 智谱文生图
ZHIPU_IMG_URL = "https://open.bigmodel.cn/api/paas/v4/images/generations"
ZHIPU_IMG_MODEL = "cogview-3-flash"   # 免费；质量更好可换 cogview-4（收费）

# 各平台封面尺寸（用智谱支持的合法比例；用户传了 size 就以用户为准）
SIZE_MAP = {
    "xiaohongshu": "864x1152",   # 3:4 竖版
    "douyin": "720x1440",        # 9:16 竖版
    "kuaishou": "720x1440",
    "shipinhao": "720x1440",
    "weixin": "1440x720",        # 2:1 横版封面
    "bilibili": "1344x768",
    "zhihu": "1344x768",
}
SIZE_DEFAULT = "1024x1024"


def img_dir():
    """确保图片目录存在并返回路径。"""
    os.makedirs(_IMG_DIR, exist_ok=True)
    return _IMG_DIR


def build_cover_prompt(keyword, platform, article_text=""):
    """根据主题/平台/正文，拼一个适合该平台的封面图提示词。"""
    style_map = {
        "xiaohongshu": "ins 风、明亮清新、低饱和、有氛围感、适合种草封面",
        "douyin": "高对比、鲜艳、抓眼球、短视频封面风",
        "weixin": "简洁高级、留白多、公众号封面风",
        "zhihu": "理性、信息图感、蓝白配色",
        "baidu": "商务简洁、搜索引擎配图风、清晰主题",
    }
    style = style_map.get(platform, "通用自媒体封面风格、清晰主体、构图干净")
    head = (article_text.split("\n", 1)[0] or keyword)[:40]
    return (
        f"一张关于「{keyword}」的社媒封面图，{style}。"
        f"画面主体明确，不要过多文字，可含少量标题感元素。参考文案主题：{head}"
    )


def _ext_from(ctype, url):
    """从 content-type 或 URL 猜图片扩展名。"""
    ctype = (ctype or "").lower()
    for k, v in (("jpeg", "jpg"), ("jpg", "jpg"), ("webp", "webp"), ("gif", "gif")):
        if k in ctype:
            return v
    return "png"


def _save_image(raw, ctype="", url=""):
    """把图片字节存到本地，返回相对访问地址 /api/images/file/xxx.png。"""
    img_dir()
    name = f"{time.strftime('%Y%m%d%H%M%S')}-{uuid.uuid4().hex[:8]}.{_ext_from(ctype, url)}"
    with open(os.path.join(_IMG_DIR, name), "wb") as f:
        f.write(raw)
    return _URL_PREFIX + name


def _fetch_to_local(img_url):
    """把远程图片抓回来存本地；失败则原样返回远程地址（聊胜于无）。"""
    r = httpx.get(img_url, timeout=120, follow_redirects=True)
    r.raise_for_status()
    return _save_image(r.content, r.headers.get("content-type", ""), img_url)


def _pick_route(api_base, api_key, model):
    """决定用哪条通道出图。返回 (通道名, 接口地址, key, 模型名)。"""
    if api_base and api_key:
        return ("custom", api_base, api_key, model or "default")

    # 没配图 API，就用智谱的 key（用户已经在用的那一把）
    try:
        import config
        key = (config.get_config(mask_secrets=False) or {}).get("ZHIPU_API_KEY", "")
    except Exception:
        key = ""
    if key:
        return ("zhipu", ZHIPU_IMG_URL, key, ZHIPU_IMG_MODEL)

    return ("", "", "", "")


def generate_cover(keyword, platform, article_text="", api_base="", api_key="", model="",
                   size="", note_cfg=None):
    """生成封面图。有可用通道就直接出图并存本地；没有则只给提示词。

    note_cfg 来自写作配置里的「图片策略/配图密度」，影响提示词描述。
    """
    import writing
    prompt = build_cover_prompt(keyword, platform, article_text)
    size = size or SIZE_MAP.get(platform, SIZE_DEFAULT)

    # 把图片策略/配图密度翻成提示词补充说明
    img_note = None
    if note_cfg:
        img_note = writing.image_note(note_cfg, len(article_text or ""))
        if img_note.get("strategy") == "product":
            prompt += "。优先使用产品实拍图，不要虚构不存在的产品外观。"
        elif img_note.get("strategy") == "web":
            prompt += "。给出适合在图库检索的配图关键词。"
        elif img_note.get("strategy") == "ai":
            prompt += "。用于 AI 文生图，画面要具体可描述。"
        if img_note.get("watermark"):
            prompt += " 画面留出角落位置用于放品牌名/水印。"

    result = {"prompt": prompt, "size": size, "image_url": None, "local": False,
              "source": "", "note": "已生成配图提示词，可手动用任一 AI 绘图工具出图"}
    if img_note:
        result["image_plan"] = img_note   # 建议配几张、什么策略

    kind, url, key, mdl = _pick_route(api_base, api_key, model)
    if not kind:
        result["note"] = ("还没配置出图通道，已生成提示词。"
                          "在「API 密钥」里配好智谱（免费出图）或自定义图 API 即可自动出图")
        return result

    result["source"] = kind
    try:
        resp = httpx.post(
            url,
            headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
            # 智谱与 OpenAI 兼容接口的请求体一致，字段取并集即可
            json={"model": mdl, "prompt": prompt, "size": size, "n": 1},
            timeout=180,
        )
        data = resp.json()
        if resp.status_code != 200 or not data.get("data"):
            msg = (data.get("error") or {}).get("message") or str(data)[:200]
            result["note"] = f"出图失败：{msg}"
            return result

        item = data["data"][0] or {}
        src = item.get("url")
        if src:
            # 抓回本地，防第三方链接过期
            try:
                result["image_url"] = _fetch_to_local(src)
                result["local"] = True
            except Exception:
                result["image_url"] = src
        elif item.get("b64_json"):
            raw = base64.b64decode(item["b64_json"])
            result["image_url"] = _save_image(raw)
            result["local"] = True

        if result["image_url"]:
            tip = "已出图并保存到本机" + ("（图片自带右下角水印，免费模型去不掉）"
                                    if kind == "zhipu" else "")
            result["note"] = tip
        else:
            result["note"] = "接口没返回图片，已保留提示词"
    except Exception as e:
        result["note"] = f"出图失败（{type(e).__name__}: {e}），已保留提示词"
    return result
