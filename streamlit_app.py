from __future__ import annotations
from io import BytesIO
from pathlib import Path
import html as htmlmod, json, re
import pandas as pd
import requests
import streamlit as st
import streamlit.components.v1 as components

BASE=Path(__file__).parent
OLD_TEMPLATE=BASE/'dashboard_template.html'
SHEET_ID='1K08X5qX9fY4dLBCn7lsOET1pMe8d25wz9iGF0ssYrE0'; GID='771277575'
OLD_URL=f'https://docs.google.com/spreadsheets/d/{SHEET_ID}/export?format=csv&gid={GID}'
SHAREPOINT_URL='https://dikichi-my.sharepoint.com/:x:/p/faiz_hadiyanul/IQBhaRp7aZ9kQqxBMD8CGalqAb9P84syKxrZ2xBJn4lP-Ns?e=44Bo7u'

st.set_page_config(page_title='Kichi-Kichi · Market Insight',page_icon='🍗',layout='wide',initial_sidebar_state='collapsed')
st.markdown('''<style>#MainMenu,header,footer,[data-testid="stToolbar"],[data-testid="stDecoration"],section[data-testid="stSidebar"]{display:none!important}.block-container{padding:0!important;max-width:none!important}iframe{border:0!important}</style>''',unsafe_allow_html=True)

def nh(x): return re.sub(r'\s+',' ',str(x or '').replace('\xa0',' ').strip()).lower()
def fc(cols,*terms):
    terms=[nh(t) for t in terms]
    return next((c for c in cols if all(t in nh(c) for t in terms)),None)
def first_col(cols, variants):
    for terms in variants:
        c=fc(cols,*terms)
        if c:return c
    return None

@st.cache_data(ttl=60)
def old_data():
    r=requests.get(OLD_URL,timeout=25); r.raise_for_status(); raw=pd.read_csv(BytesIO(r.content),dtype=str)
    cols=list(raw.columns); ts=fc(cols,'timestamp'); menu=fc(cols,'menu yang dipesan')
    sats=[c for c in cols if nh(c).split('.')[0]==nh('Apakah Anda puas dengan menu tersebut?')]
    if not ts or not menu or not sats: raise RuntimeError('Kolom dashboard ALL tidak lengkap.')
    out=pd.DataFrame({'Timestamp':pd.to_datetime(raw[ts],errors='coerce',dayfirst=True),'Menu':raw[menu]})
    aliases={'ayam geprek kichi-kichi':'Ayam Geprek Kichi-Kichi','ayam geprek kichi kichi':'Ayam Geprek Kichi-Kichi','crispy ori':'Crispy Ori','crispy original':'Crispy Ori'}
    out['Menu']=out['Menu'].map(lambda x:aliases.get(str(x).strip().casefold(),str(x).strip()))
    out['Overall']=raw[sats].apply(lambda x:pd.to_numeric(x,errors='coerce')).bfill(axis=1).iloc[:,0]
    for a in ['Rasa','Crispy','Juicy','Ukuran']:
        c=next((c for c in cols if nh(c).split('.')[0]==nh(a)),None); out[a]=pd.to_numeric(raw[c],errors='coerce') if c else float('nan')
    return out.dropna(subset=['Timestamp','Menu']).query("Menu in ['Ayam Geprek Kichi-Kichi','Crispy Ori']").sort_values('Timestamp').reset_index(drop=True)

