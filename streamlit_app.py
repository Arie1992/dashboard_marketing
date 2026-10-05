from __future__ import annotations
from io import BytesIO
from pathlib import Path
import json,re
import pandas as pd
import requests
import streamlit as st
import streamlit.components.v1 as components

BASE=Path(__file__).parent
OLD_TEMPLATE=BASE/"dashboard_template.html"
SHEET_ID="1K08X5qX9fY4dLBCn7lsOET1pMe8d25wz9iGF0ssYrE0"
GID="771277575"
OLD_URL=f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/export?format=csv&gid={GID}"
SHAREPOINT_URL="https://dikichi-my.sharepoint.com/:x:/p/faiz_hadiyanul/IQBhaRp7aZ9kQqxBMD8CGalqAb9P84syKxrZ2xBJn4lP-Ns?rtime=VtMH9YAi30g"

st.set_page_config(page_title="Kichi-Kichi · Market Insight",page_icon="🍗",layout="wide",initial_sidebar_state="collapsed")
st.markdown("""<style>
#MainMenu,header,footer,[data-testid="stToolbar"],[data-testid="stDecoration"],section[data-testid="stSidebar"]{display:none!important}
.block-container{padding:0 0 35px!important;max-width:none!important}iframe{border:0!important}
.kkhero{background:#0c3544;color:white;padding:24px max(24px,calc((100vw - 1420px)/2)) 18px}.kkhero small{color:#a8ced1;font-weight:800;letter-spacing:1.4px}.kkhero h1{margin:5px 0 2px}.kkhero p{color:#c3d4d8;margin:0}
.kkbody{max-width:1420px;margin:auto;padding:20px 24px}.kksection{font-weight:800;font-size:15px;margin:8px 0 12px}.kkcard{background:white;border:1px solid #dce3e1;border-radius:11px;padding:14px 16px;box-shadow:0 7px 22px rgba(20,44,51,.06)}
[data-testid="stMetric"]{background:white;border:1px solid #dce3e1;border-top:3px solid #2e93a1;border-radius:11px;padding:14px 16px}
</style>""",unsafe_allow_html=True)

def nh(x):return re.sub(r"\s+"," ",str(x or "").replace("\xa0"," ").strip()).lower()
def fc(cols,*terms):
    terms=[nh(t) for t in terms]
    return next((c for c in cols if all(t in nh(c) for t in terms)),None)

@st.cache_data(ttl=60)
def old_data():
    r=requests.get(OLD_URL,timeout=25);r.raise_for_status();raw=pd.read_csv(BytesIO(r.content),dtype=str)
    cols=list(raw.columns);ts=fc(cols,"timestamp");menu=fc(cols,"menu yang dipesan")
    sats=[c for c in cols if nh(c).split(".")[0]==nh("Apakah Anda puas dengan menu tersebut?")]
    out=pd.DataFrame({"Timestamp":pd.to_datetime(raw[ts],errors="coerce",dayfirst=True),"Menu":raw[menu]})
    aliases={"ayam geprek kichi-kichi":"Ayam Geprek Kichi-Kichi","ayam geprek kichi kichi":"Ayam Geprek Kichi-Kichi","crispy ori":"Crispy Ori","crispy original":"Crispy Ori"}
    out["Menu"]=out["Menu"].map(lambda x:aliases.get(str(x).strip().casefold(),str(x).strip()))
    out["Overall"]=raw[sats].apply(lambda x:pd.to_numeric(x,errors="coerce")).bfill(axis=1).iloc[:,0]
    for a in ["Rasa","Crispy","Juicy","Ukuran"]:
        c=next((c for c in cols if nh(c).split(".")[0]==nh(a)),None);out[a]=pd.to_numeric(raw[c],errors="coerce") if c else float("nan")
    return out.dropna(subset=["Timestamp","Menu"]).query("Menu in ['Ayam Geprek Kichi-Kichi','Crispy Ori']").sort_values("Timestamp").reset_index(drop=True)

def old_html(data):
    t=OLD_TEMPLATE.read_text(encoding="utf-8");menus=["Ayam Geprek Kichi-Kichi","Crispy Ori"]
    origin=data.Timestamp.iloc[0].strftime("%Y-%m-%dT%H:%M:%S");prev=data.Timestamp.iloc[0];enc=[]
    for _,r in data.iterrows():
        cur=r.Timestamp;d=max(0,round((cur-prev).total_seconds()));prev=cur
        vals=[r.Overall,r.Rasa,r.Crispy,r.Juicy,r.Ukuran];payload=str(menus.index(r.Menu))+"".join(str(int(v)) if pd.notna(v) else "0" for v in vals);enc.append(f"{d}:{payload}")
    mn=data.Timestamp.min().strftime("%Y-%m-%d");mx=data.Timestamp.max().strftime("%Y-%m-%d")
    t=t.replace("const MENU_NAMES=['Ayam Geprek Kichi-Kichi','Crispy Ori'];",f"const MENU_NAMES={json.dumps(menus)};",1)
    t=t.replace("const ORIGIN=new Date('2026-10-02T14:48:20');",f"const ORIGIN=new Date('{origin}');",1)
    t=re.sub(r"const ENCODED='[^']*';",f"const ENCODED='{';'.join(enc)}';",t,count=1)
    t=re.sub(r'min="2026-10-02" max="2026-10-03" value="2026-10-02"',f'min="{mn}" max="{mx}" value="{mn}"',t,count=1)
    t=re.sub(r'min="2026-10-02" max="2026-10-03" value="2026-10-03"',f'min="{mn}" max="{mx}" value="{mx}"',t,count=1)
    return t.replace("__MIN_DATE__",mn).replace("__MAX_DATE__",mx).replace("Menampilkan ${n} dari 132 respons","Menampilkan ${n} dari "+str(len(data))+" respons")

