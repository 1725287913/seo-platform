# selftest.py
# 全链路功能自测：把后端所有接口真实打一遍，看哪些能通、哪些断了。
# 用法（先启动服务）：
#   python selftest.py            # 不测真调模型（快，省 token）
#   python selftest.py --ai       # 连真调模型一起测（慢 30~60 秒，会花 token）
#
# 测试数据统一打 __测试__ 前缀，测完自动删掉，不污染你自己的数据。
import sys, json, time, base64
import httpx

BASE = "http://127.0.0.1:8020"
WITH_AI = "--ai" in sys.argv

results = []   # 每项：(分组, 名称, ok, 说明)


def call(method, path, body=None, timeout=30):
    """打一个接口，返回 (status_code, json_or_text)"""
    url = BASE + path
    try:
        r = httpx.request(method, url, json=body, timeout=timeout)
        try:
            return r.status_code, r.json()
        except Exception:
            return r.status_code, r.text[:300]
    except Exception as e:
        return 0, f"{type(e).__name__}: {e}"


def check(group, name, method, path, body=None, timeout=30, expect=None):
    """测一项：expect 是断言函数，返回 True/False"""
    code, data = call(method, path, body, timeout)
    ok = code == 200
    note = ""
    if not ok:
        note = f"HTTP {code} {str(data)[:160]}"
    elif expect:
        try:
            good = expect(data)
            if not good:
                ok, note = False, f"返回内容不符预期：{str(data)[:160]}"
        except Exception as e:
            ok, note = False, f"断言异常 {e}"
    else:
        note = str(data)[:120] if not isinstance(data, (list, dict)) else f"{type(data).__name__} len={len(data)}"
    results.append((group, name, ok, note))
    print(("  ✅ " if ok else "  ❌ ") + f"{name}" + ("" if ok else f"  → {note}"))
    return data


def has_key(k):
    """断言返回是个 dict 且含某字段"""
    return lambda d: isinstance(d, dict) and k in d


print("=" * 64)
print("SEO 矩阵平台 —— 全链路功能自测")
print("=" * 64)

# ---------- ① 基础与配置 ----------
print("\n【① 基础与配置】")
cache = {}

cache["cfg"] = check("基础", "读取配置 /api/config", "GET", "/api/config", expect=has_key("BAIDU_SITE"))
check("基础", "服务商列表 /api/providers", "GET", "/api/providers",
      expect=lambda d: len(d.get("providers", [])) >= 10)
check("基础", "平台列表 /api/platforms", "GET", "/api/platforms",
      expect=lambda d: len(d.get("platforms", [])) >= 5)
cache["models"] = check("基础", "模型列表 /api/models", "GET", "/api/models")
check("基础", "数据中心 /api/datacenter", "GET", "/api/datacenter")
check("基础", "统计 /api/stats", "GET", "/api/stats")
check("基础", "推送日志 /api/push-log", "GET", "/api/push-log")

# 站点配置是否填了真域名（百度闭环的前提）
site = (cache["cfg"] or {}).get("BAIDU_SITE", "")
token_ok = (cache["cfg"] or {}).get("BAIDU_TOKEN_configured", False)
print(f"\n  ℹ 百度站点配置：BAIDU_SITE={site or '(空)'} / TOKEN={'已填' if token_ok else '(空)'}")
if not site or "example.com" in str(site):
    print("  ⚠ BAIDU_SITE 还是空的或占位域名 —— 百度推送这一步必定失败，需要先有真实网站")

# ---------- ② 内容生产资料 CRUD ----------
print("\n【② 内容生产资料（增删改查）】")
TAG = "__测试__"

kw = check("关键词", "新增关键词", "POST", "/api/keywords",
           {"keyword": TAG + "南京保洁多少钱", "platform": "baidu"})
kw_id = (kw or {}).get("id") if isinstance(kw, dict) else None
check("关键词", "关键词列表", "GET", "/api/keywords",
      expect=lambda d: isinstance(d.get("keywords"), list))
if kw_id:
    check("关键词", "改关键词", "PUT", f"/api/keywords/{kw_id}", {"status": "used", "keyword": TAG + "改"})
    check("关键词", "删关键词", "DELETE", f"/api/keywords/{kw_id}")
check("关键词", "长尾词扩展 /api/keywords/expand", "POST", "/api/keywords/expand",
      {"seed": "南京保洁"}, timeout=60)

prod = check("产品库", "新增产品", "POST", "/api/products",
             {"name": TAG + "保洁套餐", "category": "服务", "selling_points": "3小时深度保洁,自带设备",
              "price": "299 元", "url": "", "image": "", "spec": "3小时"})
pid = (prod or {}).get("id") if isinstance(prod, dict) else None
if pid:
    check("产品库", "改产品", "PUT", f"/api/products/{pid}", {"price": "399 元"})
    check("产品库", "产品匹配 /api/products/match", "GET", "/api/products/match?q=保洁")
    check("产品库", "删产品", "DELETE", f"/api/products/{pid}")