def sidebar_css(): return '''<style>
:root{--side:260px;--navy:#0d3d4d;--teal:#2f98a5;--paper:#f1f0ea;--line:#d8e0df;--ink:#253941;--muted:#77888c}
*{box-sizing:border-box}body{margin:0;background:var(--paper);color:var(--ink);font:14px Inter,system-ui,"Segoe UI",sans-serif}.shell{display:grid;grid-template-columns:var(--side) minmax(0,1fr);min-height:100vh;transition:grid-template-columns .2s}.shell.sidebar-collapsed{grid-template-columns:0 minmax(0,1fr)}
.sidebar{position:sticky;top:0;height:100vh;background:#fff;border-right:1px solid var(--line);padding:28px 14px 18px;overflow:hidden;transition:padding .2s,border .2s}.sidebar.hide{padding:0;border:0}.side-title{font-size:12px;font-weight:900;letter-spacing:1.2px;color:#95a3a6;margin:8px 12px 14px}.side-link{display:block;text-decoration:none;color:#42565e;padding:14px 16px;border-radius:10px;margin:5px 0;font-size:16px}.side-link.active{background:#e8f2f1;color:#073a4b;font-weight:800}.hidebtn{position:absolute;bottom:18px;left:14px;right:14px;border:1px solid var(--line);background:#fff;border-radius:9px;padding:10px;cursor:pointer;color:#52666d}.menutoggle{position:fixed;left:14px;top:14px;z-index:99;width:44px;height:44px;border:1px solid var(--line);border-radius:9px;background:#fff;color:var(--navy);font-size:24px;box-shadow:0 4px 14px #0d3d4d22;cursor:pointer}.content{min-width:0}.sidebar:not(.hide)~.content .menutoggle{display:none}@media(max-width:760px){.shell{grid-template-columns:0 minmax(0,1fr)}.sidebar{position:fixed;z-index:100;width:260px;transform:translateX(-100%)}.sidebar:not(.hide){transform:translateX(0);padding:28px 14px 18px}.sidebar:not(.hide)~.content .menutoggle{display:block}}
</style>'''
def sidebar(active):
    return f'''<aside id="sidebar" class="sidebar"><div class="side-title">MARKET INSIGHT</div><a class="side-link {'active' if active=='all' else ''}" target="_top" href="?view=all">▣ ALL</a><a class="side-link {'active' if active=='geprek' else ''}" target="_top" href="?view=geprek">▣ Ayam Geprek</a><button id="hidebtn" class="hidebtn">‹ Hide Menu</button></aside>'''
def side_js(): return '''<script>const sb=document.getElementById('sidebar'),sh=document.querySelector('.shell');function setSide(h){sb.classList.toggle('hide',h);sh.classList.toggle('sidebar-collapsed',h);try{localStorage.setItem('kk_hide',h?'1':'0')}catch(e){}}document.getElementById('hidebtn').onclick=()=>setSide(true);document.getElementById('menutoggle').onclick=()=>setSide(!sb.classList.contains('hide'));try{if(localStorage.getItem('kk_hide')==='1')setSide(true)}catch(e){}</script>'''

def old_html(data):
    t=OLD_TEMPLATE.read_text(encoding='utf-8'); menus=['Ayam Geprek Kichi-Kichi','Crispy Ori']; origin=data.Timestamp.iloc[0].strftime('%Y-%m-%dT%H:%M:%S'); prev=data.Timestamp.iloc[0]; enc=[]
    for _,r in data.iterrows():
        cur=r.Timestamp; d=max(0,round((cur-prev).total_seconds())); prev=cur; vals=[r.Overall,r.Rasa,r.Crispy,r.Juicy,r.Ukuran]; payload=str(menus.index(r.Menu))+''.join(str(int(v)) if pd.notna(v) else '0' for v in vals); enc.append(f'{d}:{payload}')
    mn=data.Timestamp.min().strftime('%Y-%m-%d'); mx=data.Timestamp.max().strftime('%Y-%m-%d')
    t=t.replace("const MENU_NAMES=['Ayam Geprek Kichi-Kichi','Crispy Ori'];",f'const MENU_NAMES={json.dumps(menus)};',1).replace("const ORIGIN=new Date('2026-10-02T14:48:20');",f"const ORIGIN=new Date('{origin}');",1)
    t=re.sub(r"const ENCODED='[^']*';",f"const ENCODED='{';'.join(enc)}';",t,count=1)
    t=re.sub(r'min="2026-10-02" max="2026-10-03" value="2026-10-02"',f'min="{mn}" max="{mx}" value="{mn}"',t,count=1); t=re.sub(r'min="2026-10-02" max="2026-10-03" value="2026-10-03"',f'min="{mn}" max="{mx}" value="{mx}"',t,count=1)
    t=t.replace('__MIN_DATE__',mn).replace('__MAX_DATE__',mx).replace('Menampilkan ${n} dari 132 respons','Menampilkan ${n} dari '+str(len(data))+' respons')
    body=re.search(r'<body>(.*)</body>',t,re.S).group(1); head=re.search(r'<head>(.*)</head>',t,re.S).group(1)
    return '<!doctype html><html><head>'+head+sidebar_css()+'</head><body><div class="shell">'+sidebar('all')+'<div class="content"><button id="menutoggle" class="menutoggle">☰</button>'+body+'</div></div>'+side_js()+'</body></html>'

