# images.py
# 配图：根据文章生成「封面图方案」（提示词 + 尺寸建议）
# 若配置了 IMAGE_API_BASE/IMAGE_API_KEY（OpenAI 兼容图像接口，如 SiliconFlow/Volcengine），
# 则进一步调用出真实图片 URL；没配置时只返回提示词（半自动流程足够用，不阻塞）。
import httpx
import os


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


def generate_cover(keyword, platform, article_text="", api_base="", api_key="", model="",
                   size="1024x1024", note_cfg=None):
    """生成配图方案；有图 API 配置则顺便出图。
    note_cfg 来自写作配置里的「图片策略/配图密度」，只影响提示词描述，不影响接口调用。
    """
    import writing
    prompt = build_cover_prompt(keyword, platform, article_text)

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

    result = {"prompt": prompt, "size": size, "image_url": None,
              "note": "已生成配图提示词，可手动用任一 AI 绘图工具出图"}
    if img_note:
        result["image_plan"] = img_note   # 建议配几张、什么策略

    if not api_base or not api_key:
        result["note"] = "未配置图 API：已生成提示词，可复制到任意 AI 绘图工具出图（站点配置里填 IMAGE_API_BASE/KEY 可自动出图）"
        return result

    try:
        resp = httpx.post(
            api_base,
            headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
            json={"model": model or "default", "prompt": prompt, "size": size, "n": 1},
            timeout=60,
        )
        data = resp.json()
        # OpenAI 兼容返回：data[0].url 或 b64_json
        img = (data.get("data") or [{}])[0]
        result["image_url"] = img.get("url") or None
        result["note"] = "已调用图 API 出图" if result["image_url"] else "图 API 未返回图片，已保留提示词"
    except Exception as e:
        result["note"] = f"图 API 调用失败（{e}），已保留提示词"
    return result
