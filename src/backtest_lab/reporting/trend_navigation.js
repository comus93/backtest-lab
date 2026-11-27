// Trend Research only. The manifest is manually maintained.
(() => {
  const nav = document.getElementById("trend-navigation");
  if (!nav) return;
  const base = new URL(".", document.currentScript.src);
  const current = nav.dataset.asset;
  const requested = new URLSearchParams(location.search).get("strategy");
  const selector = () => (window.Bokeh?.documents || [])
    .map(d => d.get_model_by_name("trade-strategy-select")).find(Boolean);
  const style = document.createElement("style");
  style.textContent = "#trend-navigation{display:flex;flex-wrap:wrap;gap:8px;padding:12px 16px;font:14px system-ui;border-bottom:1px solid #dbe2ea;background:#f8fafc}#trend-navigation a,#trend-navigation span{padding:6px 10px;border-radius:5px;color:#334155}#trend-navigation a[aria-current=page]{background:#dbeafe;color:#1d4ed8;font-weight:600}#trend-navigation span{color:#64748b}";
  document.head.append(style);
  async function setup() {
    const response = await fetch(new URL("assets.json", base), {cache:"no-cache"});
    if (!response.ok) throw Error("asset manifest unavailable");
    const assets = await response.json();
    nav.replaceChildren();
    const home = document.createElement("a");
    home.href = new URL("../../",base);
    home.textContent = "Research Index";
    nav.append(home);
    const links = [];
    for (const asset of assets) {
      const url = new URL(asset.page,base);
      // During the initial migration a configured asset may not yet have a run.
      const available = await fetch(url,{method:"HEAD"}).then(r=>r.ok).catch(()=>false);
      const link = document.createElement(available ? "a" : "span");
      link.textContent = asset.label+" · "+asset.long+(available?"":" (pending)");
      if (available) {
        link.href=url;
        if (asset.id===current) link.setAttribute("aria-current","page");
        links.push([link,url]);
        link.addEventListener("click",e=>{
          const strategy=selector()?.value || requested;
          if(strategy) {
            const next=new URL(url); next.searchParams.set("strategy",strategy);
            link.href=next;
          }
        });
      }
      nav.append(link);
    }
    function updateLinks(value) {
      for (const [link,url] of links) {
        const next=new URL(url);
        if(value) next.searchParams.set("strategy",value);
        link.href=next;
      }
    }
    if (!current) { updateLinks(requested); return; }
    let attempts=0;
    const timer=setInterval(()=>{
      const s=selector();
      if (!s && ++attempts<200) return;
      clearInterval(timer);
      if (!s) return;
      if(requested && s.options.includes(requested)) s.value=requested;
      updateLinks(s.value);
      s.properties.value.change.connect(()=>updateLinks(s.value));
    },100);
  }
  setup().catch(()=>{const message=document.createElement("span");message.textContent="Asset navigation unavailable";nav.append(message);});
})();