def read_blob(b):
    if b[:2]==b'PK': return pd.read_excel(BytesIO(b),dtype=str)
    try:return pd.read_excel(BytesIO(b),dtype=str)
    except Exception:
        for e in ['utf-8-sig','cp1252','latin1']:
            try:return pd.read_csv(BytesIO(b),dtype=str,encoding=e)
            except Exception: pass
    raise ValueError('Respons bukan file Excel/CSV yang valid.')

@st.cache_data(ttl=60)
def geprek_raw():
    # Exact public share link supplied by user. No dummy/local fallback.
    base=SHAREPOINT_URL
    candidates=[base+'&download=1',base.replace('?e=44Bo7u','?download=1&e=44Bo7u'),base+'&web=0']
    errs=[]
    for u in candidates:
        try:
            r=requests.get(u,timeout=35,allow_redirects=True,headers={'User-Agent':'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/142 Safari/537.36','Accept':'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet,application/octet-stream,*/*'})
            r.raise_for_status(); ctype=r.headers.get('content-type','').lower(); head=r.content[:500].lstrip().lower()
            if 'text/html' in ctype or head.startswith(b'<!doctype') or head.startswith(b'<html'):
                errs.append('SharePoint mengembalikan halaman viewer HTML, bukan workbook'); continue
            df=read_blob(r.content)
            if df.empty: errs.append('Workbook terbaca tetapi kosong'); continue
            return df,'SharePoint live'
        except Exception as e: errs.append(f'{type(e).__name__}: {e}')
    raise RuntimeError('Direct SharePoint belum menghasilkan workbook yang bisa dibaca. '+ ' | '.join(errs[-3:]))

def geprek_data():
    raw,src=geprek_raw(); cols=list(raw.columns)
    tm=first_col(cols,[("completion time",),("start time",),("timestamp",),("waktu",)])
    mapping={
      'Ayam':[("rasa ayam",),("ayam",)],'Sambal':[("rasa sambel",),("rasa sambal",),("sambal",)],'Kol Goreng':[("rasa kol goreng",),("kol goreng",)],'Tahu':[("rasa tahu",),("tahu",)],'Tempe':[("rasa tempe",),("tempe",)],'Bayam Crispy':[("rasa bayam crispy",),("bayam crispy",)],
      'Overall Rasa':[("overall rasa",)],'Overall Plating':[("overall plating",),("tampilan product",),("tampilan produk",)],'Rasa vs Harga':[("rasa vs harga",)],'Porsi vs Harga':[("porsi vs harga",)]}
    found={k:first_col(cols,v) for k,v in mapping.items()}; comment=first_col(cols,[("kritik","saran"),("review",),("saran",),("comment",)])
    if not tm: raise RuntimeError('Kolom tanggal/waktu tidak ditemukan. Kolom tersedia: '+', '.join(map(str,cols[:12])))
    essential=['Overall Rasa','Overall Plating','Rasa vs Harga','Porsi vs Harga']
    missing=[k for k in essential if not found[k]]
    if missing: raise RuntimeError('Mapping kolom belum cocok untuk: '+', '.join(missing)+'. Kolom workbook: '+ ' | '.join(map(str,cols)))
    df=pd.DataFrame({'Timestamp':pd.to_datetime(raw[tm],errors='coerce',dayfirst=True)})
    for k,c in found.items(): df[k]=pd.to_numeric(raw[c],errors='coerce') if c else float('nan')
    df['Review']=raw[comment].fillna('').astype(str).str.strip() if comment else ''
    df=df.dropna(subset=['Timestamp']).sort_values('Timestamp').reset_index(drop=True)
    if df.empty: raise RuntimeError('Tidak ada timestamp valid setelah workbook dibaca.')
    return df,src

