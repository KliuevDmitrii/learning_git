 # Проект RateBot

 RateBot — это Python-бот, который отслеживает курс валют через API и присылает уведомления в Telegram, если курс вышел за установленные пороги.

## Шаги
1. Склонировать проект:
```bash
git clone https://github.com/KliuevDmitrii/learning_git.git
```

2. Создать и активировать виртуальное окружение:

```bash
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
```

3. Установить зависимости из файла `requirements.txt`, который находится в корне проекта:
```bash
pip3 install -r requirements.txt
```

 Проект находится в папке project

 4. Переименовать файл data в data.json, в файле подставить свои данные:

    {
        "TELEGRAM": {
            "TOKEN":"yourtoken",
            "CHAT_ID":"yourchatid"
        },
        "access_key":"youraccesskey"
    }

5. Отредактируйте `config.ini`:
'''
[exchange]
url_base = https://api.apilayer.com/exchangerates_data/latest
base_currency = USD
target_currency = GEL
threshold = 2.7
min_threshold = 2.4

[telegram]
url_telegram = https://api.telegram.org/bot
'''


6. Структура проекта:
'''
learning_git/
├── project/
│ ├── exchange_rate.py
│ ├── ConfigProvider.py
│ ├── DataProvider.py
│ ├── config.ini
│ └── data.json
├── requirements.txt
└── README.md
'''

## Что делает RateBot

- Запрашивает курс валют с помощью API (apilayer)
- Сравнивает курс с установленными порогами
- Если курс выходит за пределы — отправляет сообщение в Telegram
- Работает с параметрами из `config.ini` и `data.json`


## Полезные ссылки
- [Подсказка по Markdown](https://www.markdownguide.org/basic-syntax/)
- [Генератор .gitignore](https://www.toptal.com/developers/gitignore)

---
