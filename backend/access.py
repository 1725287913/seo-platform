# access.py
# 访问门禁：给线上版加一道密码锁，避免链接被转发后陌生人进来乱用
# 开关规则：存在 backend/access.txt（或设了 ACCESS_PASSWORD 环境变量）才启用门禁；
#          本地没有这个文件 = 完全不拦截，开发时不用输密码。
import hmac
import hashlib
import os

from fastapi import Body, Request
from fastapi.responses import HTMLResponse, JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PASS_FILE = os.path.join(BASE_DIR, "access.txt")
COOKIE = "seo_gate"
LOGIN_API = "/api/gate/login"
STATUS_API = "/api/gate/status"
FREE_PATHS = {LOGIN_API, STATUS_API, "/robots.txt", "/favicon.ico"}
COOKIE_MAX_AGE = 30 * 24 * 3600  # 30 天免登录


def _password() -> str:
    """取访问密码：环境变量优先，其次读 access.txt。"""
    p = (os.environ.get("ACCESS_PASSWORD") or "").strip()
    if p:
        return p
    if os.path.exists(PASS_FILE):
        try:
            with open(PASS_FILE, encoding="utf-8") as f:
                return f.read().strip()
        except Exception:
            return ""
    return ""


def enabled() -> bool:
    """门禁开没开。"""
    return bool(_password())


def _token() -> str:
    """登录凭据由密码派生 —— 改密码后所有旧 cookie 立刻失效。"""
    return hashlib.sha256(("seo-gate::" + _password()).encode("utf-8")).hexdigest()


def _same(a: str, b: str) -> bool:
    """定时安全地比较两个字符串 —— 先转字节，否则中文密码会直接报错。"""
    return hmac.compare_digest(a.encode("utf-8"), b.encode("utf-8"))


def _passed(request: Request) -> bool:
    """这个请求有没有带有效的登录凭据。"""
    got = request.cookies.get(COOKIE, "")
    return bool(got) and _same(got, _token())


# 登录页：自带样式，不依赖前端资源，也不放进仓库
LOGIN_PAGE = """<!DOCTYPE html>
<html lang="zh-CN"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<meta name="robots" content="noindex,nofollow">
<title>需要访问密码</title>
<style>
  :root{--bg:#f5f6fa;--card:#fff;--line:#e6e8f0;--text:#20232b;--sub:#7b8296;
        --brand:#6366f1;--brand-soft:#eef0fe;--danger:#e5484d;}
  @media (prefers-color-scheme:dark){
    :root{--bg:#14161c;--card:#1c1f27;--line:#2c313d;--text:#e8eaf0;--sub:#8d94a8;
          --brand:#818cf8;--brand-soft:#262a3d;--danger:#ff6b6b;}
  }
  *{box-sizing:border-box;margin:0;padding:0}
  body{min-height:100vh;display:flex;align-items:center;justify-content:center;
       background:var(--bg);color:var(--text);padding:24px;
       font:14px/1.6 -apple-system,BlinkMacSystemFont,"Segoe UI","PingFang SC","Microsoft YaHei",sans-serif;}
  .box{width:100%;max-width:380px;background:var(--card);border:1px solid var(--line);
       border-radius:14px;padding:32px 28px;box-shadow:0 12px 32px rgba(20,22,28,.08);}
  .logo{width:44px;height:44px;border-radius:12px;background:var(--brand-soft);
        display:flex;align-items:center;justify-content:center;margin-bottom:18px;}
  h1{font-size:18px;font-weight:600;margin-bottom:6px;}
  p.sub{font-size:13px;color:var(--sub);margin-bottom:22px;}
  label{display:block;font-size:13px;color:var(--sub);margin-bottom:7px;}
  input{width:100%;height:42px;padding:0 13px;font-size:14px;color:var(--text);
        background:var(--bg);border:1px solid var(--line);border-radius:9px;outline:none;
        transition:border-color .15s,box-shadow .15s;}
  input:focus{border-color:var(--brand);box-shadow:0 0 0 3px var(--brand-soft);}
  button{width:100%;height:42px;margin-top:18px;font-size:14px;font-weight:500;color:#fff;
         background:var(--brand);border:none;border-radius:9px;cursor:pointer;
         box-shadow:0 4px 12px rgba(99,102,241,.28);transition:transform .12s,box-shadow .12s;}
  button:hover{transform:translateY(-1px);box-shadow:0 6px 16px rgba(99,102,241,.34);}
  button:disabled{opacity:.6;cursor:not-allowed;transform:none;}
  .err{display:none;margin-top:14px;font-size:13px;color:var(--danger);}
</style></head>
<body>
  <div class="box">
    <div class="logo">
      <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="#6366f1"
           stroke-width="2" stroke-linecap="round"><rect x="4" y="10.5" width="16" height="10" rx="2.5"/>
      <path d="M8 10.5V7a4 4 0 018 0v3.5"/></svg>
    </div>
    <h1>这是私有预览站点</h1>
    <p class="sub">输入访问密码才能进入。本页不会被搜索引擎收录。</p>
    <label for="pw">访问密码</label>
    <input id="pw" type="password" placeholder="请输入访问密码" autocomplete="current-password" autofocus>
    <button id="go">进入</button>
    <div class="err" id="err"></div>
  </div>
<script>
  var pw = document.getElementById('pw');
  var go = document.getElementById('go');
  var err = document.getElementById('err');
  function login(){
    var v = pw.value.trim();
    if(!v){ show('请先输入密码'); return; }
    go.disabled = true; go.textContent = '验证中…'; err.style.display = 'none';
    fetch('/api/gate/login', {
      method:'POST', headers:{'Content-Type':'application/json'},
      body: JSON.stringify({password: v})
    }).then(function(r){
      if(r.ok){ location.reload(); return; }
      return r.json().then(function(d){ throw new Error(d.message || '密码不正确'); });
    }).catch(function(e){
      show(e.message || '验证失败，请重试');
      go.disabled = false; go.textContent = '进入';
    });
  }
  function show(msg){ err.textContent = msg; err.style.display = 'block'; }
  go.addEventListener('click', login);
  pw.addEventListener('keydown', function(e){ if(e.key === 'Enter') login(); });
</script>
</body></html>"""


