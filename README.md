# PyRep — Kurulum ve Kullanım

## Gerekli Kütüphaneler

Sadece **bir** kütüphane kurman gerekiyor, geri kalanı Python ile birlikte geliyor:

```bash
pip install PyQt6
```

## Dosya Yapısı

```
pyrep/
├── main.py            ← Buradan başlat
├── editor.py          ← Kod editörü + terminal
├── file_explorer.py   ← Sol panel dosya gezgini
└── package_manager.py ← Kütüphane yöneticisi
```

## Başlatma

```bash
python main.py
```

## Kısayollar

| Kısayol        | İşlem              |
|----------------|--------------------|
| Ctrl+Enter     | Kodu çalıştır      |
| Ctrl+S         | Kaydet             |
| Ctrl+O         | Dosya aç           |
| Ctrl+N         | Yeni dosya         |
| Tab            | 4 boşluk girinti   |

## Özellikler

### Kod Editörü
- Python syntax renklendirme
- Satır numaraları
- Otomatik girinti
- Tab = 4 boşluk

### Terminal
- Kodun çıktısı gerçek zamanlı gelir
- Hata mesajları kırmızı gösterilir
- Çalışan kodu durdurabilirsin

### Dosya Gezgini
- Klasör açma
- Yeni dosya/klasör oluşturma
- Sağ tık menüsü (aç, sil, yeniden adlandır)
- Çift tıkla dosyayı editörde aç

### Kütüphane Yöneticisi
- Toolbar'dan "📦 Kütüphaneler" butonuna bas
- Paket adı yaz → Kur
- Popüler kütüphanelere tek tıkla kur
- Kurulu listesini gör ve sil
- Arka planda çalışır, arayüz donmaz

## Kullanılan Python Modülleri

| Modül          | Kaynak              | Ne için?                    |
|----------------|---------------------|-----------------------------|
| PyQt6          | pip install PyQt6   | Arayüz (pencere, butonlar)  |
| subprocess     | Python dahili       | pip ve kod çalıştırma       |
| os             | Python dahili       | Dosya işlemleri             |
| sys            | Python dahili       | Python path, çıkış          |
| tempfile       | Python dahili       | Geçici dosya oluşturma      |
| shutil         | Python dahili       | Klasör silme                |
