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

# ONE LINK / TWO VIEWS
a,b=st.columns(2)
if "view" not in st.session_state:st.session_state.view="all"
with a:
    if st.button("ALL MENU · Dashboard Lama",use_container_width=True,type="primary" if st.session_state.view=="all" else "secondary"):st.session_state.view="all";st.rerun()
with b:
    if st.button("AYAM GEPREK · Market Insight",use_container_width=True,type="primary" if st.session_state.view=="geprek" else "secondary"):st.session_state.view="geprek";st.rerun()

if st.session_state.view=="all":
    components.html(old_html(old_data()),height=2200,scrolling=True)
else:
    df,source=geprek()
    st.markdown('<div class="kkhero"><small>MARKET INSIGHT · CUSTOMER SURVEY</small><h1>Ayam Geprek Kichi-Kichi</h1><p>Product quality, value for money, dan review pelanggan.</p></div>',unsafe_allow_html=True)
    st.markdown('<div class="kkbody">',unsafe_allow_html=True)
    d1,d2=st.columns(2)
    lo,hi=df.Timestamp.min().date(),df.Timestamp.max().date()
    with d1: start=st.date_input("Periode dari",lo,min_value=lo,max_value=hi)
    with d2: end=st.date_input("Sampai",hi,min_value=lo,max_value=hi)
    f=df[(df.Timestamp.dt.date>=start)&(df.Timestamp.dt.date<=end)].copy()
    st.markdown('<div class="kksection">RINGKASAN OVERALL</div>',unsafe_allow_html=True)
    q1,q2,q3,q4=st.columns(4)
    q1.metric("TOTAL RESPONDEN",len(f));q2.metric("OVERALL RASA",f["Overall Rasa"].mean().round(2))
    q3.metric("OVERALL PLATING",f["Overall Plating"].mean().round(2));q4.metric("QUALITY VS HARGA",f[["Rasa vs Harga","Porsi vs Harga"]].stack().mean().round(2))
    st.markdown('<div class="kksection">RATA-RATA NILAI ATRIBUT</div>',unsafe_allow_html=True)
    attrs=["Ayam","Sambal","Kol Goreng","Tahu","Tempe","Bayam Crispy"]
    st.bar_chart(f[attrs].mean(),horizontal=True)
    st.markdown('<div class="kksection">RATING RENDAH PER ASPEK</div>',unsafe_allow_html=True)
    aspects=["Overall Rasa","Overall Plating","Rasa vs Harga","Porsi vs Harga"]
    low=pd.DataFrame({"Aspek":aspects,"Rata-rata":[f[x].mean() for x in aspects],"Rating ≤ 3":[((f[x]<=3)&f[x].notna()).sum() for x in aspects]})
    low["% Rendah"]=(low["Rating ≤ 3"]/max(1,len(f))*100).round(1)
    st.dataframe(low,use_container_width=True,hide_index=True)
    st.markdown('<div class="kksection">RATING RENDAH & REVIEW TERKAIT</div>',unsafe_allow_html=True)
    c1,c2=st.columns([2,1])
    with c1: aspect=st.selectbox("Aspek penilaian",aspects)
    with c2: limit=st.selectbox("Batas rating",[3,2,1],format_func=lambda x:f"≤ {x}")
    reviews=f[(f[aspect]<=limit)&f[aspect].notna()&f.Review.ne("")][["Timestamp",aspect,"Review"]].sort_values("Timestamp",ascending=False)
    st.dataframe(reviews,use_container_width=True,hide_index=True)
    st.markdown('<div class="kksection">SEMUA DATA SURVEI</div>',unsafe_allow_html=True)
    detail=["Timestamp"]+attrs+aspects+["Review"]
    st.dataframe(f[detail].sort_values("Timestamp",ascending=False),use_container_width=True,hide_index=True,height=520)
    st.caption(f"Source: {source} · cache refresh ±60 detik")
    st.markdown('</div>',unsafe_allow_html=True)