def read_blob(b):
    try:return pd.read_excel(BytesIO(b),dtype=str)
    except Exception:
        for e in ["utf-8-sig","cp1252","latin1"]:
            try:return pd.read_csv(BytesIO(b),dtype=str,encoding=e)
            except:pass
    raise ValueError("Format file tidak terbaca")

@st.cache_data(ttl=60)
def geprek_raw():
    # LIVE ONLY: no CSV/local fallback. Public SharePoint file must be downloadable anonymously.
    candidates=[
        SHAREPOINT_URL + ("&" if "?" in SHAREPOINT_URL else "?") + "download=1",
        SHAREPOINT_URL.replace("?", "?download=1&", 1),
    ]
    errors=[]
    for u in candidates:
        try:
            r=requests.get(u,timeout=30,allow_redirects=True,headers={"User-Agent":"Mozilla/5.0"})
            r.raise_for_status()
            ctype=r.headers.get("content-type","").lower()
            head=r.content[:300].lstrip().lower()
            if "text/html" in ctype or head.startswith(b"<!doctype") or head.startswith(b"<html"):
                errors.append("SharePoint returned an HTML viewer page, not the Excel file")
                continue
            return read_blob(r.content),"SharePoint live"
        except Exception as e:
            errors.append(str(e))
    raise RuntimeError("File SharePoint tidak dapat di-download langsung secara anonymous. Pastikan sharing = Anyone with the link dan file dapat di-download. Detail: " + " | ".join(errors[-2:]))

def geprek():
    raw,source=geprek_raw();cols=list(raw.columns)
    tm=fc(cols,"completion time") or fc(cols,"start time")
    mp={"Ayam":fc(cols,"rasa ayam"),"Sambal":fc(cols,"rasa sambel"),"Kol Goreng":fc(cols,"rasa kol goreng"),"Tahu":fc(cols,"rasa tahu"),"Tempe":fc(cols,"rasa tempe"),"Bayam Crispy":fc(cols,"rasa bayam crispy"),"Overall Rasa":fc(cols,"overall rasa"),"Overall Plating":fc(cols,"overall plating"),"Rasa vs Harga":fc(cols,"rasa vs harga"),"Porsi vs Harga":fc(cols,"porsi vs harga")}
    comment=fc(cols,"kritik","saran")
    df=pd.DataFrame({"Timestamp":pd.to_datetime(raw[tm],errors="coerce")})
    for k,c in mp.items():df[k]=pd.to_numeric(raw[c],errors="coerce") if c else float("nan")
    df["Review"]=raw[comment].fillna("").astype(str).str.strip() if comment else ""
    return df.dropna(subset=["Timestamp"]).sort_values("Timestamp"),source


REFERENCE_TEMPLATE=(BASE/"market_insight_reference.html").read_text(encoding="utf-8")
try: _view=st.query_params.get("view","geprek")
except Exception: _view="geprek"
st.session_state.view="all" if _view=="all" else "geprek"

