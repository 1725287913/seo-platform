// app.js —— AI 内容中台前端逻辑（Vue 3 自托管，单文件应用）

// Vue 没加载成功时给一句人话提示，否则整页只会露出一堆 {{ }} 让人摸不着头脑
if (!window.Vue) {
  document.documentElement.innerHTML =
    '<body style="margin:0;display:flex;align-items:center;justify-content:center;height:100vh;'
    + 'font:15px/1.9 system-ui,-apple-system,\'Microsoft YaHei\',sans-serif;background:#f5f6fa;color:#1f2333">'
    + '<div style="max-width:460px;padding:28px 30px;background:#fff;border:1px solid #e6e8f0;border-radius:14px">'
    + '<div style="font-size:17px;font-weight:600;margin-bottom:10px">页面框架没加载成功</div>'
    + '<div style="color:#5c6178">Vue 运行库没取到，请确认 <code style="background:#f0f1f6;padding:1px 6px;border-radius:4px">'
    + 'frontend/vendor/vue.global.prod.js</code> 这个文件存在（它在项目里，不用联网）。'
    + '刷新一次通常就能恢复。</div></div></body>';
  throw new Error('Vue 未加载：请确认 frontend/vendor/vue.global.prod.js 存在');
}

const { createApp, ref, reactive, computed, onMounted, watch, nextTick } = Vue;

/* ============ 通用工具 ============ */
function escapeHtml(s){
  return String(s||'').replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;');
}

