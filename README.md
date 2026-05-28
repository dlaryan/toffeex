# Toffee Extractor v2.0 - CLI Tool

বাংলাদেশের Toffee লাইভ টিভি চ্যানেলের প্লেব্যাক লিংক এক্সট্রাক্ট করার জন্য একটি Python স্ক্রিপ্ট। এই টুলটি JSON এবং M3U প্লেলিস্ট জেনারেট করে।

## ✨ নতুন ফিচার

- **Auto Token Refresh** - টোকেন এক্সপায়ার হওয়ার আগেই অটো রিফ্রেশ
- **Token Auto-Save** - `.toffee_token` ফাইলে সেভ হয়
- **401 Detection** - টোকেন এক্সপায়ার হলে সতর্কতা
- **Backup System** - `.toffee_token_backup` এ ব্যাকআপ

## 📋 প্রয়োজনীয়তা

- Python 3.8+
- বিস্তারিত দেখুন: `requirements.txt`

## 🚀 ইনস্টলেশন

```bash
# Clone করুন
git clone https://github.com/YOUR_USERNAME/toffee-extractor.git
cd toffee-extractor

# Dependencies ইনস্টল করুন
pip install -r requirements.txt
```

## ⚙️ কনফিগারেশন

### সোর্স কোডে টোকেন (ডিফল্ট)
টোকেন সরাসরি স্ক্রিপ্টের প্রথম লাইনে `TOKEN = "..."` দেওয়া আছে।

### Option 1: config.ini ফাইলে (প্রস্তাবিত)

```ini
[TOFFEE]
TOKEN = আপনার_JWT_টোকেন_এখানে

[SETTINGS]
MAX_RETRIES = 3
TIMEOUT = 20
WORKERS = 5
JSON_OUTPUT = toffee_playlist.json
M3U_OUTPUT = toffee_playlist.m3u
AUTO_REFRESH = True
REFRESH_BEFORE_HOURS = 24
```

### Option 2: পরিবেশ ভেরিয়েবল

```bash
export TOFFEE_TOKEN="আপনার_টোকেন"
```

## 🎯 ব্যবহার

```bash
# ডিফল্ট (সোর্স কোডের টোকেন ব্যবহার করবে)
python toffee_extractor.py

# পরিবেশ ভেরিয়েবল দিয়ে
TOFFEE_TOKEN="আপনার_টোকেন" python toffee_extractor.py

# কমান্ড লাইন আর্গুমেন্ট দিয়ে
python toffee_extractor.py --token "আপনার_টোকেন"
```

## 📤 আউটপুট

স্ক্রিপ্ট চালানোর পর নিম্নলিখিত ফাইলগুলো তৈরি হবে:

- `toffee_playlist.json` - সম্পূর্ণ চ্যানেল ডেটা JSON ফরম্যাটে
- `toffee_playlist.m3u` - IPTV প্লেলিস্ট M3U ফরম্যাটে
- `.toffee_token` - সেভ করা টোকেন
- `.toffee_token_backup` - টোকেন ব্যাকআপ

## 🔄 টোকেন ম্যানেজমেন্ট

```
[*] Token expires: 2026-11-21 12:05:16 UTC
[*] Time remaining: ~177 days, 10 hours
[*] Toffee Extractor Started at ...
```

**Auto-Refresh সেটিংস:**
- `AUTO_REFRESH_ENABLED = True` - অটো রিফ্রেশ চালু
- `REFRESH_BEFORE_HOURS = 24` - ২৪ ঘণ্টা আগে রিফ্রেশ চেষ্টা করবে

**ম্যানুয়াল আপডেট:**
টোকেন এক্সপায়ার হলে স্ক্রিপ্টের `TOKEN` ভেরিয়েবলে নতুন টোকেন দিন।

## ⚠️ গুরুত্বপূর্ণ নোট

- এই টুল শুধুমাত্র শিক্ষামূলক উদ্দেশ্যে ব্যবহার করুন
- টোকেন GitHub এ শেয়ার করবেন না (.gitignore এ আছে)
- সার্ভার লোড এড়াতে ৫টি workers ব্যবহার করা হয়েছে
- কোনো DRM protected চ্যানেল স্কিপ করা হবে

## 🔧 Troubleshooting

### Connection Error
- ইন্টারনেট কানেকশন চেক করুন
- ফায়ারওয়াল/প্রক্সি সেটিংস দেখুন

### Token Expired
- নতুন JWT টোকেন জেনারেট করুন
- স্ক্রিপ্টের `TOKEN` ভেরিয়েবল আপডেট করুন

### 401 Unauthorized Error
- টোকেন এক্সপায়ার হয়ে থাকতে পারে
- নতুন টোকেন নিন

### Empty Output
- টোকেন কপি করতে ভুল হচ্ছে না তো?
- সমস্ত RAIL_IDs সঠিক কিনা যাচাই করুন

## 📜 License

MIT License - বিস্তারিত দেখুন: [LICENSE](LICENSE) ফাইল

## 👨‍💻 Author

Md Sohanur Rahman Hady
- Telegram: https://t.me/livesportsplay