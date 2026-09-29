# products.py
# 产品库：产品名/卖点/规格/价格/图片，出稿时按主题匹配注入，让 AI 写出带真实卖点的内容。
import json, os, re, time, uuid

DATA = os.path.join(os.path.dirname(__file__), "data", "products.json")


def _read():
    if not os.path.exists(DATA):
        json.dump([], open(DATA, "w", encoding="utf-8"))
        return []
    return json.load(open(DATA, encoding="utf-8"))


def _write(arr):
    json.dump(arr, open(DATA, "w", encoding="utf-8"), ensure_ascii=False, indent=2)


def list_products(category="", q=""):
    arr = _read()
    if category:
        arr = [p for p in arr if p.get("category") == category]
    if q:
        q = q.lower()
        arr = [p for p in arr
               if q in (p.get("name", "") + p.get("selling", "") + p.get("tags", "")).lower()]
    return arr


def categories():
    """已有分类去重列表，供前端下拉。"""
    return sorted({p.get("category") for p in _read() if p.get("category")})


def get_product(pid):
    return next((p for p in _read() if p.get("id") == pid), None)


def add_product(d: dict):
    arr = _read()
    name = (d.get("name") or "").strip()
    if not name:
        return {"error": "empty", "message": "产品名称不能为空"}
    item = {
        "id": str(uuid.uuid4())[:8],
        "name": name,
        "category": d.get("category", "") or "未分类",
        "selling": (d.get("selling") or "").strip(),   # 卖点，一行一条
        "specs": (d.get("specs") or "").strip(),       # 规格参数
        "price": (d.get("price") or "").strip(),
        "url": (d.get("url") or "").strip(),
        "image": (d.get("image") or "").strip(),       # 主图地址（配图参考用）
        "tags": (d.get("tags") or "").strip(),
        "created_at": time.strftime("%Y-%m-%d %H:%M"),
    }
    arr.insert(0, item)
    _write(arr)
    return item


def update_product(pid, d: dict):
    arr = _read()
    for p in arr:
        if p.get("id") == pid:
            for k in ("name", "category", "selling", "specs", "price", "url", "image", "tags"):
                if k in d and d[k] is not None:
                    p[k] = d[k]
            _write(arr)
            return p
    return {"error": "not_found", "message": "产品不存在"}


def del_product(pid):
    _write([p for p in _read() if p.get("id") != pid])
    return {"ok": True}


# ---------- 出稿时注入用 ----------

def _tokens(q):
    """中文 2-gram + 英文数字词，与知识库保持同一套切词逻辑。"""
    q = (q or "").lower()
    grams = set()
    for block in re.findall(r"[\u4e00-\u9fa5]+", q):
        for i in range(len(block) - 1):
            grams.add(block[i:i + 2])
        if len(block) == 1:
            grams.add(block)
    for w in re.findall(r"[a-z0-9]{2,}", q):
        grams.add(w)
    return grams


def build_context(query, ids=""):
    """挑出与主题相关的产品，拼成 prompt 里的「产品资料」段。
    ids 非空时只取指定产品（前端手动勾选），否则按关键词自动匹配。
    """
    arr = _read()
    if ids:
        wanted = [i for i in ids.split(",") if i.strip()]
        picked = [p for p in arr if p.get("id") in wanted]
    else:
        grams = _tokens(query)
        if not grams:
            return "", []
        scored = []
        for p in arr:
            text = (p.get("name", "") + " " + p.get("selling", "") + " " + p.get("tags", "")
                    + " " + p.get("category", "")).lower()
            hit = sum(1 for g in grams if g in text)
            if hit:
                scored.append((hit, p))
        scored.sort(key=lambda x: -x[0])
        picked = [p for _, p in scored[:3]]

    if not picked:
        return "", []

    buf = ["【产品资料（真实信息，写到时必须依据它，不得编造参数与价格）】"]
    for p in picked:
        line = [f"· {p['name']}"]
        if p.get("category"):
            line.append(f"  分类：{p['category']}")
        if p.get("price"):
            line.append(f"  价格：{p['price']}")
        if p.get("selling"):
            line.append("  卖点：" + "；".join(x.strip() for x in p["selling"].split("\n") if x.strip()))
        if p.get("specs"):
            line.append(f"  规格：{p['specs'].replace(chr(10), '；')}")
        buf.append("\n".join(line))

    ctx = "\n".join(buf)
    meta = [{"id": p["id"], "name": p["name"]} for p in picked]
    return ctx, meta
