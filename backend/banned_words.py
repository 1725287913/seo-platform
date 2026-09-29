# banned_words.py
# 违禁词库加载 + 文本检测（支持「通用词库 + 平台专属词库」两层）
# - 通用词库：data/banned_words.txt（广告法极限词等，所有平台共用）
# - 平台专属：data/banned_platform.json（各平台规则不同，如小红书禁引流词）
import json, os

BASE = os.path.dirname(__file__)
WORDS_FILE = os.path.join(BASE, "data", "banned_words.txt")
PLATFORM_FILE = os.path.join(BASE, "data", "banned_platform.json")

# 预置的各平台专属词库（首次运行时写入 JSON，之后可在界面增删）
PLATFORM_DEFAULTS = {
    "xiaohongshu": ["微信", "加微", "加V", "私聊", "引流", "代购", "扫码"],
    "weibo": ["加微", "加V", "私信我", "引流", "扫码"],
    "douyin": ["微信", "加微", "私聊", "引流", "点主页", "扫码"],
    "weixin": ["转发抽奖", "关注领取", "诱导分享", "点击领取"],
    "toutiao": ["微信", "加微", "引流"],
    "zhihu": ["微信", "加微", "引流", "导流"],
}
# 各平台一句话说明（前端展示用）
PLATFORM_TIPS = {
    "xiaohongshu": "严打站外引流（微信/代购等），营销味重易限流",
    "weibo": "导流词汇易被降权",
    "douyin": "口播/字幕禁引流词，违者限流",
    "weixin": "公众号禁诱导分享/关注",
    "toutiao": "导流词易扣分",
    "zhihu": "导流易折叠回答",
}


def _ensure_platform_file():
    """首次运行：把预置平台词库写进 JSON（已存在则不动）。"""
    if not os.path.exists(PLATFORM_FILE):
        json.dump(PLATFORM_DEFAULTS, open(PLATFORM_FILE, "w", encoding="utf-8"),
                  ensure_ascii=False, indent=2)


def load_platform_words():
    """读平台专属词库，返回 {platform_key: [word, ...]}。"""
    _ensure_platform_file()
    return json.load(open(PLATFORM_FILE, encoding="utf-8"))


def _save_platform_words(data):
    json.dump(data, open(PLATFORM_FILE, "w", encoding="utf-8"),
              ensure_ascii=False, indent=2)


def load_words(platform: str = None):
    """读词库：通用词库 +（可选）指定平台的专属词库，去重保序。"""
    words = []
    if os.path.exists(WORDS_FILE):
        with open(WORDS_FILE, encoding="utf-8") as f:
            for line in f:
                w = line.strip()
                if not w or w.startswith("#"):   # 空行/注释行跳过
                    continue
                words.append(w)
    if platform:
        words += load_platform_words().get(platform, [])
    # 去重并保持顺序
    return list(dict.fromkeys(words))


def check_text(text: str, platform: str = None):
    """在 text 中逐个匹配违禁词（含平台专属），返回每次命中的位置。
    返回: [{"word": "最佳", "index": 12, "platform": ""}, ...]
    """
    if not text:
        return []
    lower = text.lower()
    matches = []
    # 通用词命中不带平台标记
    for w in load_words():
        wl = w.lower()
        idx = lower.find(wl)
        while idx != -1:
            matches.append({"word": w, "index": idx, "platform": ""})
            idx = lower.find(wl, idx + len(wl))
    # 平台专属词命中带平台标记（前端能显示来源）
    if platform:
        for w in load_platform_words().get(platform, []):
            wl = w.lower()
            idx = lower.find(wl)
            while idx != -1:
                matches.append({"word": w, "index": idx, "platform": platform})
                idx = lower.find(wl, idx + len(wl))
    return matches


def add_word(word: str, platform: str = ""):
    """加词：platform 为空 → 通用 txt；否则 → 该平台专属 JSON。"""
    word = word.strip()
    if not word:
        return {"ok": False, "message": "词不能为空"}
    if platform:
        data = load_platform_words()
        arr = data.setdefault(platform, [])
        if word not in arr:
            arr.append(word)
        _save_platform_words(data)
    else:
        with open(WORDS_FILE, "a", encoding="utf-8") as f:
            f.write(word + "\n")
    return {"ok": True}


def del_word(word: str, platform: str = ""):
    """删词：platform 为空 → 从通用 txt 删；否则从平台专属删。"""
    if platform:
        data = load_platform_words()
        data[platform] = [w for w in data.get(platform, []) if w != word]
        _save_platform_words(data)
    else:
        if not os.path.exists(WORDS_FILE):
            return {"ok": True}
        lines = [l.rstrip("\n") for l in open(WORDS_FILE, encoding="utf-8")]
        lines = [l for l in lines if l.strip() and l.strip() != word]
        open(WORDS_FILE, "w", encoding="utf-8").write("\n".join(lines) + "\n")
    return {"ok": True}


def platform_tips():
    """给前端：每个平台的专属词数量 + 一句话规则说明。"""
    data = load_platform_words()
    return {k: {"count": len(v), "tip": PLATFORM_TIPS.get(k, "")} for k, v in data.items()}


# 简单自测：python banned_words.py
if __name__ == "__main__":
    print("通用命中:", check_text("我们是最好的，销量第一！"))
    print("小红书命中:", check_text("加微信领优惠，最好的选择", "xiaohongshu"))