class GateMiddleware(BaseHTTPMiddleware):
    """没通过门禁的请求：页面返回登录页，接口返回 401。"""

    async def dispatch(self, request: Request, call_next):
        # 顺手给所有响应加两个头：
        #   X-Robots-Tag  —— 禁止搜索引擎收录
        #   Cache-Control —— 禁止 CDN/浏览器缓存，否则改版后会继续吐旧页面
        def stamp(resp):
            resp.headers["X-Robots-Tag"] = "noindex, nofollow"
            resp.headers["Cache-Control"] = "no-store, no-cache, must-revalidate"
            resp.headers["Pragma"] = "no-cache"
            return resp

        if not enabled() or request.url.path in FREE_PATHS or _passed(request):
            return stamp(await call_next(request))

        if request.url.path.startswith("/api/"):
            return stamp(JSONResponse(
                {"error": "unauthorized", "message": "需要访问密码，请刷新页面后重新登录"},
                status_code=401))
        return stamp(HTMLResponse(LOGIN_PAGE))


def setup(app):
    """把门禁挂到应用上，并注册登录/查询两个接口。"""

    @app.post(LOGIN_API)
    def gate_login(payload: dict = Body(...)):
        if not enabled():
            return {"ok": True, "gate": False}
        pw = str(payload.get("password", ""))
        if not _same(pw, _password()):
            return JSONResponse({"ok": False, "message": "密码不正确，请重新输入"},
                                status_code=401)
        resp = JSONResponse({"ok": True, "gate": True})
        resp.set_cookie(COOKIE, _token(), max_age=COOKIE_MAX_AGE,
                        httponly=True, samesite="lax", path="/")
        return resp

    @app.get(STATUS_API)
    def gate_status(request: Request):
        return {"gate": enabled(), "passed": (not enabled()) or _passed(request)}

    @app.get("/robots.txt")
    def robots():
        # 直接告诉爬虫：整站都别收录
        return HTMLResponse("User-agent: *\nDisallow: /\n", media_type="text/plain")