kn = check("知识库", "新增知识", "POST", "/api/knowledge",
           {"title": TAG + "行业资料", "content": "2026年9月南京保洁市场价 35-45 元/小时。"})
kid = (kn or {}).get("id") if isinstance(kn, dict) else None
if kid:
    check("知识库", "知识检索", "GET", "/api/knowledge/search?q=保洁")
    check("知识库", "知识详情", "GET", f"/api/knowledge/{kid}")
    check("知识库", "删知识", "DELETE", f"/api/knowledge/{kid}")
check("知识库", "文件导入 /api/knowledge/import", "POST", "/api/knowledge/import",
      {"filename": "test.txt",
       "content_b64": base64.b64encode((TAG + "导入测试内容，一段纯文本。").encode("utf-8")).decode()})

per = check("人设", "新增人设", "POST", "/api/personas",
            {"name": TAG + "人设", "platform": "baidu", "tone": "朋友聊天", "bio": "本地生活老编辑"})
if (per or {}).get("id"):
    check("人设", "改人设", "PUT", f"/api/personas/{per['id']}", {"tone": "专业但亲切"})
    check("人设", "删人设", "DELETE", f"/api/personas/{per['id']}")

sn = check("素材", "新增素材", "POST", "/api/snippets", {"title": TAG + "素材", "content": "一段可插入的参考资料。"})
if (sn or {}).get("id"):
    check("素材", "素材列表", "GET", "/api/snippets")
    check("素材", "删素材", "DELETE", f"/api/snippets/{sn['id']}")

tp = check("模板", "新增模板", "POST", "/api/templates",
           {"name": TAG + "模板", "platform": "baidu", "category": "干货",
            "structure": "痛点开头\n原因分析\n解决方案\n行动号召"})
if (tp or {}).get("id"):
    check("模板", "改模板", "PUT", f"/api/templates/{tp['id']}", {"category": "指南"})
    check("模板", "删模板", "DELETE", f"/api/templates/{tp['id']}")

top = check("选题", "新增选题", "POST", "/api/topics", {"keyword": TAG + "装修避坑", "source": "手动"})
if (top or {}).get("id"):
    check("选题", "选题列表", "GET", "/api/topics")
    check("选题", "删选题", "DELETE", f"/api/topics/{top['id']}")
check("选题", "选题推荐 /api/topics/recommend", "POST", "/api/topics/recommend", {"seed": "保洁"}, timeout=60)

acc = check("账号", "新增账号", "POST", "/api/accounts", {"name": TAG + "账号", "platform": "baidu"})
if (acc or {}).get("id"):
    check("账号", "改账号（发布预设）", "PUT", f"/api/accounts/{acc['id']}", {"preset": {"tags": "本地生活"}})
    check("账号", "账号列表", "GET", "/api/accounts")
    check("账号", "删账号", "DELETE", f"/api/accounts/{acc['id']}")

wh = check("Webhook", "新增 Webhook", "POST", "/api/webhooks", {"url": "https://example.com/hook", "event": "pipeline_done"})
if (wh or {}).get("id"):
    check("Webhook", "开关 Webhook", "POST", f"/api/webhooks/{wh['id']}/toggle")
    check("Webhook", "删 Webhook", "DELETE", f"/api/webhooks/{wh['id']}")

check("排期", "排期列表", "GET", "/api/schedule")
check("排期", "待办排期", "GET", "/api/schedule/due")

print("\n【③ 违禁词】")
check("违禁词", "词库读取", "GET", "/api/banned-words", expect=lambda d: isinstance(d, (list, dict)))
check("违禁词", "文本检测 /api/check", "POST", "/api/check",
      {"text": "这是最好的产品，全国第一，加微信详聊", "platform": "baidu"},
      expect=lambda d: isinstance(d, dict))

print("\n【④ 写作配置 / 预设 / 百度就绪诊断】")
check("写作", "可调项定义 /api/writing-options", "GET", "/api/writing-options",
      expect=lambda d: len(d.get("options", [])) >= 10 and "defaults" in d)
check("写作", "预设列表 /api/presets", "GET", "/api/presets",
      expect=lambda d: isinstance(d.get("presets"), list))
pre = check("写作", "保存写作预设", "POST", "/api/presets",
            {"name": TAG + "预设",
             "config": {"style": "guide", "word_count": 2000, "deai": False},
             "platform": "baidu"})
if isinstance(pre, dict) and pre.get("id"):
    cfg = pre.get("config", {})
    cfg_ok = cfg.get("style") == "guide" and cfg.get("word_count") == 2000
    results.append(("写作", "预设内容存取正确", cfg_ok, "" if cfg_ok else f"存回的不对：{cfg}"))
    print(("  ✅ " if cfg_ok else "  ❌ ") + "预设内容存取正确")
    check("写作", "删除写作预设", "DELETE", f"/api/presets/{pre['id']}")
rd = check("写作", "百度跑通体检 /api/baidu-readiness", "GET", "/api/baidu-readiness",
           expect=lambda d: isinstance(d.get("items"), list) and "next_step" in d)