def geprek_reference_html(df,source_label):
    html=REFERENCE_TEMPLATE
    attrs=["Ayam","Sambal","Kol Goreng","Tahu","Tempe","Bayam Crispy"]
    aspects=["Overall Rasa","Overall Plating","Rasa vs Harga","Porsi vs Harga"]
    data=[]
    for _,r in df.iterrows():
        row={"Timestamp":r["Timestamp"].isoformat(),"Review":str(r.get("Review","") or "")}
        for c in attrs+aspects:
            v=r.get(c); row[c]=None if pd.isna(v) else float(v)
        data.append(row)

    html=html.replace('<button class="active" data-page="overview">▣ Ayam Geprek</button>',
                      '<button class="active" onclick="location.href=\\'?view=geprek\\'">▣ Ayam Geprek</button>',1)
    html=html.replace('<button data-page="legacy">▣ Menu Existing / Lama</button>',
                      '<button onclick="location.href=\\'?view=all\\'">▣ Menu Existing / Lama</button>',1)
    html=re.sub(r'<label class="field"><span>Outlet</span><select>.*?</select></label>','',html,count=1,flags=re.S)

    a=html.find("<script>"); b=html.rfind("</script>")
    js = '''<script>
const DATA=__DATA__;
const ATTRS=["Ayam","Sambal","Kol Goreng","Tahu","Tempe","Bayam Crispy"];
const ASPECTS=["Overall Rasa","Overall Plating","Rasa vs Harga","Porsi vs Harga"];
const $=x=>document.getElementById(x), day=x=>x.Timestamp.slice(0,10);
const mean=(a,k)=>{const v=a.map(x=>x[k]).filter(Number.isFinite);return v.length?v.reduce((p,q)=>p+q,0)/v.length:null};
const fmt=v=>Number.isFinite(v)?v.toLocaleString("id-ID",{minimumFractionDigits:2,maximumFractionDigits:2}):"—";
const esc=s=>String(s||"").replace(/[&<>"]/g,c=>({"&":"&amp;","<":"&lt;",">":"&gt;","\\"":"&quot;"}[c]));
let D=DATA; const dates=DATA.map(day).sort();
if(dates.length){$("from").value=dates[0];$("to").value=dates[dates.length-1]}
function productHtml(){return ATTRS.map(k=>{const v=mean(D,k);return `<div class="product"><strong>${k}</strong><div class="score">${fmt(v)}</div><div class="stars">★★★★★</div><div class="track"><div class="fill" style="width:${(v||0)/5*100}%"></div></div></div>`}).join("")}
function render(){
 const f=$("from").value,t=$("to").value;D=DATA.filter(x=>(!f||day(x)>=f)&&(!t||day(x)<=t));
 const vals=document.querySelectorAll("#overview .stat .value");
 if(vals.length>=5){vals[0].textContent=D.length.toLocaleString("id-ID");vals[1].textContent=fmt(mean(D,"Overall Rasa"));vals[2].textContent=fmt(mean(D,"Overall Plating"));vals[3].textContent=fmt(mean(D,"Rasa vs Harga"));vals[4].textContent=fmt(mean(D,"Porsi vs Harga"))}
 $("products").innerHTML=productHtml();$("products2").innerHTML=productHtml();
 const cs=[1,2,3,4,5].map(v=>D.filter(x=>x["Overall Rasa"]===v).length),mx=Math.max(1,...cs);
 $("bars").innerHTML=cs.map((n,i)=>`<div class="barcol"><b>${n}</b><div class="bar" style="height:${Math.max(2,n/mx*155)}px"></div>${i+1}</div>`).join("");
 const low=[];D.forEach(x=>ASPECTS.forEach(k=>{if(Number.isFinite(x[k])&&x[k]<=3&&x.Review)low.push({x,k})}));
 const fb=low.length?low.slice(0,20).map(({x,k})=>`<div class="comment"><span><b style="color:#b65346">${k} · ${x[k]}/5</b><br>“${esc(x.Review)}”</span><span style="white-space:nowrap;color:#879598">${new Date(x.Timestamp).toLocaleDateString("id-ID")}</span></div>`).join(""):`<div class="comment"><span>Tidak ada komentar dengan rating ≤3 pada periode ini.</span></div>`;
 $("feedbackMini").innerHTML=fb;$("feedbackAll").innerHTML=fb;
 $("rows").innerHTML=[...D].reverse().map(x=>`<tr><td>${new Date(x.Timestamp).toLocaleDateString("id-ID")}</td><td>—</td><td>${x.Ayam??"—"}</td><td>${x.Sambal??"—"}</td><td>${x["Overall Rasa"]??"—"}</td><td>${x["Overall Plating"]??"—"}</td><td>${esc(x.Review)}</td></tr>`).join("");
}
const side=$("sidebar"),shell=document.querySelector(".shell");const setSidebar=hidden=>{side.classList.toggle("hide",hidden);shell.classList.toggle("sidebar-collapsed",hidden);try{localStorage.setItem("kk_hide",hidden?"1":"0")}catch(e){}};
$("hidebtn").onclick=()=>setSidebar(true);$("menutoggle").onclick=()=>setSidebar(!side.classList.contains("hide"));try{if(localStorage.getItem("kk_hide")==="1")setSidebar(true)}catch(e){}
document.querySelectorAll(".nav button[data-page]").forEach(b=>b.onclick=()=>{document.querySelectorAll(".nav button").forEach(x=>x.classList.remove("active"));b.classList.add("active");document.querySelectorAll(".section").forEach(x=>x.classList.remove("active"));const p=$(b.dataset.page);if(p)p.classList.add("active");if(innerWidth<700)setSidebar(true)});
$("filters").onsubmit=e=>{e.preventDefault();render()};render();
</script>'''.replace("__DATA__",json.dumps(data,ensure_ascii=False))
    html=html[:a]+js+html[b+9:]
    html=html.replace("Prototype dashboard dengan data dummy. Nantinya satu link dapat berisi beberapa sub-dashboard.","Dashboard live dari SharePoint · cache data 60 detik.")
    html=html.replace("</main>",f'<div style="text-align:center;font-size:10px;color:#879598;margin:14px">Source: {source_label} · cache 60 detik</div></main>')
    return html

if st.session_state.view=="all":
    components.html(old_html(old_data()),height=2200,scrolling=True)
else:
    try:
        df,source=geprek()
        components.html(geprek_reference_html(df,source),height=2600,scrolling=True)
    except Exception as e:
        st.error(f"Dashboard Ayam Geprek gagal membaca SharePoint live: {e}")
