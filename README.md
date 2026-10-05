# Kichi-Kichi Market Insight — Direct SharePoint

Satu URL Streamlit:
- ALL MENU: source dashboard lama
- AYAM GEPREK: **langsung dari SharePoint public**

Tidak ada CSV fallback. Jika SharePoint tidak dapat di-download anonymous, dashboard akan menampilkan error agar tidak diam-diam memakai data lama.

Run:
```bash
pip install -r requirements.txt
streamlit run streamlit_app.py
```

Cache source: 60 detik.
