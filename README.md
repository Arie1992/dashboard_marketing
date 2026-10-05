# Market Insight Dashboard — reviewed baseline

- Satu URL: `?view=all` dan `?view=geprek`
- Sidebar hanya **ALL** dan **Ayam Geprek**
- Sidebar dapat di-hide; tombol ☰ muncul saat sidebar hidden
- ALL mempertahankan dashboard lama
- Geprek: UI V6 report yang dikunci (4 KPI, atribut, tren, review rating rendah, distribusi, detail)
- Tidak ada filter Outlet pada Geprek
- Source Geprek hanya direct SharePoint link yang diberikan user
- Cache data 60 detik
- Tidak ada dummy/local/CSV fallback untuk Geprek
- Jika SharePoint tidak menghasilkan workbook valid, tampilkan error source
