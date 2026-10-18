# 🚀 Instagram Video Downloader & Video Note Telegram Bot

Ushbu loyiha **Python**, **aiogram 3.x**, **yt-dlp** va **FFmpeg** texnologiyalari asosida yaratilgan ko'p funksiyali Telegram bot hisoblanadi.

---

## ✨ Asosiy Imkoniyatlari

1. 📥 **Instagram Yuklovchi:**
   - Instagram Reels, video postlar, IGTV va karusellarni (albom) sifatli MP4 formatida yuklab beradi.
   - Post muallifi va sarlavhasini chiroyli formatda ko'rsatadi.
   - Original postga eltuvchi inline tugma taqdim etadi.

2. ⭕ **Dumaloq Video (Video Note / Kruglyash) Generator:**
   - Foydalanuvchi botga istalgan oddiy video (yoki video fayl) yuborganida uni avtomatik tarzda markazidan 1:1 kvadrat qilib qirqadi.
   - 384x384 o'lchamda Telegram dumaloq video xabari ko'rinishida yuboradi.
   - Agar video 60 soniyadan uzun bo'lsa, Telegram talabi bo'yicha dastlabki 60 soniyasini oladi.

3. ⚡ **Asinxron va Xavfsiz:**
   - Bir vaqtning o'zida bir nechta foydalanuvchi so'rovlarini qotib qolmasdan qayta ishlaydi.
   - Yuklangan barcha vaqtinchalik fayllar foydalanuvchiga yetkazilgach zudlik bilan o'chiriladi.

---

## 📁 Loyiha Strukturasi

```text
bott/
├── .env                  # Bot tokeni saqlanadigan konfiguratsiya fayli
├── .env.example          # Namuna env fayli
├── .gitignore            # Git uchun e'tiborga olinmaydigan fayllar
├── config.py             # Sozlamalar va o'zgaruvchilar moduli
├── downloader.py         # yt-dlp orqali Instagram yuklovchi mexanizm
├── video_converter.py    # FFmpeg orqali dumaloq video tayyorlash moduli
├── handlers.py           # Telegram xabarlari va buyruqlarini ushlovchi handlerlar
├── main.py               # Botni ishga tushirish nuqtasi
├── requirements.txt      # Kutubxonalar ro'yxati
└── README.md             # Qo'llanma
```

---

## 🛠️ O'rnatish va Ishga Tushirish

### 1-qadam: Kutubxonalarni o'rnatish

```bash
pip install -r requirements.txt
```

### 2-qadam: Tokenni `.env` fayliga kiritish

[`.env`](file:///c:/Users/01/Downloads/bott/.env) faylini oching va [@BotFather](https://t.me/BotFather) dan olingan tokenni yozing:

```env
BOT_TOKEN=8890328774:AAEGENgT93aj2y0DFVmuAyN1BC6SsEZEqk4
```

### 3-qadam: Botni ishga tushirish

```bash
python main.py
```
