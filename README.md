# 🎬 CreatorBot — Telegram Bot для видео-профессионалов

Умный помощник для YouTubers, монтажёров и контент-мейкеров.

## 🚀 Функции

| Функция | Статус |
|---|---|
| 📥 Скачать видео с YouTube (720p / 1080p / 480p) | ✅ Готово |
| 🎵 Извлечь аудио из YouTube (MP3) | ✅ Готово |
| 📸 Скачать Reel / видео с Instagram | ✅ Готово |
| 🎵 TikTok | 🔜 Скоро |
| 🐦 Twitter / X | 🔜 Скоро |

---

## ⚙️ Установка

### 1. Клонируй и перейди в папку
```bash
cd contact
```

### 2. Создай виртуальное окружение (рекомендуется)
```bash
python -m venv venv
venv\Scripts\activate   # Windows
```

### 3. Установи зависимости
```bash
pip install -r requirements.txt
```

### 4. Создай `.env` файл
Скопируй `.env.example` → `.env` и вставь свой токен:
```
BOT_TOKEN=123456789:AAXXXX...
```
Токен получи у [@BotFather](https://t.me/BotFather) в Telegram.

### 5. Запусти бота
```bash
python bot.py
```

---

## 📂 Структура проекта

```
contact/
├── bot.py              # Точка входа
├── config.py           # Настройки (токен)
├── handlers/
│   ├── start.py        # /start, главное меню
│   ├── youtube.py      # YouTube загрузка
│   └── instagram.py    # Instagram загрузка
├── utils/
│   ├── downloader.py   # yt-dlp обёртка
│   └── helpers.py      # Вспомогательные функции
├── downloads/          # Временные файлы (создаётся автоматически)
├── requirements.txt
└── .env
```

---

## ⚠️ Ограничения

- Telegram не позволяет отправлять файлы больше **50 МБ**
- Instagram: только **публичные** аккаунты
- YouTube: некоторые видео недоступны из-за авторских прав

---

## 🛠 Зависимости

- [python-telegram-bot](https://github.com/python-telegram-bot/python-telegram-bot) v20+
- [yt-dlp](https://github.com/yt-dlp/yt-dlp)
- [python-dotenv](https://github.com/theskumar/python-dotenv)