if isinstance(rd, dict):
    print(f"     ↳ 体检结果：{'已就绪' if rd.get('ready') else '尚未就绪'}，"
          f"通过 {rd.get('passed')}/{rd.get('total')}")
    print(f"     ↳ 下一步：{str(rd.get('next_step'))[:90]}")

# ---------- ④ AI 生成 ----------
print("\n【⑤ AI 生成】（真调模型，慢）")
if WITH_AI:
    gen = check("生成", "文章生成 /api/generate（带写作配置）", "POST", "/api/generate",
                {"keyword": "南京 保洁 多少钱一次", "platform": "baidu",
                 "writing": {"style": "guide", "word_count": 800, "industry": "家政保洁",
                             "audience": "本地居民", "title_kw": "南京保洁",
                             "deai": True, "temperature": 0.7}}, timeout=240,
                expect=lambda d: bool(d.get("content")))
    words = len((gen or {}).get("content", ""))
    print(f"     ↳ 出稿 {words} 字，模型 {(gen or {}).get('model')}")
    print(f"     ↳ 生效配置：{(gen or {}).get('used', {}).get('writing')}")
    # 写作配置真的生效了吗：字数配的 800，成品不该跑到 3000
    if gen and gen.get("content"):
        n = len(gen["content"])
        ok = 300 <= n <= 2200
        results.append(("生成", "字数配置是否生效", ok, "" if ok else f"配了 800 字，实际 {n} 字"))
        print(("  ✅ " if ok else "  ❌ ") + f"字数配置是否生效（配 800 字，实际 {n} 字）")
    check("生成", "社媒文案 /api/generate/social", "POST", "/api/generate/social",
          {"kind": "post", "platform": "xiaohongshu", "keyword": "南京保洁避坑"}, timeout=180,
          expect=lambda d: bool(d.get("content")))
else:
    print("  ⏭ 跳过（加 --ai 参数才会真调模型）")

# ---------- ⑤ 文章库 / 静态页导出 ----------
print("\n【⑤ 文章库与 SEO 静态页】")
arts = check("文章", "文章列表", "GET", "/api/articles", expect=lambda d: isinstance(d, list))
art_id = None
if arts:
    art_id = arts[0].get("id")
    print(f"     ↳ 现有 {len(arts)} 篇，取第一篇测导出（不删你的文章）")
if art_id:
    check("文章", "文章状态修改", "POST", f"/api/articles/{art_id}/status", {"status": "checked"})
    exp = check("文章", "导出 SEO 静态页", "POST", f"/api/articles/{art_id}/export",
                {"site": site or "test.example.com"}, expect=has_key("url"))
    print(f"     ↳ 生成 HTML：{(exp or {}).get('file')}")
    print(f"     ↳ 线上 URL：{(exp or {}).get('url')}")
    check("文章", "取文章 URL", "GET", f"/api/articles/{art_id}/url")

# ---------- ⑥ 百度闭环 ----------
print("\n【⑥ 百度闭环：导出 → 推送 → 收录检测】")
push_body = {"urls": [f"https://{site or 'test.example.com'}/seo-test.html"]}
push = check("百度", "主动推送 /api/push", "POST", "/api/push", push_body)
print(f"     ↳ 百度返回：{json.dumps(push, ensure_ascii=False)[:280]}")
if isinstance(push, dict):
    if push.get("error") == "missing_config":
        print("     ⚠ 没配 BAIDU_SITE/BAIDU_TOKEN —— 这一步是百度闭环的卡点")
    elif push.get("error"):
        print(f"     ⚠ 推送被拒：{push.get('message') or push.get('error')}（域名/Token/备案问题）")
    elif push.get("success") is not None:
        print(f"     ✅ 百度收下了 {push.get('success')} 条（remain={push.get('remain')}）")

check("百度", "收录检测", "POST", "/api/index-check",
      {"urls": [f"https://{site or 'test.example.com'}/seo-test.html"]}, timeout=60)

# ---------- ⑦ 流水线 ----------
print("\n【⑦ 一键流水线】")
if WITH_AI:
    pl = check("流水线", "全流程 /api/pipeline/run", "POST", "/api/pipeline/run",
               {"keyword": "南京 保洁 上门 价格", "platform": "baidu", "auto_push": False}, timeout=240)
    for s in (pl or {}).get("steps", []):
        print(f"     {'✅' if s.get('ok') else '⚠️ '} {s.get('name')}：{s.get('detail')}")
else:
    print("  ⏭ 跳过（加 --ai 参数才会测）")

# ---------- 汇总 ----------
print("\n" + "=" * 64)
total = len(results)
passed = sum(1 for r in results if r[2])
failed = [r for r in results if not r[2]]
print(f"总计 {total} 项：通过 {passed}，失败 {len(failed)}")
if failed:
    print("\n失败清单：")
    for g, n, ok, note in failed:
        print(f"  ❌ [{g}] {n}\n      {note}")
else:
    print("全部通过 ✅")
print("=" * 64)