def geprek_html(df,src):
    cols=['Ayam','Sambal','Kol Goreng','Tahu','Tempe','Bayam Crispy','Overall Rasa','Overall Plating','Rasa vs Harga','Porsi vs Harga']
    data=[]
    for _,r in df.iterrows():
        o={'Timestamp':r.Timestamp.isoformat(),'Review':str(r.Review or '')}
        for c in cols:o[c]=None if pd.isna(r[c]) else float(r[c])
        data.append(o)
    payload=json.dumps(data,ensure_ascii=False).replace('</','<\\/')
    css='''<style>:root{--navy:#0d3d4d;--teal:#2f98a5;--paper:#f1f0ea;--line:#d8e0df;--ink:#253941;--muted:#77888c;--green:#27765f;--gold:#e7aa45;--red:#dc6654}*{box-sizing:border-box}.hero{background:var(--navy);color:#fff;padding:28px 34px 0}.eyebrow{font-size:12px;font-weight:900;letter-spacing:1.4px;color:#a8d2d5}.hero h1{font-size:30px;margin:7px 0 4px}.hero p{font-size:15px;color:#c7d6d9;margin:0 0 20px}.filters{background:#fff;color:var(--ink);padding:16px 18px;border-radius:12px 12px 0 0;display:flex;gap:12px;align-items:end;flex-wrap:wrap}.field{display:grid;gap:5px}.field b{font-size:11px;color:#6f8085}.field input,.field select{border:1px solid #d5dfde;border-radius:9px;padding:11px 13px;font-size:14px;background:#fff}.btn{border:0;border-radius:9px;background:var(--navy);color:#fff;padding:12px 20px;font-weight:800;font-size:14px}main{padding:24px 30px 45px;max-width:1800px;margin:auto}.summary-title{display:flex;justify-content:space-between;align-items:center}.summary-title h2{font-size:16px}.summary-title span{color:var(--muted);font-size:12px}.stats{display:grid;grid-template-columns:repeat(4,1fr);gap:14px;margin:12px 0 16px}.card{background:#fff;border:1px solid var(--line);border-radius:12px;box-shadow:0 8px 24px #1938410b}.stat{padding:20px;border-top:3px solid var(--teal)}.stat:nth-child(2){border-top-color:var(--gold)}.stat:nth-child(3){border-top-color:#4ba67d}.stat:nth-child(4){border-top-color:var(--red)}.label{font-size:11px;font-weight:850;color:#687a80}.value{font-size:31px;font-weight:900;color:#073b4c;margin:10px 0 3px}.sub{font-size:11px;color:#819095}.grid{display:grid;grid-template-columns:1.15fr .95fr;gap:14px;margin-bottom:14px}.head{padding:16px 18px 0}.head h3{font-size:15px;margin:0}.head p{font-size:11px;color:var(--muted);margin:5px 0 0}.body{padding:15px 18px 18px}.attrs{display:grid;grid-template-columns:repeat(3,1fr);gap:9px}.attr{border:1px solid #e1e7e6;border-radius:9px;padding:12px}.attrname{font-size:11px;font-weight:800}.score{font-size:22px;font-weight:900;color:#176a78;margin:6px 0}.track{height:5px;background:#edf1f0;border-radius:10px}.fill{height:100%;background:var(--teal);border-radius:10px}.trend{height:210px;display:flex;align-items:flex-end;gap:26px;padding:15px 10px 0;border-bottom:1px solid var(--line)}.tcol{flex:1;text-align:center;color:#687b80;font-size:11px}.tcol b{display:block;margin-bottom:6px}.bar{width:48px;max-width:70%;margin:auto;background:linear-gradient(#3299a5,#0d4b5b);border-radius:6px 6px 0 0}.reviewfilters{display:flex;gap:10px;flex-wrap:wrap;margin-bottom:12px}.comment{display:flex;justify-content:space-between;gap:15px;border:1px solid #e2e8e7;border-radius:9px;padding:11px;margin:8px 0;font-size:12px}.tablewrap{overflow:auto;max-height:520px}.table{border-collapse:collapse;width:100%;min-width:1250px}.table th,.table td{padding:10px 11px;border-bottom:1px solid #e8eceb;text-align:left;font-size:11px}.table th{position:sticky;top:0;background:#f4f6f5;color:#708187}.source{font-size:10px;color:#89979a;text-align:right;padding:0 30px 14px}@media(max-width:1000px){.stats{grid-template-columns:repeat(2,1fr)}.grid{grid-template-columns:1fr}.attrs{grid-template-columns:repeat(2,1fr)}}@media(max-width:600px){main,.hero{padding-left:12px;padding-right:12px}.stats,.attrs{grid-template-columns:1fr}}</style>'''
    body='''<header class="hero"><div class="eyebrow">MARKET INSIGHT · CUSTOMER SURVEY</div><h1>Ayam Geprek Kichi-Kichi</h1><p>Ringkasan penilaian produk dan detail respons pelanggan.</p><form class="filters" id="filters"><label class="field"><b>PERIODE DARI</b><input id="from" type="date"></label><label class="field"><b>SAMPAI</b><input id="to" type="date"></label><button class="btn">Terapkan</button></form></header><main><div class="summary-title"><h2>RINGKASAN OVERALL</h2><span>Skala rating 1–5</span></div><div class="stats"><div class="card stat"><div class="label">TOTAL RESPONDEN</div><div id="total" class="value">—</div><div class="sub">Respons pada periode terpilih</div></div><div class="card stat"><div class="label">OVERALL RASA</div><div id="rasa" class="value">—</div><div class="sub">Product Quality · rasa</div></div><div class="card stat"><div class="label">OVERALL PLATING</div><div id="plating" class="value">—</div><div class="sub">Product Quality · tampilan produk</div></div><div class="card stat"><div class="label">QUALITY VS HARGA</div><div id="harga" class="value">—</div><div class="sub">Rata-rata rasa & porsi vs harga</div></div></div><div class="grid"><div class="card"><div class="head"><h3>Rata-rata Nilai Atribut</h3><p>Rata-rata dari masing-masing kolom penilaian produk</p></div><div class="body"><div id="attrs" class="attrs"></div></div></div><div class="card"><div class="head"><h3>Tren Respons</h3><p>Jumlah respons per tanggal</p></div><div class="body"><div id="trend" class="trend"></div></div></div></div><div class="grid"><div class="card"><div class="head"><h3>Rating Rendah & Review Terkait</h3><p>Cek komentar responden berdasarkan aspek dan batas rating</p></div><div class="body"><div class="reviewfilters"><label class="field"><b>ASPEK PENILAIAN</b><select id="aspect"></select></label><label class="field"><b>BATAS RATING</b><select id="limit"><option value="3">≤ 3</option><option value="2">≤ 2</option><option value="1">≤ 1</option><option value="5">Semua Rating</option></select></label></div><div id="reviews"></div></div></div><div class="card"><div class="head"><h3>Distribusi Overall Rasa</h3><p>Jumlah respons untuk setiap nilai</p></div><div class="body"><div id="dist" class="trend"></div></div></div></div><div class="card"><div class="head"><h3>Semua Data Survei</h3><p>Detail respons terbaru — kolom penilaian komponen tetap ditampilkan</p></div><div class="body tablewrap"><table class="table"><thead><tr><th>Waktu</th><th>Ayam</th><th>Sambal</th><th>Kol Goreng</th><th>Tahu</th><th>Tempe</th><th>Bayam Crispy</th><th>Overall Rasa</th><th>Plating</th><th>Rasa vs Harga</th><th>Porsi vs Harga</th><th>Review / Saran</th></tr></thead><tbody id="rows"></tbody></table></div></div></main>'''
    js='''<script>const DATA=__DATA__,ATTR=['Ayam','Sambal','Kol Goreng','Tahu','Tempe','Bayam Crispy'],ASP=['Overall Rasa','Overall Plating','Rasa vs Harga','Porsi vs Harga'],$=x=>document.getElementById(x),day=x=>x.Timestamp.slice(0,10),esc=s=>String(s||'').replace(/[&<>\"]/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','\"':'&quot;'}[c])),mean=(a,k)=>{const v=a.map(x=>x[k]).filter(Number.isFinite);return v.length?v.reduce((p,q)=>p+q,0)/v.length:null},fmt=v=>Number.isFinite(v)?v.toLocaleString('id-ID',{minimumFractionDigits:2,maximumFractionDigits:2}):'—';let D=DATA;const ds=DATA.map(day).sort();if(ds.length){$('from').value=ds[0];$('to').value=ds[ds.length-1]}$('aspect').innerHTML='<option>Semua Aspek</option>'+ASP.map(x=>`<option>${x}</option>`).join('');function reviews(){const a=$('aspect').value,l=+$('limit').value,out=[];D.forEach(x=>(a==='Semua Aspek'?ASP:[a]).forEach(k=>{if(Number.isFinite(x[k])&&x[k]<=l&&x.Review)out.push([x,k])}));$('reviews').innerHTML=out.length?out.slice(0,50).map(([x,k])=>`<div class="comment"><span><b style="color:#b65346">${k} · ${x[k]}/5</b><br>“${esc(x.Review)}”</span><span>${new Date(x.Timestamp).toLocaleDateString('id-ID')}</span></div>`).join(''):'<div class="comment">Tidak ada komentar sesuai filter.</div>'}function render(){const f=$('from').value,t=$('to').value;D=DATA.filter(x=>(!f||day(x)>=f)&&(!t||day(x)<=t));$('total').textContent=D.length.toLocaleString('id-ID');$('rasa').textContent=fmt(mean(D,'Overall Rasa'));$('plating').textContent=fmt(mean(D,'Overall Plating'));const h=[mean(D,'Rasa vs Harga'),mean(D,'Porsi vs Harga')].filter(Number.isFinite);$('harga').textContent=fmt(h.length?h.reduce((a,b)=>a+b,0)/h.length:null);$('attrs').innerHTML=ATTR.map(k=>{const v=mean(D,k);return `<div class="attr"><div class="attrname">${k}</div><div class="score">${fmt(v)}</div><div class="track"><div class="fill" style="width:${(v||0)/5*100}%"></div></div></div>`}).join('');const cnt={};D.forEach(x=>cnt[day(x)]=(cnt[day(x)]||0)+1);const arr=Object.entries(cnt).sort(),mx=Math.max(1,...arr.map(x=>x[1]));$('trend').innerHTML=arr.map(([d,n])=>`<div class="tcol"><b>${n}</b><div class="bar" style="height:${Math.max(3,n/mx*150)}px"></div>${new Date(d+'T00:00:00').toLocaleDateString('id-ID',{day:'2-digit',month:'short'})}</div>`).join('');const cs=[1,2,3,4,5].map(v=>D.filter(x=>x['Overall Rasa']===v).length),dm=Math.max(1,...cs);$('dist').innerHTML=cs.map((n,i)=>`<div class="tcol"><b>${n}</b><div class="bar" style="height:${Math.max(3,n/dm*150)}px"></div>${i+1}</div>`).join('');$('rows').innerHTML=[...D].reverse().map(x=>`<tr><td>${new Date(x.Timestamp).toLocaleString('id-ID')}</td>${ATTR.map(k=>`<td>${x[k]??'—'}</td>`).join('')}<td>${x['Overall Rasa']??'—'}</td><td>${x['Overall Plating']??'—'}</td><td>${x['Rasa vs Harga']??'—'}</td><td>${x['Porsi vs Harga']??'—'}</td><td>${esc(x.Review)}</td></tr>`).join('');reviews()}$('filters').onsubmit=e=>{e.preventDefault();render()};$('aspect').onchange=reviews;$('limit').onchange=reviews;render();</script>'''.replace('__DATA__',payload)
    return '<!doctype html><html><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">'+sidebar_css()+css+'</head><body><div class="shell">'+sidebar('geprek')+'<div class="content"><button id="menutoggle" class="menutoggle">☰</button>'+body+f'<div class="source">Source: {htmlmod.escape(src)} · cache 60 detik</div></div></div>'+js+side_js()+'</body></html>'

view=st.query_params.get('view','geprek')
if view=='all':
    try: components.html(old_html(old_data()),height=2300,scrolling=True)
    except Exception as e: st.error(f'Dashboard ALL gagal dimuat: {e}')
else:
    try:
        df,src=geprek_data(); components.html(geprek_html(df,src),height=2800,scrolling=True)
    except Exception as e:
        st.error('Dashboard Ayam Geprek gagal membaca SharePoint live. Tidak ada dummy/fallback yang ditampilkan.')
        st.code(str(e))
        st.caption('Source dikunci ke link SharePoint yang diberikan. Cache 60 detik.')