// Markdown → 富文本 HTML（用于复制富文本、粘贴到公众号保留结构）
function mdToHtml(md){
  if(!md) return '';
  const lines = md.split('\n');
  let html=''; let inList=null; let inCode=false, codeBuf=[];
  const closeList=()=>{ if(inList){ html+=`</${inList}>`; inList=null; } };
  const inline=(s)=>{
    s = escapeHtml(s);
    s = s.replace(/\*\*(.+?)\*\*/g,'<strong>$1</strong>');
    s = s.replace(/\*(.+?)\*/g,'<em>$1</em>');
    s = s.replace(/\[(.+?)\]\((.+?)\)/g,'<a href="$2">$1</a>');
    return s;
  };
  for(const raw of lines){
    const line = raw.replace(/\s+$/,'');
    if(/^```/.test(line.trim())){
      if(inCode){ html+=`<pre><code>${escapeHtml(codeBuf.join('\n'))}</code></pre>`; codeBuf=[]; inCode=false; }
      else { closeList(); inCode=true; }
      continue;
    }
    if(inCode){ codeBuf.push(line); continue; }
    const t = line.trim();
    if(t===''){ closeList(); continue; }
    let m;
    if(m = t.match(/^(#{1,6})\s+(.*)$/)){ closeList(); const lv=m[1].length; html+=`<h${lv}>${inline(m[2])}</h${lv}>`; continue; }
    if(m = t.match(/^>\s?(.*)$/)){ closeList(); html+=`<blockquote>${inline(m[1])}</blockquote>`; continue; }
    if(m = t.match(/^\s*[-*]\s+(.*)$/)){ if(inList!=='ul'){ closeList(); html+='<ul>'; inList='ul'; } html+=`<li>${inline(m[1])}</li>`; continue; }
    if(m = t.match(/^\s*\d+\.\s+(.*)$/)){ if(inList!=='ol'){ closeList(); html+='<ol>'; inList='ol'; } html+=`<li>${inline(m[1])}</li>`; continue; }
    closeList(); html+=`<p>${inline(t)}</p>`;
  }
  closeList();
  if(inCode){ html+=`<pre><code>${escapeHtml(codeBuf.join('\n'))}</code></pre>`; }
  return html;
}

// 用于界面展示（带违禁词高亮）
function renderContent(md, matches){
  if(!md) return '';
  let html = escapeHtml(md);
  if(matches && matches.length){
    const words = [...new Set(matches.map(m=>m.word))].sort((a,b)=>b.length-a.length);
    words.forEach(w=>{ const esc = escapeHtml(w); html = html.split(esc).join('<mark>'+esc+'</mark>'); });
  }
  // 行内格式：在「已转义」的文本上做，所以不会出现注入
  const inline = (s)=> s
    .replace(/!\[([^\]]*)\]\(([^)\s]+)\)/g, '<img src="$2" alt="$1" loading="lazy">')
    .replace(/\[([^\]]+)\]\(([^)\s]+)\)/g, '<a href="$2" target="_blank" rel="noopener">$1</a>')
    .replace(/\*\*([^*]+)\*\*/g, '<b>$1</b>')
    .replace(/`([^`]+)`/g, '<code>$1</code>');

  let out = '', inList = false, inCode = false;
  for(const raw of html.split('\n')){
    const t = raw.trim();
    if(t.startsWith('```')){ inCode = !inCode; out += inCode ? '<pre><code>' : '</code></pre>'; continue; }
    if(inCode){ out += raw + '\n'; continue; }
    if(t === ''){ if(inList){ out += '</ul>'; inList = false; } continue; }
    if(t.startsWith('### ')) out += '<h3>'+inline(t.slice(4))+'</h3>';
    else if(t.startsWith('## ')) out += '<h2>'+inline(t.slice(3))+'</h2>';
    else if(t.startsWith('# ')) out += '<h1>'+inline(t.slice(2))+'</h1>';
    else if(/^[-*] /.test(t)){
      if(!inList){ out += '<ul>'; inList = true; }
      out += '<li>'+inline(t.slice(2))+'</li>';
    }
    else if(t.startsWith('> ')) out += '<blockquote>'+inline(t.slice(2))+'</blockquote>';
    else if(/^(-{3,}|\*{3,})$/.test(t)) out += '<hr>';
    else out += '<p>'+inline(t)+'</p>';
  }
  if(inList) out += '</ul>';
  return out;
}

// 英文报错 → 中文提示（双语展示）
function translateBaiduMsg(msg){
  const map = {
    "site init fail": "站点未初始化：百度搜索资源平台还没添加或验证该域名（先去添加站点并完成验证）",
    "token is not valid": "token 无效：请检查「站点配置」里的 BAIDU_TOKEN 是否与站点匹配",
    "over quota": "今日推送额度已用完，明天再试",
  };
  return map[(msg||"").trim()] || null;
}
function translateDeepSeek(msg){
  const m = (msg||"").toLowerCase();
  if(m.includes("invalid api key") || m.includes("authentication")) return "API Key 无效，请检查「API 密钥」里的对应 Key";
  if(m.includes("insufficient") || m.includes("quota") || m.includes("balance")) return "账户余额不足或额度受限，请检查账户";
  if(m.includes("rate") || m.includes("limit")) return "请求过于频繁被限流，稍等几秒再试";
  return null;
}

createApp({
  setup(){
    /* ---------- 基础 ---------- */
    const view = ref('dashboard');
    const navOpen = reactive({ create:true, smart:false, auto:false, publish:true, system:false });
    const toggleGroup = (k)=>{ navOpen[k] = !navOpen[k]; };
    const toasts = ref([]);
    function toast(msg, kind='ok'){
      const id = Date.now()+Math.random();
      toasts.value.push({ id, msg, kind });
      setTimeout(()=>{ toasts.value = toasts.value.filter(t=>t.id!==id); }, 3200);
    }

    /* ---------- 主题：跟随系统 / 浅色 / 深色 ----------
       之前是「点一下循环三个模式」，有个坑：系统本来就是浅色时，
       第一次点 auto→light 界面颜色完全没变，看起来像没反应；
       而且每次切换还弹 toast，提示正好压在右上角按钮上，再点就点不到了。
       现在改成：点图标弹出菜单，三个模式直接选，点一次就生效，也不弹提示。 */
    const themeMode = ref(localStorage.getItem('seo-theme') || 'auto');
    const themeOpen = ref(false);   // 主题菜单是否展开
    const themeLabel = computed(()=> ({ auto:'跟随系统', light:'浅色', dark:'深色' }[themeMode.value] || '跟随系统'));
    // 菜单里能选的三种模式
    const themeOptions = [
      { key:'auto',  name:'跟随系统', icon:'🌗' },
      { key:'light', name:'浅色',     icon:'☀️' },
      { key:'dark',  name:'深色',     icon:'🌙' },
    ];
    // 老浏览器/jsdom 没有 matchMedia，降级成"永远浅色"，不能让整页挂掉
    const sysDark = window.matchMedia
      ? window.matchMedia('(prefers-color-scheme: dark)')
      : { matches:false, addEventListener(){}, addListener(){} };
    // 把最终结果写到 html[data-theme]，CSS 里两套变量靠它切换
    function applyTheme(){
      const dark = themeMode.value === 'dark' || (themeMode.value === 'auto' && sysDark.matches);
      document.documentElement.setAttribute('data-theme', dark ? 'dark' : 'light');
    }
    function setTheme(mode){
      themeMode.value = mode;
      try { localStorage.setItem('seo-theme', mode); } catch(e){}
      applyTheme();
      themeOpen.value = false;      // 选完立刻收起，不留遮挡
    }
    function toggleThemeMenu(){ themeOpen.value = !themeOpen.value; }
    // 点页面别处收起菜单（按钮上加了 .stop，所以点按钮不会立刻被这里关掉）
    document.addEventListener('click', ()=>{ themeOpen.value = false; });
    // 系统主题变了 —— 只有「跟随系统」模式才跟着变，手动选过的不动
    sysDark.addEventListener('change', ()=>{ if(themeMode.value === 'auto') applyTheme(); });
    applyTheme();

    const platforms = ref([]);
    const platform = ref('baidu');
    const currentPlatform = computed(()=> platforms.value.find(p=>p.key===platform.value) || platforms.value[0] || {});
    const platformName = (k)=> (platforms.value.find(p=>p.key===k)||{}).name || k;

    const stats = ref({ articles_total:0, articles_today:0, schedule_pending:0, schedule_total:0, accounts_total:0,
      push_ok:0, push_fail:0, active_model:'—', keywords_total:0, knowledge_total:0, banned_words_total:0,
      key_status:{}, accounts_by_platform:{} });
    const pushLog = ref([]);
    async function loadStats(){
      try{
        const r = await fetch('/api/stats'); stats.value = await r.json();
        const l = await fetch('/api/push-log'); pushLog.value = (await l.json()).log || [];
      }catch(e){ /* 静默 */ }
    }
    function go(v){
      view.value = v;
      if(v==='dashboard') loadStats();
      if(v==='datacenter') loadDatacenter();
      if(v==='write'||v==='batch') loadGenOptions();
      if(v==='products') loadProducts();
      if(v==='keys') loadProviders();
      if(v==='distribute'){ loadDistTargets(); loadDistTasks(); loadArticles(); }
      if(v==='create'){ loadArticles(); }
    }

    /* ---------- 数据中心 ---------- */
    const dcFilter = reactive({ days:30, platform:'', status:'', q:'' });
    const dc = ref({ metrics:{}, overview:[], trend:[] });
    async function loadDatacenter(){
      const qs = new URLSearchParams({ days:dcFilter.days, platform:dcFilter.platform,
        status:dcFilter.status, q:dcFilter.q }).toString();
      try{
        const r = await fetch('/api/datacenter?'+qs);
        const d = await r.json();
        dc.value = { metrics:d.metrics||{}, overview:d.overview||[], trend:d.trend||[] };
      }catch(e){ toast('数据加载失败：'+e, 'err'); }
    }
    function resetDc(){ dcFilter.days=30; dcFilter.platform=''; dcFilter.status=''; dcFilter.q=''; loadDatacenter(); }
    const dcMaxY = computed(()=>{
      const vals = dc.value.trend.flatMap(t=>[t.articles, t.push]);
      return Math.max(1, ...vals);
    });
    const _pts = (key)=>{
      const n = dc.value.trend.length;
      if(!n) return '';
      const max = dcMaxY.value;
      return dc.value.trend.map((t,i)=>{
        const x = n===1 ? 300 : i*(600/(n-1));
        const y = 140 - (t[key]/max)*120;
        return `${x.toFixed(1)},${y.toFixed(1)}`;
      }).join(' ');
    };
    const dcArtPoints = computed(()=> _pts('articles'));
    const dcPushPoints = computed(()=> _pts('push'));

    /* ---------- AI 服务商（选一家就自动配好地址与模型）---------- */
    const providers = ref([]);
    const providerGroups = ref([]);
    const activeModel = ref(null);
    const expandedProvider = ref('');     // 当前展开配置面板的服务商
    const pvModel = ref(''), pvBase = ref(''), pvKey = ref(''), pvMsg = ref(''), pvOk = ref(true);

    async function loadProviders(){
      const r = await fetch('/api/providers');
      const d = await r.json();
      providers.value = d.providers || [];
      providerGroups.value = d.groups || [];
      activeModel.value = d.active || null;
    }
    const providersByGroup = (g)=> providers.value.filter(p=>p.group === g);
    const curProvider = computed(()=> providers.value.find(p=>p.key === expandedProvider.value) || null);
    const activeProviderShort = computed(()=>{
      const p = providers.value.find(x=>x.key === (activeModel.value||{}).provider);
      return p ? p.short : 'AI';
    });

    // 点卡片展开配置；再点一次收起
    function pickProvider(p){
      if(expandedProvider.value === p.key){ expandedProvider.value = ''; return; }
      expandedProvider.value = p.key;
      pvModel.value = (p.models && p.models[0]) || '';
      pvBase.value = p.api_base || '';
      pvKey.value = '';
      pvMsg.value = '';
    }
    async function saveProvider(){
      const p = curProvider.value; if(!p) return;
      pvMsg.value = '';
      const r = await fetch('/api/providers/activate',{method:'POST',headers:{'Content-Type':'application/json'},
        body: JSON.stringify({ provider:p.key, model_name:pvModel.value, api_base:pvBase.value, key:pvKey.value })});
      const d = await r.json();
      if(d.error){ pvOk.value = false; pvMsg.value = d.message || d.error; return; }
      pvOk.value = true;
      pvMsg.value = '已启用：' + d.model.label + (d.key_configured ? '' : '（还没填 Key，填上才能出稿）');
      pvKey.value = '';
      await Promise.all([loadProviders(), loadModels(), loadStats(), loadKeys()]);
      toast('当前模型已切换');
    }
    async function testProvider(){
      const p = curProvider.value; if(!p) return;
      pvOk.value = true; pvMsg.value = '正在测试，请稍候…';
      const r = await fetch('/api/config/test',{method:'POST',headers:{'Content-Type':'application/json'},
        body: JSON.stringify({ kind:p.key, model:pvModel.value, api_base:pvBase.value, key:pvKey.value })});
      const d = await r.json();
      pvOk.value = !!d.ok; pvMsg.value = d.message;
    }
    async function testActiveModel(){
      keyMsg.value = '正在测试，请稍候…'; keyMsgOk.value = true;
      const r = await fetch('/api/models/test',{method:'POST',headers:{'Content-Type':'application/json'},body: JSON.stringify({})});
      const d = await r.json();
      keyMsgOk.value = !!d.ok; keyMsg.value = d.message;
    }

    /* ---------- 模型 / 模板 / 人设（写作台共用） ---------- */
    const modelList = ref([]);
    const selModel = ref('');
    const tplListAll = ref([]);
    const tplSel = ref('');
    const personaList = ref([]);
    const accSel = ref('');
    const topics = ref([]);
    const snippets = ref([]);
    const snipSel = ref('');

    async function loadModels(){
      const r = await fetch('/api/models'); const d = await r.json();
      modelList.value = d.models || [];
      const act = modelList.value.find(m=>m.active);
      selModel.value = act ? act.id : (modelList.value[0]||{}).id || '';
    }
    async function loadTemplates(){ const r = await fetch('/api/templates'); tplListAll.value = (await r.json()).templates || []; }
    async function loadPersonas(){ const r = await fetch('/api/personas'); personaList.value = (await r.json()).personas || []; }
    async function loadTopics(){ const r = await fetch('/api/topics'); topics.value = (await r.json()).topics || []; }
    async function loadSnippets(){ const r = await fetch('/api/snippets'); snippets.value = (await r.json()).snippets || []; }
    const loadGenOptions = ()=> Promise.all([loadModels(), loadTemplates(), loadPersonas(), loadTopics(), loadSnippets(), loadProducts()]);

    /* ---------- 产品库 ---------- */
    const productList = ref([]);
    const prodCats = ref([]);
    const prodPicked = ref([]);              // 写作台手动勾选的产品 id
    const prodFilterCat = ref('');
    const prodFilterQ = ref('');
    const prodQuery = ref('');               // 注入预览用的主题
    const prodCtx = ref('');
    const prodTested = ref(false);
    const prodTesting = ref(false);
    const prodMsg = ref('');
    const prodMsgType = ref('ok');
    const blankProd = ()=>({ id:'', name:'', category:'', selling:'', specs:'', price:'', url:'', image:'', tags:'' });
    const prodForm = reactive(blankProd());
    const resetProdForm = ()=> Object.assign(prodForm, blankProd());
    function prodTip(msg, type='ok'){ prodMsg.value = msg; prodMsgType.value = type; }

    async function loadProducts(){
      const qs = new URLSearchParams({ category: prodFilterCat.value, q: prodFilterQ.value }).toString();
      try{
        const r = await fetch('/api/products?'+qs);
        const d = await r.json();
        productList.value = d.products || [];
        prodCats.value = d.categories || [];
      }catch(e){ /* 静默 */ }
    }

    function toggleProd(id){
      const i = prodPicked.value.indexOf(id);
      if(i >= 0) prodPicked.value.splice(i, 1); else prodPicked.value.push(id);
    }

    async function saveProduct(){
      prodMsg.value = '';
      if(!prodForm.name.trim()){ prodTip('产品名称不能为空', 'err'); return; }
      const editing = !!prodForm.id;
      const r = await fetch(editing ? '/api/products/'+prodForm.id : '/api/products', {
        method: editing ? 'PUT' : 'POST',
        headers: {'Content-Type':'application/json'},
        body: JSON.stringify({ ...prodForm }),
      });
      const d = await r.json();
      if(d.error){ prodTip(d.message || '保存失败', 'err'); return; }
      prodTip(editing ? '修改已保存 ✅' : '产品已添加 ✅');
      resetProdForm(); await loadProducts(); loadStats();
    }

    function editProduct(p){ Object.assign(prodForm, p); prodMsg.value=''; }

    async function delProduct(id){
      await fetch('/api/products/'+id,{ method:'DELETE' });
      prodPicked.value = prodPicked.value.filter(x=>x !== id);
      await loadProducts(); loadStats(); toast('已删除');
    }

    async function testProdMatch(){
      prodTesting.value = true; prodCtx.value=''; prodTested.value=false;
      try{
        const r = await fetch('/api/products/match?q='+encodeURIComponent(prodQuery.value));
        const d = await r.json();
        prodCtx.value = d.context || '';
        prodTested.value = true;
      }catch(e){ toast('预览失败：'+e, 'err'); }
      finally{ prodTesting.value = false; }
    }

    // 只显示「通用模板 + 当前平台模板」
    const tplListForPlatform = computed(()=> tplListAll.value.filter(t=> !t.platform || t.platform===platform.value));
    const personaListForPlatform = computed(()=> personaList.value.filter(p=> p.platform===platform.value));

    /* ---------- AI 创作（三步向导）---------- */
    const writeStep = ref(1);          // 1 选素材 → 2 写作配置 → 3 生成文章
    // 只要配过任意一家 AI 服务商的 Key，就算「可以创作」
    const aiReady = computed(()=> Object.entries(stats.value.key_status || {})
      .some(([k, v]) => k.endsWith('_API_KEY') && v));
    const keyword = ref('');
    const topicSel = ref('');
    const realData = ref('');
    const genResult = ref('');
    const genError = ref('');
    const genLoading = ref(false);
    const genModel = ref('');
    const matches = ref([]);
    const coverResult = ref(null);
    const coverLoading = ref(false);   // 出图要十几秒，按钮得能显示进度
    const rendered = computed(()=> renderContent(genResult.value, matches.value));
    let lastSavedId = '';

    /* ---------- 写作配置：所有可调项 ----------
       选项定义由后端 writing.py 的 OPTIONS 提供（/api/writing-options），
       后端加一项，前端面板自动多一项，不用改前端代码。
       配置本身存 localStorage，实现「用一次记一次」。 */
    const wOpts = ref([]);
    const W_KEY = 'seo-writing';
    let savedWriting = {};
    try { savedWriting = JSON.parse(localStorage.getItem(W_KEY) || '{}') || {}; } catch(e){ savedWriting = {}; }
    const wcfg = reactive({
      style:'soft', audience:'', industry:'', word_count:1200, language:'zh-Hans',
      title_kw:'', structure:'', custom:'', temperature:0.8,
      deai:true, use_knowledge:true, generic:false,
      image_strategy:'mix', image_density:'standard', image_watermark:false,
      ...savedWriting,
    });
    // 改哪一项都自动记下来，下次打开还是这套
    watch(wcfg, ()=>{ try{ localStorage.setItem(W_KEY, JSON.stringify(wcfg)); }catch(e){} }, {deep:true});
    // 写作配置默认收起：一屏 15 个控件太劝退，改成「需要调才展开」
    const wcfgOpen = ref(false);

    // 取某一组配置的候选项 / 取当前值的人话说明
    const optItems = (key)=> ((wOpts.value.find(x=>x.key===key) || {}).items) || [];
    const optNote = (key, val)=> { const it = optItems(key).find(x=>x.key===val); return it ? (it.note||'') : ''; };
    // 卡片右上角一句概括：这次按什么配置写
    const writingSummary = computed(()=>{
      const p = [];
      const st = optItems('style').find(x=>x.key===wcfg.style);
      if(st) p.push(st.name);
      if(wcfg.audience) p.push(wcfg.audience);
      if(wcfg.industry) p.push(wcfg.industry);
      p.push(wcfg.word_count ? wcfg.word_count + ' 字' : '不限字数');
      const lg = optItems('language').find(x=>x.key===wcfg.language);
      if(lg && wcfg.language !== 'zh-Hans') p.push(lg.name);
      if(wcfg.deai) p.push('去 AI 味');
      if(wcfg.generic) p.push('通用写法');
      return p.filter(Boolean).join(' · ');
    });
    async function loadWritingOptions(){
      try{
        const r = await fetch('/api/writing-options'); const d = await r.json();
        wOpts.value = [...(d.options||[]), ...(d.image_options||[])];
      }catch(e){ /* 拿不到就沿用内置默认值，不让整页挂掉 */ }
    }

    /* ---------- 配置预设：整套配置存下来，一键切换 ---------- */
    const presetList = ref([]);
    const presetSel = ref('');
    async function loadPresets(){
      try{ const r = await fetch('/api/presets'); presetList.value = (await r.json()).presets || []; }
      catch(e){ /* 静默 */ }
    }
    function applyPreset(){
      const p = presetList.value.find(x=>x.id===presetSel.value);
      if(!p) return;
      Object.assign(wcfg, p.config || {});
      toast('已载入预设：' + p.name);
    }
    async function promptSavePreset(){
      const cur = presetList.value.find(x=>x.id===presetSel.value);
      const name = window.prompt('给这套写作配置起个名字（同名会覆盖）：', cur ? cur.name : '我的配置');
      if(!name || !name.trim()) return;
      await fetch('/api/presets',{ method:'POST', headers:{'Content-Type':'application/json'},
        body: JSON.stringify({ name:name.trim(), config:{...wcfg}, platform: platform.value }) });
      await loadPresets();
      toast('预设已保存 ✅');
    }
    async function delPreset(){
      if(!presetSel.value) return;
      await fetch('/api/presets/'+presetSel.value,{ method:'DELETE' });
      presetSel.value = '';
      await loadPresets();
      toast('预设已删除');
    }

    /* ---------- 百度闭环「准备就绪」诊断 ---------- */
    const readiness = ref(null);
    const rdLoading = ref(false);
    async function loadReadiness(){
      rdLoading.value = true;
      try{ const r = await fetch('/api/baidu-readiness'); readiness.value = await r.json(); }
      catch(e){ toast('诊断失败：'+e, 'err'); }
      finally{ rdLoading.value = false; }
    }
    const rdMark = (s)=> ({ ok:'✅', warn:'⚠️', fail:'❌', manual:'📌' }[s] || '•');

    function insertSnip(){
      const s = snippets.value.find(x=>x.id===snipSel.value);
      if(!s){ toast('请先选择一个素材', 'err'); return; }
      realData.value = (realData.value ? realData.value + '\n\n' : '') + s.content;
      toast('已插入素材：'+s.title);
    }

    async function generate(){
      if(!keyword.value.trim()){ toast('请先填写写作主题', 'err'); return; }
      genError.value=''; genLoading.value=true; genResult.value=''; matches.value=[]; coverResult.value=null; genModel.value='';
      try{
        const r = await fetch('/api/generate',{method:'POST',headers:{'Content-Type':'application/json'},
          body: JSON.stringify({ keyword:keyword.value, platform:platform.value, model_id:selModel.value,
            real_data:realData.value, topic:topicSel.value, template_id:tplSel.value, account:accSel.value,
            product_ids: prodPicked.value.join(','), writing: {...wcfg} })});
        const data = await r.json();
        if(data.error){
          let tip = data.message;
          if(data.error==='api_error' || data.error==='request_failed'){
            const t = translateDeepSeek(data.message);
            tip = t ? `${t}（原文：${data.message}）` : data.message;
          }
          genError.value = '❌ ' + tip;
        } else {
          genResult.value = data.content;
          genModel.value = data.model || '';
          const u = data.used || {};
          const parts = [];
          if(u.writing) parts.push(u.writing);
          if(u.persona) parts.push('套用人设');
          if(u.template) parts.push('套用模板');
          if(u.knowledge) parts.push('注入知识库');
          if(u.products && u.products.length) parts.push('注入产品 ' + u.products.join('、'));
          toast('生成完成' + (parts.length ? '（'+parts.join('、')+'）' : ''));
          writeStep.value = 3;   // 出稿后自动进第三步，不用手点
        }
      }catch(e){ genError.value = '❌ 请求失败：'+e; }
      finally{ genLoading.value=false; }
    }

    async function detect(){
      const r = await fetch('/api/check',{method:'POST',headers:{'Content-Type':'application/json'},
        body: JSON.stringify({ text: genResult.value, platform: platform.value })});
      matches.value = (await r.json()).matches || [];
      toast(matches.value.length ? `检出 ${matches.value.length} 处违禁词` : '未检出违禁词 ✅', matches.value.length?'err':'ok');
    }
    // 出图十几秒，期间按钮显示「出图中…」，也让用户知道没卡死
    async function makeCover(){
      if(coverLoading.value) return;
      coverLoading.value = true;
      try{
        const r = await fetch('/api/images',{method:'POST',headers:{'Content-Type':'application/json'},
          body: JSON.stringify({ keyword:keyword.value, platform:platform.value, article_text:genResult.value,
            writing: {...wcfg} })});
        coverResult.value = await r.json();
        if(coverResult.value.image_url) toast('配图生成好了 ✅');
        else toast(coverResult.value.note || '没出图，看提示词说明', 'err');
      }catch(e){ toast('出图失败：'+e, 'err'); }
      finally{ coverLoading.value = false; }
    }
    // 相对地址补成完整地址：复制给别人/粘到别的平台时必须是绝对 URL
    const absUrl = (u)=> !u ? '' : (/^https?:/i.test(u) ? u : location.origin + u);
    function downloadImage(u){
      const a = document.createElement('a');
      a.href = u;
      a.download = (u.split('/').pop() || 'cover.png').split('?')[0];
      document.body.appendChild(a); a.click(); document.body.removeChild(a);
      toast('已开始下载');
    }
    // 把配图插到正文末尾（Markdown 图片语法），导出 SEO 页时也会带上
    function coverToBody(){
      if(!genResult.value || !coverResult.value || !coverResult.value.image_url) return;
      genResult.value = genResult.value.replace(/\s+$/, '')
        + `\n\n![封面图](${absUrl(coverResult.value.image_url)})\n`;
      toast('已插入正文末尾');
    }
    // 复制到剪贴板：优先 Clipboard API，不可用时退回 textarea + execCommand。
    // 注意 navigator.clipboard 只在 https 或 localhost 下存在，局域网 IP 访问时是没有的，
    // 直接调用会抛 TypeError（而且 .catch 抓不到同步异常）。
    const copyText = (t)=>{
      if(!t) return;
      const fallback = ()=>{
        try{
          const ta = document.createElement('textarea');
          ta.value = t;
          ta.style.position = 'fixed';
          ta.style.opacity = '0';
          document.body.appendChild(ta);
          ta.select();
          const ok = document.execCommand && document.execCommand('copy');
          document.body.removeChild(ta);
          toast(ok ? '已复制 ✅' : '复制失败，请手动选中文字复制', ok ? 'ok' : 'err');
        }catch(e){ toast('复制失败，请手动选中文字复制', 'err'); }
      };
      if(!navigator.clipboard || !navigator.clipboard.writeText){ fallback(); return; }
      navigator.clipboard.writeText(t).then(()=> toast('已复制 ✅')).catch(fallback);
    };
    function copyMarkdown(t){ copyText(t); }
    async function copyRich(t){
      if(!t) return;
      try{
        const item = new ClipboardItem({
          'text/html': new Blob([`<div>${mdToHtml(t)}</div>`], {type:'text/html'}),
          'text/plain': new Blob([t], {type:'text/plain'})
        });
        await navigator.clipboard.write([item]);
        toast('已复制富文本（保留标题/列表结构），可直接粘到公众号 ✅');
      }catch(e){
        navigator.clipboard.writeText(t);
        toast('浏览器不支持富文本复制，已退回纯文本', 'info');
      }
    }
    // 把当前生成结果存进文章库（保存草稿 与 一键分发 共用这一段）
    async function _saveGenArticle(){
      const title = (genResult.value.match(/^#\s+(.+)$/m)||[])[1] || keyword.value;
      const r = await fetch('/api/articles',{method:'POST',headers:{'Content-Type':'application/json'},
        body: JSON.stringify({ title, content:genResult.value, keyword:keyword.value, platform:platform.value,
          topic:topicSel.value, account:accSel.value, model:genModel.value, status:'generated',
          cover:(coverResult.value && coverResult.value.image_url) || '',
          cover_prompt:(coverResult.value && coverResult.value.prompt) || '' })});
      const a = await r.json(); lastSavedId = a.id;
      return a;
    }
    async function saveArticle(){
      await _saveGenArticle();
      toast('已保存到文章库 ✅');
      loadArticles(); loadStats();
    }
    // 出稿后直接分发：先自动存一次（不用你手动点保存草稿），再带着这篇跳分发页
    async function distFromDraft(){
      if(!genResult.value){ toast('还没有内容', 'err'); return; }
      const a = await _saveGenArticle();
      toast('已存进文章库，正在带到分发页…');
      await loadArticles(); loadStats();
      await distFromArticle(a);
    }
    // 把生成结果端到「文章创作」页自己改（改完还能分发）
    function genToCreate(){
      if(!genResult.value){ toast('还没有内容', 'err'); return; }
      cf.title = (genResult.value.match(/^#\s+(.+)$/m)||[])[1] || keyword.value;
      cf.body = genResult.value;
      cf.platform = platform.value;
      cf.keyword = keyword.value;
      cfTab.value = 'edit';
      view.value = 'create';
      toast('已带到「文章创作」，改完可直接分发');
    }

    /* ---------- 批量创作 ---------- */
    const batchText = ref('');
    const batchList = ref([]);
    const batchRunning = ref(false);
    const batchStop = ref(false);
    const batchDone = computed(()=> batchList.value.filter(b=>b.status!=='wait'&&b.status!=='run').length);
    const batchOk = computed(()=> batchList.value.filter(b=>b.status==='ok').length);
    const batchPct = computed(()=> batchList.value.length ? Math.round(batchDone.value/batchList.value.length*100) : 0);

    async function runBatch(){
      const kws = batchText.value.split('\n').map(s=>s.trim()).filter(Boolean).slice(0,10);
      if(!kws.length){ toast('请先填写关键词（一行一个）', 'err'); return; }
      batchStop.value = false;
      batchRunning.value = true;
      batchList.value = kws.map(k=>({ keyword:k, status:'wait', len:0, note:'' }));
      for(let i=0;i<batchList.value.length;i++){
        if(batchStop.value){ batchList.value[i].status='wait'; batchList.value[i].note='已手动停止'; continue; }
        batchList.value[i].status = 'run';
        try{
          const r = await fetch('/api/generate',{method:'POST',headers:{'Content-Type':'application/json'},
            body: JSON.stringify({ keyword:batchList.value[i].keyword, platform:platform.value, model_id:selModel.value,
              real_data:realData.value, template_id:tplSel.value, account:accSel.value })});
          const d = await r.json();
          if(d.error){
            batchList.value[i].status='fail';
            batchList.value[i].note = d.message || '生成失败';
          } else {
            const content = d.content;
            const title = (content.match(/^#\s+(.+)$/m)||[])[1] || batchList.value[i].keyword;
            await fetch('/api/articles',{method:'POST',headers:{'Content-Type':'application/json'},
              body: JSON.stringify({ title, content, keyword:batchList.value[i].keyword, platform:platform.value,
                model:d.model||'', account:accSel.value, status:'generated' })});
            batchList.value[i].status='ok';
            batchList.value[i].len = content.length;
            batchList.value[i].note = title;
          }
        }catch(e){ batchList.value[i].status='fail'; batchList.value[i].note = String(e); }
      }
      batchRunning.value = false;
      loadArticles(); loadStats();
      toast(`批量完成：成功 ${batchOk.value}/${batchList.value.length} 篇`);
    }

    /* ---------- 关键词库 ---------- */
    const kwList = ref([]);
    const kwGroups = ref({});
    const kwIntents = ref(['信息型','导航型','交易型','本地型']);
    const kwForm = reactive({ keyword:'', group:'默认分组', intent:'信息型', difficulty:3, note:'' });
    const kwFilterGroup = ref('');
    const kwFilterQ = ref('');
    const expandSeed = ref('');
    const expandList = ref([]);
    const expandLoading = ref(false);

    async function loadKeywords(){
      const r = await fetch('/api/keywords'); const d = await r.json();
      kwList.value = d.keywords || []; kwGroups.value = d.groups || {}; kwIntents.value = d.intents || kwIntents.value;
    }
    const kwFiltered = computed(()=> kwList.value.filter(k=>
      (!kwFilterGroup.value || k.group===kwFilterGroup.value) &&
      (!kwFilterQ.value || k.keyword.includes(kwFilterQ.value))));
    async function addKeyword(){
      if(!kwForm.keyword.trim()){ toast('关键词不能为空', 'err'); return; }
      const r = await fetch('/api/keywords',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(kwForm)});
      const d = await r.json();
      if(d.error){ toast(d.message, 'err'); return; }
      kwForm.keyword=''; kwForm.note='';
      await loadKeywords(); loadStats(); toast('已加入词库 ✅');
    }
    async function delKeyword(id){ await fetch('/api/keywords/'+id,{method:'DELETE'}); await loadKeywords(); loadStats(); }
    async function doExpand(){
      if(!expandSeed.value.trim()){ toast('请先输入种子词', 'err'); return; }
      expandLoading.value = true; expandList.value = [];
      try{
        const r = await fetch('/api/keywords/expand',{method:'POST',headers:{'Content-Type':'application/json'},
          body: JSON.stringify({ seed:expandSeed.value, model_id:selModel.value, n:10 })});
        const d = await r.json();
        if(d.error){ toast(d.message, 'err'); return; }
        expandList.value = (d.keywords||[]).map(k=>({ ...k, picked:true }));
        if(!expandList.value.length) toast('没有拓展出词，换个种子词试试', 'info');
      }catch(e){ toast('拓展失败：'+e, 'err'); }
      finally{ expandLoading.value = false; }
    }
    async function importExpanded(){
      const picked = expandList.value.filter(e=>e.picked);
      if(!picked.length){ toast('请先勾选要入库的词', 'err'); return; }
      for(const e of picked){
        await fetch('/api/keywords',{method:'POST',headers:{'Content-Type':'application/json'},
          body: JSON.stringify({ keyword:e.keyword, intent:e.intent, difficulty:e.difficulty, group:expandSeed.value||'默认分组' })});
      }
      expandList.value = []; expandSeed.value='';
      await loadKeywords(); loadStats(); toast(`已入库 ${picked.length} 个词 ✅`);
    }

    /* ---------- 内容中心：选题 + 素材 ---------- */
    const contentTab = ref('topics');
    const topicKw = ref('');
    const recList = ref([]);
    const topicLoading = ref(false);
    async function addTopic(kw){
      if(!kw || !String(kw).trim()){ toast('请先输入选题', 'err'); return; }
      await fetch('/api/topics',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({keyword:kw})});
      topicKw.value=''; await loadTopics(); toast('已加入选题库 ✅');
    }
    async function delTopic(id){ await fetch('/api/topics/'+id,{method:'DELETE'}); await loadTopics(); }
    async function recommendTopics(){
      topicLoading.value = true; recList.value = [];
      try{
        const r = await fetch('/api/topics/recommend?seed='+encodeURIComponent(topicKw.value||keyword.value),{method:'POST'});
        const d = await r.json();
        if(d.error) toast('推荐失败：'+(d.message||''), 'err');
        else recList.value = d.topics || [];
      }catch(e){ toast('推荐失败：'+e, 'err'); }
      finally{ topicLoading.value = false; }
    }
    const snipForm = reactive({ title:'', content:'', tags:'', platform:'' });
    async function addSnippet(){
      if(!snipForm.content.trim()){ toast('素材内容不能为空', 'err'); return; }
      await fetch('/api/snippets',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(snipForm)});
      snipForm.title=''; snipForm.content=''; snipForm.tags='';
      await loadSnippets(); toast('素材已保存 ✅');
    }
    async function delSnippet(id){ await fetch('/api/snippets/'+id,{method:'DELETE'}); await loadSnippets(); }

    /* ---------- 社媒短内容（动态 / 视频） ---------- */
    const socKeyword = ref('');
    const socRealData = ref('');
    const socResult = ref('');
    const socError = ref('');
    const socLoading = ref(false);
    async function genSocial(){
      if(!socKeyword.value.trim()){ toast('请先填写主题', 'err'); return; }
      socLoading.value = true; socError.value = ''; socResult.value = '';
      try{
        const r = await fetch('/api/generate/social',{method:'POST',headers:{'Content-Type':'application/json'},
          body: JSON.stringify({ kind: view.value==='video'?'video':'post', platform:platform.value,
            keyword:socKeyword.value, model_id:selModel.value, real_data:socRealData.value, account:accSel.value })});
        const d = await r.json();
        if(d.error){
          const t = translateDeepSeek(d.message);
          socError.value = '❌ ' + (t ? `${t}（原文：${d.message}）` : d.message);
        } else {
          socResult.value = d.content;
          toast('生成完成 ✅');
        }
      }catch(e){ socError.value = '❌ 请求失败：'+e; }
      finally{ socLoading.value = false; }
    }
    async function saveSocial(){
      const title = (socResult.value.match(/^#\s+(.+)$/m)||[])[1] || socKeyword.value;
      await fetch('/api/articles',{method:'POST',headers:{'Content-Type':'application/json'},
        body: JSON.stringify({ title, content:socResult.value, keyword:socKeyword.value, platform:platform.value,
          status:'draft' })});
      loadArticles(); loadStats(); toast('已存为草稿 ✅');
    }

    /* ---------- 模板市场 ---------- */
    const tplForm = reactive({ name:'', category:'自定义', platform:'', outline:'', instruction:'' });
    async function addTemplate(){
      if(!tplForm.name.trim()){ toast('模板名不能为空', 'err'); return; }
      await fetch('/api/templates',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(tplForm)});
      tplForm.name=''; tplForm.outline=''; tplForm.instruction='';
      await loadTemplates(); toast('模板已创建 ✅');
    }
    async function delTemplate(id){
      const r = await fetch('/api/templates/'+id,{method:'DELETE'});
      const d = await r.json();
      if(d.error){ toast(d.message, 'err'); return; }
      await loadTemplates();
    }

    /* ---------- 账号定位 ---------- */
    const personaForm = reactive({ platform:'baidu', name:'', audience:'', tone:'', selling:'', taboo:'', extra:'' });
    async function addPersona(){
      if(!personaForm.name.trim()){ toast('账号名不能为空', 'err'); return; }
      await fetch('/api/personas',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(personaForm)});
      personaForm.name=''; personaForm.audience=''; personaForm.tone=''; personaForm.selling=''; personaForm.taboo=''; personaForm.extra='';
      await loadPersonas(); toast('人设已保存 ✅');
    }
    async function delPersona(id){ await fetch('/api/personas/'+id,{method:'DELETE'}); await loadPersonas(); }

    /* ---------- 知识库 ---------- */
    const docList = ref([]);
    const docForm = reactive({ title:'', content:'', tags:'' });
    const docDetail = ref(null);
    const kbQuery = ref('');
    const kbHits = ref([]);
    const kbTesting = ref(false);
    const kbTested = ref(false);
    async function loadDocs(){ const r = await fetch('/api/knowledge'); docList.value = (await r.json()).docs || []; }

    /* 文件导入建库：前端把文件读成 base64，后端解析（PDF/docx/xlsx/txt…） */
    const importTags = ref('');
    const importing = ref(false);
    const importLog = ref([]);
    async function importDocs(e){
      const files = Array.from(e.target.files || []);
      if(!files.length) return;
      importing.value = true; importLog.value = [];
      for(const f of files){
        try{
          const b64 = await new Promise((res, rej)=>{
            const fr = new FileReader();
            fr.onload = ()=> res(String(fr.result).split(',')[1] || '');
            fr.onerror = rej;
            fr.readAsDataURL(f);
          });
          const r = await fetch('/api/knowledge/import',{ method:'POST', headers:{'Content-Type':'application/json'},
            body: JSON.stringify({ filename:f.name, content_b64:b64, tags:importTags.value }) });
          const d = await r.json();
          if(d.error) importLog.value.push(`❌ ${f.name}：${d.message}`);
          else importLog.value.push(`✅ ${f.name} → 入库 ${d.count} 篇（解析出 ${d.chars} 字）`);
        }catch(err){ importLog.value.push(`❌ ${f.name}：${err}`); }
      }
      importing.value = false;
      e.target.value = '';            // 清空，方便同名文件重复导入
      await loadDocs(); loadStats();
    }
    async function addDoc(){
      if(!docForm.title.trim() || !docForm.content.trim()){ toast('标题和正文都要填', 'err'); return; }
      await fetch('/api/knowledge',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(docForm)});
      docForm.title=''; docForm.content=''; docForm.tags='';
      await loadDocs(); loadStats(); toast('资料已入库 ✅');
    }
    async function delDoc(id){ await fetch('/api/knowledge/'+id,{method:'DELETE'}); await loadDocs(); loadStats(); }
    async function viewDoc(id){ const r = await fetch('/api/knowledge/'+id); docDetail.value = await r.json(); }
    async function testKb(){
      if(!kbQuery.value.trim()){ toast('请输入检索词', 'err'); return; }
      kbTesting.value = true;
      try{
        // 直接复用后端检索：通过一次「不花钱」的生成前检索不方便，这里走后端 search 接口
        const r = await fetch('/api/knowledge/search?q='+encodeURIComponent(kbQuery.value));
        const d = await r.json();
        kbHits.value = d.hits || [];
        kbTested.value = true;
      }catch(e){ toast('检索失败：'+e, 'err'); }
      finally{ kbTesting.value = false; }
    }

    /* ---------- 模型中心 ---------- */
    const newModel = reactive({ label:'', model_name:'', api_base:'', key_env:'DEEPSEEK_API_KEY' });
    const modelMsg = ref(''); const modelMsgOk = ref(false);
    async function addModel(){
      if(!newModel.label || !newModel.model_name){ toast('显示名和模型名都要填', 'err'); return; }
      await fetch('/api/models',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(newModel)});
      newModel.label=''; newModel.model_name='';
      await loadModels(); toast('模型已添加 ✅');
    }
    async function setActive(id){ await fetch('/api/models/active',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({id})}); await loadModels(); loadStats(); toast('已切换生效模型 ✅'); }
    async function delModel(id){ await fetch('/api/models/'+id,{method:'DELETE'}); await loadModels(); loadStats(); }
    async function testModel(id){
      modelMsg.value='';
      const r = await fetch('/api/models/test',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({id})});
      const d = await r.json();
      modelMsgOk.value = !!d.ok; modelMsg.value = d.message || JSON.stringify(d);
    }

    /* ---------- 一键流水线 ---------- */
    const pipeForm = reactive({ keyword:'', platform:'baidu', model_id:'', template_id:'', real_data:'', product_ids:'', auto_cover:false, auto_push:false });
    const pipeSteps = ref([]);
    const pipeRunning = ref(false);
    const pipeArticleId = ref('');
    async function runPipeline(){
      if(!pipeForm.keyword.trim()){ toast('请先填写关键词', 'err'); return; }
      pipeRunning.value = true; pipeSteps.value = []; pipeArticleId.value = '';
      try{
        const r = await fetch('/api/pipeline/run',{method:'POST',headers:{'Content-Type':'application/json'},
          body: JSON.stringify({ ...pipeForm, account:accSel.value, product_ids: prodPicked.value.join(',') })});
        const d = await r.json();
        pipeSteps.value = d.steps || [];
        pipeArticleId.value = d.article_id || '';
        toast(d.ok ? '流水线执行完成 ✅' : '流水线有步骤失败，请查看结果', d.ok?'ok':'err');
      }catch(e){ toast('执行失败：'+e, 'err'); }
      finally{ pipeRunning.value = false; loadArticles(); loadStats(); }
    }
    async function viewArticleById(id){
      await loadArticles();
      const a = articles.value.find(x=>x.id===id);
      if(a) viewArticleData.value = a; else toast('未找到该文章', 'err');
    }

    /* ---------- 定时计划 ---------- */
    const scheduleList = ref([]);
    const dueList = ref([]);
    const schForm = reactive({ article_id:'', platform:'baidu', account:'', planned_at:'', note:'' });
    const schMsg = ref('');
    async function loadSchedule(){
      const r = await fetch('/api/schedule'); scheduleList.value = (await r.json()).schedule || [];
      const d = await fetch('/api/schedule/due'); dueList.value = (await d.json()).due || [];
    }
    async function createSchedule(){
      if(!schForm.article_id || !schForm.planned_at){ toast('请选择文章并填写时间', 'err'); return; }
      await fetch('/api/schedule',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(schForm)});
      schMsg.value = '✅ 已创建计划';
      schForm.article_id=''; schForm.planned_at=''; schForm.note='';
      await loadSchedule(); loadStats();
    }
    async function doneSchedule(id){ await fetch('/api/schedule/'+id+'/done',{method:'POST'}); await loadSchedule(); loadStats(); }
    async function delSchedule(id){ await fetch('/api/schedule/'+id,{method:'DELETE'}); await loadSchedule(); loadStats(); }

    /* ---------- 接口回调 ---------- */
    const hooks = ref([]);
    const hookEvents = ref({});
    const hookForm = reactive({ name:'', url:'', event:'all', enabled:true });
    const hookMsg = ref(''); const hookMsgOk = ref(false);
    async function loadHooks(){
      const r = await fetch('/api/webhooks'); const d = await r.json();
      hooks.value = d.hooks || []; hookEvents.value = d.events || {};
    }
    async function addHook(){
      if(!hookForm.url.trim()){ toast('回调地址不能为空', 'err'); return; }
      const r = await fetch('/api/webhooks',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(hookForm)});
      const d = await r.json();
      if(d.error){ toast(d.message, 'err'); return; }
      hookForm.name=''; hookForm.url='';
      await loadHooks(); toast('回调已添加 ✅');
    }
    async function delHook(id){ await fetch('/api/webhooks/'+id,{method:'DELETE'}); await loadHooks(); }
    async function toggleHook(id){ await fetch('/api/webhooks/'+id+'/toggle',{method:'POST'}); await loadHooks(); }
    async function testHook(id){
      hookMsg.value='';
      const r = await fetch('/api/webhooks/'+id+'/test',{method:'POST'});
      const d = await r.json();
      hookMsgOk.value = !!d.ok; hookMsg.value = (d.ok?'✅ ':'❌ ') + (d.message||'');
      await loadHooks();
    }

    /* ---------- 多账号矩阵 ---------- */
    const accounts = ref([]);
    const accForm = reactive({ platform:'xiaohongshu', name:'', url:'', note:'', is_default:false });
    const accountGroups = computed(()=>{
      const map = {};
      for(const a of accounts.value){ (map[a.platform] = map[a.platform] || []).push(a); }
      return Object.keys(map).map(k=>({ platform:k, name:platformName(k), items:map[k] }));
    });
    async function loadAccounts(){ const r = await fetch('/api/accounts'); accounts.value = (await r.json()).accounts || []; }

    /* 账号发布预设：这个账号每次发文都要填的固定项，存一次省得反复填 */
    const presetEditing = ref('');
    const blankPreset = ()=>({ tags:'', category:'', visibility:'', cover:'', extra:'' });
    const presetForm = reactive(blankPreset());
    const presetFilled = (p)=> !!(p && (p.tags || p.category || p.visibility || p.cover || p.extra));
    function openPreset(a){
      if(presetEditing.value === a.id){ presetEditing.value = ''; return; }
      Object.assign(presetForm, blankPreset(), a.preset || {});
      presetEditing.value = a.id;
    }
    async function savePreset(aid){
      const r = await fetch('/api/accounts/'+aid,{ method:'PUT', headers:{'Content-Type':'application/json'},
        body: JSON.stringify({ preset: { ...presetForm } }) });
      const d = await r.json();
      if(d.error){ toast(d.message || '保存失败', 'err'); return; }
      presetEditing.value = ''; await loadAccounts(); toast('发布预设已保存 ✅');
    }
    async function addAccount(){
      if(!accForm.name.trim()){ toast('账号名不能为空', 'err'); return; }
      await fetch('/api/accounts',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(accForm)});
      accForm.name=''; accForm.url=''; accForm.note=''; accForm.is_default=false;
      await loadAccounts(); loadStats(); toast('账号已添加 ✅');
    }
    async function delAccount(id){ await fetch('/api/accounts/'+id,{method:'DELETE'}); await loadAccounts(); loadStats(); }
    async function setDefault(id){ await fetch('/api/accounts/default',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({id})}); await loadAccounts(); }

    /* ---------- 文章库 ---------- */
    const articles = ref([]);
    const viewArticleData = ref(null);
    async function loadArticles(){ const r = await fetch('/api/articles'); articles.value = await r.json(); }
    function viewArticle(a){ viewArticleData.value = a; }
    async function delArticle(id){
      if(!confirm('删除后可在「回收站」里恢复，确定删除？')) return;
      await fetch('/api/articles/'+id,{method:'DELETE'});
      loadArticles(); viewArticleData.value=null; loadStats();
      toast('已移入回收站', 'info');
    }

    /* ---------- 回收站（防误删） ---------- */
    const trashOpen = ref(false);
    const trashList = ref([]);
    async function loadTrash(){ const r = await fetch('/api/trash'); trashList.value = (await r.json()).trash || []; }
    async function openTrash(){ await loadTrash(); trashOpen.value = true; }
    async function restoreArticle(id){
      await fetch('/api/trash/'+id+'/restore',{method:'POST'});
      await loadTrash(); await loadArticles(); loadStats();
      toast('已恢复到文章库');
    }
    async function purgeTrash(){
      if(!confirm('清空回收站？这些文章将无法再恢复。')) return;
      await fetch('/api/trash',{method:'DELETE'});
      trashList.value = [];
      toast('回收站已清空', 'info');
    }
    const statusText = (s)=> ({draft:'草稿',generated:'已生成',checked:'已检测',pushed:'已推送',published:'已发布',pending:'待发布',done:'已发布'}[s]||s);
    const statusCls = (s)=> ({draft:'tag n',generated:'tag a',checked:'tag b',pushed:'tag g',published:'tag g'}[s]||'tag n');

    /* ---------- 发布 / 导出 ---------- */
    const pubModal = ref({ open:false, content:'', urls:'', articleId:'', loading:false, result:null });
    const pushDisplay = computed(()=>{
      const r = pubModal.value.result; if(!r) return null;
      if(r.error && !("success" in r)) return { cls:"err", zh: r.message || "推送失败", en: JSON.stringify(r) };
      if(typeof r.success === "number") return { cls:"ok", zh:`百度推送成功：本次 ${r.success} 条，今日剩余 ${r.remain ?? "未知"} 条`, en: JSON.stringify(r) };
      if(r.error){ const zh = translateBaiduMsg(r.message) || r.message || "未知错误"; return { cls:"err", zh, en: JSON.stringify(r) }; }
      return { cls:"ok", zh:"操作完成", en: JSON.stringify(r) };
    });
    async function fillUrls(aid){ const r = await fetch('/api/articles/'+aid+'/url'); const d = await r.json(); return d.url || ''; }
    async function openPublish(){
      pubModal.value = { open:true, content:genResult.value, urls:'', articleId:lastSavedId, loading:false, result:null };
      if(currentPlatform.value.mode==='auto' && lastSavedId) pubModal.value.urls = await fillUrls(lastSavedId);
    }
    async function openPublishFromArticle(a){
      lastSavedId = a.id;
      pubModal.value = { open:true, content:a.content, urls:'', articleId:a.id, loading:false, result:null };
      if(currentPlatform.value.mode==='auto') pubModal.value.urls = await fillUrls(a.id);
    }
    async function doPush(){
      pubModal.value.loading = true; pubModal.value.result = null;
      const urls = pubModal.value.urls.split('\n').map(s=>s.trim()).filter(Boolean);
      try{
        const r = await fetch('/api/push',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({platform:'baidu', urls})});
        const data = await r.json(); pubModal.value.result = data;
        if(data && data.success && lastSavedId){
          await fetch('/api/articles/'+lastSavedId+'/status',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({status:'published'})});
          loadArticles(); loadStats();
        }
      }catch(e){ pubModal.value.result = {error:true, message:String(e)}; }
      finally{ pubModal.value.loading = false; }
    }
    async function doPushArticle(){
      const aid = pubModal.value.articleId;
      if(!aid){ toast('请先在写作台保存文章', 'err'); return; }
      pubModal.value.loading = true; pubModal.value.result = null;
      try{
        const r = await fetch('/api/articles/'+aid+'/push',{method:'POST'});
        pubModal.value.result = await r.json();
        loadArticles(); loadStats();
      }catch(e){ pubModal.value.result = {error:true, message:String(e)}; }
      finally{ pubModal.value.loading = false; }
    }

    const exportModal = ref({ open:false, title:'', html:'', url:'', file:'', slug:'' });
    async function exportArticle(a){
      const r = await fetch('/api/articles/'+a.id+'/export',{method:'POST'});
      const d = await r.json();
      if(d.error){ toast(d.message||'导出失败', 'err'); return; }
      exportModal.value = { open:true, title:a.title||'', html:d.html, url:d.url, file:d.file, slug:d.slug };
    }
    function downloadHtml(html, filename){
      if(!html) return;
      const blob = new Blob([html], {type:'text/html;charset=utf-8'});
      const a = document.createElement('a');
      a.href = URL.createObjectURL(blob);
      a.download = filename || 'seo.html';
      a.click();
      URL.revokeObjectURL(a.href);
    }

    /* ---------- 收录检测 ---------- */
    const idxUrls = ref('');
    const idxResults = ref([]);
    const idxLoading = ref(false);
    const idxNote = ref('');
    const idxStatusText = (s)=> ({indexed:'已收录', not_indexed:'未收录', unknown:'未知'}[s]||s);
    async function runIndexCheck(){
      const urls = idxUrls.value.split('\n').map(s=>s.trim()).filter(Boolean);
      if(!urls.length){ toast('请先填入 URL', 'err'); return; }
      idxLoading.value = true; idxResults.value = []; idxNote.value='';
      try{
        const r = await fetch('/api/index-check',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({urls})});
        const d = await r.json();
        if(d.error){ toast(d.message, 'err'); return; }
        idxResults.value = d.results || [];
        idxNote.value = d.note || '';
      }catch(e){ toast('检测失败：'+e, 'err'); }
      finally{ idxLoading.value = false; loadDatacenter(); }
    }
    async function fillArticleUrls(){
      const list = articles.value.slice(0,10);
      const urls = [];
      for(const a of list){ const u = await fillUrls(a.id); if(u) urls.push(u); }
      if(!urls.length){ toast('没有可用 URL（需先配置站点域名）', 'err'); return; }
      idxUrls.value = urls.join('\n');
      toast(`已填入 ${urls.length} 条 URL`);
    }

    /* ---------- 违禁词 ---------- */
    const wordsData = ref({ common:[], platform:{} });
    const wordTips = ref({});
    const checkPlatform = ref('');
    const wordPlatform = ref('');
    const newWord = ref('');
    const checkTextInput = ref('');
    const checkResult = ref([]);
    const checkDone = ref(false);
    async function loadWords(){
      const r = await fetch('/api/banned-words'); const d = await r.json();
      wordsData.value = { common:d.common||[], platform:d.platform||{} };
      wordTips.value = d.tips || {};
    }
    async function addWord(){
      if(!newWord.value.trim()) { toast('请输入违禁词', 'err'); return; }
      await fetch('/api/banned-words',{method:'POST',headers:{'Content-Type':'application/json'},
        body: JSON.stringify({ word:newWord.value, platform:wordPlatform.value })});
      newWord.value=''; await loadWords(); loadStats(); toast('已添加 ✅');
    }
    async function delWord(w, pk){
      await fetch('/api/banned-words?word='+encodeURIComponent(w)+'&platform='+encodeURIComponent(pk||''),{method:'DELETE'});
      await loadWords(); loadStats();
    }
    async function doCheck(){
      if(!checkTextInput.value.trim()){ toast('请先粘贴文案', 'err'); return; }
      const r = await fetch('/api/check',{method:'POST',headers:{'Content-Type':'application/json'},
        body: JSON.stringify({ text:checkTextInput.value, platform:checkPlatform.value })});
      checkResult.value = (await r.json()).matches || [];
      checkDone.value = true;
    }
    const uniqueWords = (arr)=> [...new Set(arr.map(m=>m.word))];

    /* ---------- 密钥 / 站点配置 ---------- */
    const keyStatus = ref({});
    const keyForm = reactive({ DEEPSEEK_API_KEY:'', SILICONFLOW_API_KEY:'', IMAGE_API_BASE:'', IMAGE_API_KEY:'', IMAGE_MODEL:'' });
    const keyMsg = ref(''); const keyMsgOk = ref(false); const keyMsgSrc = ref('');
    async function loadKeys(){
      const r = await fetch('/api/config'); const cfg = await r.json();
      keyStatus.value = {
        DEEPSEEK_API_KEY: cfg.DEEPSEEK_API_KEY_configured, SILICONFLOW_API_KEY: cfg.SILICONFLOW_API_KEY_configured,
        IMAGE_API_KEY: cfg.IMAGE_API_KEY_configured, BAIDU_SITE: !!cfg.BAIDU_SITE, BAIDU_TOKEN: cfg.BAIDU_TOKEN_configured
      };
      keyForm.IMAGE_API_BASE = cfg.IMAGE_API_BASE || '';
      keyForm.IMAGE_MODEL = cfg.IMAGE_MODEL || '';
    }
    async function saveKey(){
      await fetch('/api/config',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(keyForm)});
      keyForm.DEEPSEEK_API_KEY=''; keyForm.SILICONFLOW_API_KEY='';
      await loadKeys(); loadStats(); toast('密钥已保存 ✅');
    }
    async function saveImageKey(){
      await fetch('/api/config',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(keyForm)});
      keyForm.IMAGE_API_KEY='';
      await loadKeys(); loadStats(); toast('配图配置已保存 ✅');
    }
    async function testKey(kind){
      keyMsg.value=''; keyMsgSrc.value='';
      const r = await fetch('/api/config/test?kind='+kind,{method:'POST'});
      const d = await r.json();
      keyMsgOk.value = !!d.ok;
      keyMsg.value = (d.ok?'✅ ':'❌ ') + (d.message || JSON.stringify(d));
      keyMsgSrc.value = d.raw ? String(d.raw).slice(0,180) : '';
    }

    const configForm = reactive({ BAIDU_SITE:'', BAIDU_TOKEN:'' });
    const configMsg = ref('');
    async function loadConfig(){
      const r = await fetch('/api/config'); const cfg = await r.json();
      configForm.BAIDU_SITE = cfg.BAIDU_SITE || '';
      configForm.BAIDU_TOKEN = '';
    }
    async function saveConfig(){
      await fetch('/api/config',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(configForm)});
      configMsg.value = '配置已保存 ✅'; loadStats();
    }
    async function openScheduleFromPub(){
      if(!lastSavedId){ toast('请先保存文章再定时', 'err'); return; }
      schForm.article_id = lastSavedId;
      schForm.platform = platform.value;
      pubModal.value.open = false;
      view.value = 'automation';
      await loadSchedule();
      toast('已跳到「定时计划」，填时间即可', 'info');
    }

    /* ---------- 一键分发（对标 ALQQ / 小火花：一次操作铺到多个平台）---------- */
    const distTargets = ref({ auto: [], accounts: [] });
    const distPicked = ref([]);          // 勾选的目标 id 列表
    const distArticleId = ref('');
    const distTags = ref('');            // 额外话题标签，会加到各平台
    const distTasks = ref([]);
    const distSummary = ref({ total: 0, done: 0, pending: 0, failed: 0 });
    const distRunning = ref(false);
    const distPreviewOpen = ref(false);
    const distPreviewData = ref([]);
    const distPreviewLoading = ref(false);

    const distArticle = computed(()=> articles.value.find(a=>a.id===distArticleId.value) || null);
    const distArticleChars = computed(()=> (distArticle.value && distArticle.value.content || '').length);
    const distAll = computed(()=> distTargets.value.auto.concat(distTargets.value.accounts));

    // 已勾选目标涉及到的平台（预览按平台去重）
    const distPickedPlatforms = computed(()=>{
      const s = new Set();
      distPicked.value.forEach(id=>{
        const t = distAll.value.find(x=>x.id===id);
        if(t) s.add(t.platform);
      });
      return [...s];
    });

    // 账号按平台分组，方便「全选本组」
    const distGroups = computed(()=>{
      const map = new Map();
      for(const a of distTargets.value.accounts){
        if(!map.has(a.platform))
          map.set(a.platform, { platform:a.platform, name:a.platform_name, format:a.format||{}, items:[] });
        map.get(a.platform).items.push(a);
      }
      return [...map.values()];
    });

    async function loadDistTargets(){
      try{
        const r = await fetch('/api/distribute/targets');
        const d = await r.json();
        distTargets.value = { auto:d.auto||[], accounts:d.accounts||[] };
      }catch(e){ toast('分发目标加载失败：'+e, 'err'); }
    }

    async function loadDistTasks(){
      try{
        const r = await fetch('/api/distribute/tasks?limit=60');
        const d = await r.json();
        distTasks.value = d.tasks || [];
        distSummary.value = d.summary || { total:0, done:0, pending:0, failed:0 };
      }catch(e){ /* 静默 */ }
    }

    function distPickAll(){
      distPicked.value = distTargets.value.auto.filter(t=>t.available).map(t=>t.id)
        .concat(distTargets.value.accounts.map(a=>a.id));
    }
    function distPickNone(){ distPicked.value = []; }
    function distPickGroup(g){
      const ids = g.items.map(a=>a.id);
      if(ids.every(i=>distPicked.value.includes(i)))
        distPicked.value = distPicked.value.filter(i=>!ids.includes(i));
      else
        distPicked.value = [...new Set(distPicked.value.concat(ids))];
    }

    async function runDistribute(){
      if(!distArticleId.value || !distPicked.value.length) return;
      distRunning.value = true;
      try{
        const r = await fetch('/api/distribute', {
          method:'POST', headers:{'Content-Type':'application/json'},
          body: JSON.stringify({ article_id:distArticleId.value,
                                 targets:distPicked.value, extra_tags:distTags.value })
        });
        const d = await r.json();
        if(d.error){ toast(d.message || '分发失败', 'err'); }
        else{
          toast('已分发到 ' + d.count + ' 个目标（自动的已跑完，社媒待你确认）');
          await loadDistTasks();
          loadStats();
        }
      }catch(e){ toast('分发失败：'+e, 'err'); }
      finally{ distRunning.value = false; }
    }

    async function distPreview(){
      if(!distArticleId.value) return;
      const plats = distPickedPlatforms.value;
      if(!plats.length){ toast('先勾选要分发的目标，才知道要预览哪些平台', 'err'); return; }
      distPreviewLoading.value = true;
      try{
        const rs = await Promise.all(plats.map(p=>
          fetch('/api/distribute/preview', {
            method:'POST', headers:{'Content-Type':'application/json'},
            body: JSON.stringify({ article_id:distArticleId.value, platform:p, extra_tags:distTags.value })
          }).then(x=>x.json())
        ));
        distPreviewData.value = rs.reduce((acc,d)=> acc.concat(d.items||[]), []);
        distPreviewOpen.value = true;
      }catch(e){ toast('预览失败：'+e, 'err'); }
      finally{ distPreviewLoading.value = false; }
    }

    // 复制并打开：大多数平台发布框能直接粘贴，一次点击就把这一步做完
    function distCopy(t){ copyText(t.copy_text || t.body || ''); }
    function distCopyOpen(t){
      distCopy(t);
      if(t.publish_url) window.open(t.publish_url, '_blank', 'noopener');
      else toast('这个平台没登记发布地址，去「多账号矩阵」补上主页链接', 'err');
    }
    const distOpen = distCopyOpen;   // 旧名字保留，别的地方还在用

    async function distDone(t){
      try{
        const r = await fetch('/api/distribute/'+t.id+'/done', {
          method:'POST', headers:{'Content-Type':'application/json'}, body:'{}' });
        const d = await r.json();
        if(d.error) toast(d.message, 'err');
        else { toast('已标记为发布完成'); await loadDistTasks(); loadStats(); }
      }catch(e){ toast('操作失败：'+e, 'err'); }
    }
    async function distUndone(t){
      try{ await fetch('/api/distribute/'+t.id+'/pending', {method:'POST'}); }
      catch(e){}
      await loadDistTasks();
    }
    async function distRetry(t){
      try{
        const r = await fetch('/api/distribute/'+t.id+'/retry', {method:'POST'});
        const d = await r.json();
        toast(d.error ? (d.message||'重试失败') : '已重试', d.error ? 'err' : 'ok');
      }catch(e){ toast('重试失败：'+e, 'err'); }
      await loadDistTasks();
    }
    async function clearDist(){
      if(!confirm('清空所有分发记录？（已发布的文章不受影响）')) return;
      try{ await fetch('/api/distribute', {method:'DELETE'}); }catch(e){}
      await loadDistTasks();
      toast('分发记录已清空');
    }
    // 删掉队列里的某一条（原来只能整表清空，没法只去掉一条）
    async function distRemove(t){
      if(!confirm('把这条（'+(t.platform_name||'')+'）从队列删掉？')) return;
      try{
        const r = await fetch('/api/distribute/'+t.id, {method:'DELETE'});
        const d = await r.json();
        toast(d.ok ? '已删除这一条' : (d.message||'删除失败'), d.ok ? 'ok' : 'err');
      }catch(e){ toast('删除失败：'+e, 'err'); }
      await loadDistTasks(); loadStats();
    }
    async function purgeDistDone(){
      try{
        const r = await fetch('/api/distribute/purge-done', {method:'POST'});
        const d = await r.json();
        toast(`已清掉 ${d.removed || 0} 条已完成的`);
      }catch(e){ toast('清理失败：'+e, 'err'); }
      await loadDistTasks(); loadStats();
    }
    function distStatusText(s){
      return { pending:'待发布', done:'已完成', failed:'失败' }[s] || s;
    }

    // 从文章库直接跳过来：带上稿子，并默认勾好「自动通道 + 各平台默认账号」，
    // 这样一进页面就能直接点「一键分发」，不用再手点一遍
    async function distFromArticle(a){
      distArticleId.value = a.id;
      distPreviewOpen.value = false;
      await loadDistTargets();
      distPicked.value = distTargets.value.auto.filter(t=>t.available).map(t=>t.id)
        .concat(distTargets.value.accounts.filter(x=>x.is_default).map(x=>x.id));
      view.value = 'distribute';
      loadDistTasks();
    }

    /* ---------- 文章创作（自己写 / 从别处粘贴 / 让 AI 帮改）----------
       对标 ALQQ 的「文章创作」：标题 + 正文编辑器 + 工具栏 + 预览。
       不用富文本编辑器（会引入一堆依赖，且富文本存进库还得转回 Markdown），
       直接写 Markdown，预览就在旁边看效果。 */
    const cf = reactive({ title:'', body:'', platform:'baidu', keyword:'' });
    const cfTab = ref('edit');
    const cfSel = ref('');
    const cfAsk = ref('');
    const cfAiOut = ref('');
    const cfAiBusy = ref(false);
    const cfErr = ref('');
    const cfLastMode = ref('');
    const cfMatches = ref([]);
    const cfArea = ref(null);
    const cfHtml = computed(()=> renderContent(cf.body, []));

    // 在光标处插入格式标记（选中了文字就包住它）
    function cfInsert(before, after, fallback){
      const el = cfArea.value, t = cf.body || '';
      if(!el){ cf.body = t + '\n' + before + (fallback||'') + after; return; }
      const s = el.selectionStart ?? t.length, e = el.selectionEnd ?? t.length;
      const sel = t.slice(s, e) || fallback || '';
      cf.body = t.slice(0, s) + before + sel + after + t.slice(e);
      nextTick(()=>{ el.focus(); const p = s + before.length + sel.length; el.setSelectionRange(p, p); });
    }
    const mdWrap = (b, a='')=> cfInsert(b, a, '');
    // 行首前缀（列表 / 引用 / 编号）：加给光标所在行
    function mdLine(prefix){
      const el = cfArea.value, t = cf.body || '';
      if(!el){ cf.body = prefix + t; return; }
      const s = el.selectionStart ?? 0;
      const ls = t.lastIndexOf('\n', s - 1) + 1;
      cf.body = t.slice(0, ls) + prefix + t.slice(ls);
      nextTick(()=>{ el.focus(); el.setSelectionRange(s + prefix.length, s + prefix.length); });
    }
    function mdLink(){
      const u = prompt('链接地址（https://…）');
      if(u) cfInsert('[', ']('+u+')', '链接文字');
    }
    function mdImage(){
      const u = prompt('图片地址', (coverResult.value && coverResult.value.image_url) || '');
      if(u) cfInsert('![', ']('+u+')', '图片说明');
    }
    const mdHr = ()=> cfInsert('\n---\n', '', '');
    // Tab 键插两个空格（默认会跳走焦点，写文章时很烦）
    function cfTabKey(e){
      const el = e.target, s = el.selectionStart;
      cf.body = cf.body.slice(0, s) + '  ' + cf.body.slice(el.selectionEnd);
      nextTick(()=>{ el.setSelectionRange(s + 2, s + 2); });
    }

    async function cfSave(){
      const body = (cf.body||'').trim();
      if(!body && !(cf.title||'').trim()){ toast('标题和正文都还是空的', 'err'); return null; }
      const title = (cf.title||'').trim() || (cf.body.match(/^#\s+(.+)$/m)||[])[1] || '未命名文章';
      try{
        const r = await fetch('/api/articles',{method:'POST',headers:{'Content-Type':'application/json'},
          body: JSON.stringify({ title, content:cf.body, keyword:cf.keyword, platform:cf.platform,
            status:'draft', cover:(coverResult.value && coverResult.value.image_url) || '' })});
        const a = await r.json();
        toast('已存进文章库 ✅');
        loadArticles(); loadStats();
        return a;
      }catch(e){ toast('保存失败：'+e, 'err'); return null; }
    }
    // 存一份再跳分发页（分发要有文章 id，所以这一步是必须的，但用户不用自己点）
    async function cfDistribute(){
      if(!(cf.body||'').trim()){ toast('正文还是空的，先写点内容', 'err'); return; }
      const a = await cfSave();
      if(a && a.id) await distFromArticle(a);
    }
    async function cfDetect(){
      if(!(cf.body||'').trim()){ toast('正文还是空的', 'err'); return; }
      const r = await fetch('/api/check',{method:'POST',headers:{'Content-Type':'application/json'},
        body: JSON.stringify({ text:cf.body, platform:cf.platform })});
      cfMatches.value = (await r.json()).matches || [];
      toast(cfMatches.value.length ? `检出 ${cfMatches.value.length} 处违禁词`
                                   : '未检出违禁词 ✅', cfMatches.value.length ? 'err' : 'ok');
    }
    async function cfCover(){
      const kw = (cf.keyword||'').trim() || (cf.title||'').trim();
      if(!kw){ toast('先写个标题或关键词，配图才有依据', 'err'); return; }
      if(coverLoading.value) return;
      coverLoading.value = true;
      try{
        const r = await fetch('/api/images',{method:'POST',headers:{'Content-Type':'application/json'},
          body: JSON.stringify({ keyword:kw, platform:cf.platform,
            article_text:cf.body, writing:{...wcfg} })});
        coverResult.value = await r.json();
        if(coverResult.value.image_url) toast('配图生成好了 ✅');
        else toast(coverResult.value.note || '没出图', 'err');
      }catch(e){ toast('出图失败：'+e, 'err'); }
      finally{ coverLoading.value = false; }
    }
    function cfClear(){
      if(!confirm('清空当前内容重写？没存进文章库的内容会丢。')) return;
      cf.title=''; cf.body=''; cf.keyword=''; cfAiOut=''; cfMatches.value=[];
    }
    // 让 AI 改一段或整篇。cfSel 有内容就只改那段
    async function cfAssist(mode){
      const text = (cfSel.value||'').trim() || (cf.body||'').trim();
      if(!text){ toast('把要改的段落填进来，或先在正文里写点内容', 'err'); return; }
      cfAiBusy.value = true; cfErr.value=''; cfLastMode.value = mode; cfAiOut.value='';
      try{
        const r = await fetch('/api/assist',{method:'POST',headers:{'Content-Type':'application/json'},
          body: JSON.stringify({ text, mode, instruction:cfAsk.value })});
        const d = await r.json();
        if(d.error) cfErr.value = d.message || 'AI 处理失败，去「API 密钥」检查模型';
        else if(!(d.content||'').trim()) cfErr.value = '模型返回了空内容，换个模型或再试一次';
        else cfAiOut.value = d.content;
      }catch(e){ cfErr.value = '请求失败：'+e; }
      finally{ cfAiBusy.value = false; }
    }
    function cfApply(){
      if(!cfAiOut.value) return;
      if((cfSel.value||'').trim() && cf.body.includes(cfSel.value)){
        cf.body = cf.body.replace(cfSel.value, cfAiOut.value);   // 只换选中的那段
      }else{
        cf.body = cfAiOut.value;                                  // 否则整篇替换
      }
      cfAiOut.value=''; cfSel.value=''; cfErr.value='';
      cfTab.value = 'edit';
      toast('已替换进正文');
    }
    function cfApplyTitle(){
      if(!cfAiOut.value) return;
      cf.title = cfAiOut.value.split('\n')[0].replace(/^[#\d.、)（\s]+/, '').trim();
      cfAiOut.value=''; toast('标题已更新');
    }

    /* ---------- 初始化 ---------- */
    onMounted(async ()=>{
      const p = await fetch('/api/platforms'); platforms.value = (await p.json()).platforms || [];
      await Promise.all([loadStats(), loadArticles(), loadModels(), loadTemplates(), loadPersonas(),
        loadTopics(), loadSnippets(), loadKeywords(), loadDocs(), loadAccounts(), loadSchedule(),
        loadHooks(), loadWords(), loadKeys(), loadConfig(), loadDatacenter(), loadProducts(),
        loadProviders(), loadWritingOptions(), loadPresets(), loadDistTasks()]);
    });

    return {
      // 基础
      view, go, navOpen, toggleGroup, platforms, platform, currentPlatform, platformName,
      stats, pushLog, toasts, toast,
      themeMode, themeLabel, themeOpen, themeOptions, setTheme, toggleThemeMenu,
      // 数据中心
      dcFilter, dc, loadDatacenter, resetDc, dcArtPoints, dcPushPoints, dcMaxY,
      // 一键分发
      distTargets, distPicked, distArticleId, distTags, distTasks, distSummary, distRunning,
      distArticle, distArticleChars, distGroups, distPickedPlatforms,
      loadDistTargets, loadDistTasks, distPickAll, distPickNone, distPickGroup,
      runDistribute, distPreview, distPreviewOpen, distPreviewData, distPreviewLoading,
      distCopy, distOpen, distCopyOpen, distDone, distUndone, distRetry, clearDist,
      distRemove, purgeDistDone, distStatusText,
      distFromArticle,
      // 写作台
      writeStep, aiReady,
      // 写作配置 / 预设 / 百度就绪诊断
      wOpts, wcfg, optItems, optNote, writingSummary, loadWritingOptions, wcfgOpen,
      presetList, presetSel, applyPreset, promptSavePreset, delPreset,
      readiness, rdLoading, loadReadiness, rdMark,
      trashOpen, trashList, openTrash, loadTrash, restoreArticle, purgeTrash,
      keyword, topicSel, realData, genResult, genError, genLoading, genModel, matches, rendered,
      coverResult, coverLoading, generate, detect, makeCover, copyMarkdown, copyRich, copyText, saveArticle,
      absUrl, downloadImage, coverToBody, distFromDraft, genToCreate,
      // 文章创作（自己写）
      cf, cfTab, cfSel, cfAsk, cfAiOut, cfAiBusy, cfErr, cfLastMode, cfMatches, cfArea, cfHtml,
      mdWrap, mdLine, mdLink, mdImage, mdHr, cfTabKey,
      cfSave, cfDistribute, cfDetect, cfCover, cfClear, cfAssist, cfApply, cfApplyTitle,
      selModel, modelList, tplSel, tplListForPlatform, tplListAll, accSel, personaListForPlatform,
      topics, snippets, snipSel, insertSnip,
      // 批量
      batchText, batchList, batchRunning, batchStop, batchDone, batchOk, batchPct, runBatch,
      // 关键词
      kwList, kwGroups, kwIntents, kwForm, kwFilterGroup, kwFilterQ, kwFiltered,
      addKeyword, delKeyword, expandSeed, expandList, expandLoading, doExpand, importExpanded,
      // 产品库
      productList, prodCats, prodPicked, toggleProd, prodForm, prodMsg, prodMsgType, saveProduct,
      editProduct, resetProdForm, delProduct, loadProducts, prodFilterCat, prodFilterQ,
      prodQuery, prodCtx, prodTested, prodTesting, testProdMatch,
      // 内容中心
      contentTab, topicKw, recList, topicLoading, addTopic, delTopic, recommendTopics,
      snipForm, addSnippet, delSnippet,
      // 社媒
      socKeyword, socRealData, socResult, socError, socLoading, genSocial, saveSocial, renderContent,
      // 模板 / 人设 / 知识库 / 模型
      tplForm, addTemplate, delTemplate,
      personaForm, addPersona, personaList, delPersona,
      docList, docForm, docDetail, kbQuery, kbHits, kbTesting, kbTested, addDoc, delDoc, viewDoc, testKb,
      importTags, importing, importLog, importDocs,
      newModel, modelMsg, modelMsgOk, addModel, setActive, delModel, testModel,
      // 流水线
      pipeForm, pipeSteps, pipeRunning, pipeArticleId, runPipeline, viewArticleById,
      // 定时
      scheduleList, dueList, schForm, schMsg, createSchedule, doneSchedule, delSchedule,
      // webhooks
      hooks, hookEvents, hookForm, hookMsg, hookMsgOk, addHook, delHook, toggleHook, testHook,
      // 账号
      accounts, accForm, accountGroups, addAccount, delAccount, setDefault,
      presetEditing, presetForm, presetFilled, openPreset, savePreset,
      // 文章
      articles, viewArticleData, viewArticle, delArticle, statusText, statusCls,
      exportModal, exportArticle, downloadHtml,
      pubModal, openPublish, openPublishFromArticle, doPush, doPushArticle, pushDisplay, openScheduleFromPub,
      // 收录
      idxUrls, idxResults, idxLoading, idxNote, runIndexCheck, idxStatusText, fillArticleUrls,
      // 违禁词
      wordsData, wordTips, checkPlatform, wordPlatform, newWord, addWord, delWord,
      checkTextInput, checkResult, checkDone, doCheck, uniqueWords,
      // 密钥 / 配置 / 服务商
      keyStatus, keyForm, keyMsg, keyMsgOk, keyMsgSrc, saveKey, saveImageKey, testKey,
      providers, providerGroups, activeModel, activeProviderShort, providersByGroup, curProvider,
      expandedProvider, pvModel, pvBase, pvKey, pvMsg, pvOk,
      pickProvider, saveProvider, testProvider, testActiveModel,
      configForm, configMsg, saveConfig,
    };
  }
}).mount('#app');
