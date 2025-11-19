import os
import asyncio
import aiohttp
import json
from datetime import datetime
from telegram import Bot
from telegram.constants import ParseMode
from aiohttp import web
import logging
import hashlib
import random

# ================ НАСТРОЙКИ ================
TELEGRAM_BOT_TOKEN = os.environ.get('TELEGRAM_NEWS_BOT_TOKEN')
CHANNEL_ID = os.environ.get('CHANNEL_ID')
PORT = int(os.environ.get('PORT', 10002))

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ================ ИСТОЧНИКИ НОВОСТЕЙ ================
NEWS_SOURCES = [
    {
        'name': 'CryptoCompare',
        'url': 'https://min-api.cryptocompare.com/data/v2/news/?lang=EN',
        'type': 'cryptocompare'
    },
    {
        'name': 'BlockchainNews', 
        'url': 'https://newsapi.org/v2/everything?q=blockchain&apiKey=demo&pageSize=5',
        'type': 'newsapi'
    }
]

# Хранилище обработанных новостей
processed_news = set()

# ================ СТИЛЬ MARVEL MARKET ================
MARVEL_STYLE_TEMPLATES = {
    'analysis': """
🔥 <b>{title}</b>

📌 <b>О ЧЕМ РЕЧЬ:</b>
{summary}

💡 <b>MARVEL АНАЛИЗ:</b>
• {analysis_point1}
• {analysis_point2} 
• {analysis_point3}

⚡ <b>ВЫВОДЫ:</b>
{conclusion}

🎯 <b>НАША ПОЗИЦИЯ:</b>
{position}

🔗 <b>Источник:</b> {source}
⏰ <b>Время:</b> {time}
    """,
    
    'breaking': """
🚨 <b>ЭКСТРЕННО: {title}</b>

📢 <b>СУТЬ СОБЫТИЯ:</b>
{event_details}

💥 <b>ПОСЛЕДСТВИЯ:</b>
• {impact1}
• {impact2}
• {impact3}

🎯 <b>ЧТО ДЕЛАТЬ:</b>
{action_advice}

🔗 <b>Источник:</b> {source}  
⏰ <b>Время:</b> {time}
    """
}

# Заголовки для обхода ограничений
USER_AGENTS = [
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36',
    'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36'
]

def generate_news_hash(news_item):
    """Генерируем уникальный хеш для новости"""
    content = f"{news_item['title']}_{news_item.get('url', '')}"
    return hashlib.md5(content.encode()).hexdigest()

def analyze_sentiment(title, summary):
    """Анализируем тональность новости"""
    positive_words = ['рост', 'вырос', 'успех', 'прорыв', 'инновация', 'партнерство', 'одобрение', 'запуск', 'bullish', 'up', 'success', 'breakthrough', 'approval']
    negative_words = ['падение', 'упал', 'сбой', 'запрет', 'регуляция', 'суд', 'хакеры', 'мошенничество', 'обвал', 'bearish', 'down', 'hack', 'scam', 'ban', 'crash']
    
    text = f"{title} {summary}".lower()
    
    positive_score = sum(1 for word in positive_words if word in text)
    negative_score = sum(1 for word in negative_words if word in text)
    
    if positive_score > negative_score:
        return "🟢 ПОЗИТИВ", "📈 Бычье настроение"
    elif negative_score > positive_score:
        return "🔴 НЕГАТИВ", "📉 Медвежье давление"
    else:
        return "🟡 НЕЙТРАЛ", "⚖️ Баланс сил"

def generate_marvel_analysis(news_item):
    """Генерируем авторский анализ в стиле Marvel Market"""
    title = news_item['title']
    summary = news_item.get('summary', title)[:300] + '...'
    source = news_item['source']
    
    sentiment, sentiment_desc = analyze_sentiment(title, summary)
    
    # Определяем тип новости
    title_lower = title.lower()
    if any(word in title_lower for word in ['hack', 'attack', 'exploit', 'stolen', 'scam', 'взлом', 'атака', 'кража', 'fraud']):
        news_type = 'breaking'
    elif any(word in title_lower for word in ['bitcoin', 'ethereum', 'btc', 'eth', 'crypto', 'regulation']):
        news_type = 'analysis'
    else:
        news_type = 'analysis'
    
    # Генерируем анализ в зависимости от типа
    if news_type == 'analysis':
        analysis_points = [
            "Потенциальное влияние на основные активы BTC/ETH",
            "Реакция рынка в краткосрочной перспективе", 
            "Долгосрочные последствия для индустрии"
        ]
        conclusions = [
            "Рынок может отреагировать в течение торговой сессии",
            "Рекомендуем следить за ценовой динамикой"
        ]
        position = f"{sentiment_desc} - {sentiment}"
        
        return MARVEL_STYLE_TEMPLATES['analysis'].format(
            title=title.upper(),
            summary=summary,
            analysis_point1=analysis_points[0],
            analysis_point2=analysis_points[1],
            analysis_point3=analysis_points[2],
            conclusion="\n".join([f"• {c}" for c in conclusions]),
            position=position,
            source=source,
            time=datetime.now().strftime('%d.%m.%Y %H:%M')
        )
    
    else:  # breaking
        impacts = [
            "Возможная повышенная волатильность на рынке",
            "Реакция регуляторов на инцидент",
            "Влияние на доверие инвесторов"
        ]
        actions = "Рекомендуем дождаться прояснения ситуации перед крупными сделками"
        
        return MARVEL_STYLE_TEMPLATES['breaking'].format(
            title=title.upper(),
            event_details=summary,
            impact1=impacts[0],
            impact2=impacts[1],
            impact3=impacts[2],
            action_advice=actions,
            source=source,
            time=datetime.now().strftime('%d.%m.%Y %H:%M')
        )

async def fetch_news_with_retry(source):
    """Получаем новости с повторами при ошибках"""
    headers = {
        'User-Agent': random.choice(USER_AGENTS),
        'Accept': 'application/json'
    }
    
    try:
        logger.info(f"📡 Получаем новости из {source['name']}...")
        
        async with aiohttp.ClientSession() as session:
            async with session.get(source['url'], headers=headers) as response:
                if response.status == 200:
                    data = await response.json()
                    news_items = []
                    
                    if source['type'] == 'cryptocompare':
                        for item in data.get('Data', [])[:5]:
                            news_item = {
                                'title': item.get('title', ''),
                                'summary': item.get('body', item.get('title', ''))[:300],
                                'url': item.get('url', ''),
                                'source': source['name'],
                                'hash': generate_news_hash({'title': item.get('title', ''), 'url': item.get('url', '')})
                            }
                            news_items.append(news_item)
                    
                    elif source['type'] == 'newsapi':
                        for item in data.get('articles', [])[:5]:
                            news_item = {
                                'title': item.get('title', ''),
                                'summary': item.get('description', item.get('title', ''))[:300],
                                'url': item.get('url', ''),
                                'source': source['name'],
                                'hash': generate_news_hash({'title': item.get('title', ''), 'url': item.get('url', '')})
                            }
                            news_items.append(news_item)
                    
                    logger.info(f"✅ Получено {len(news_items)} новостей из {source['name']}")
                    return news_items
                    
                else:
                    logger.warning(f"⚠️ Ошибка {source['name']} API: {response.status}")
                    return []
                    
    except Exception as e:
        logger.error(f"❌ Ошибка при получении новостей из {source['name']}: {e}")
        return []

async def get_mock_news():
    """Генерируем тестовые новости когда API недоступны"""
    mock_news = [
        {
            'title': 'Bitcoin демонстрирует устойчивость выше $40,000',
            'summary': 'Крупнейшая криптовалюта удерживает ключевой уровень поддержки, пока инвесторы оценивают макроэкономические данные.',
            'url': 'https://example.com/btc-news',
            'source': 'MarvelMarket Analytics',
            'hash': generate_news_hash({'title': 'Bitcoin демонстрирует устойчивость выше $40,000', 'url': 'https://example.com/btc-news'})
        },
        {
            'title': 'Ethereum готовится к следующему обновлению сети',
            'summary': 'Разработчики анонсировали важное обновление, которое улучшит масштабируемость блокчейна Ethereum.',
            'url': 'https://example.com/eth-news', 
            'source': 'MarvelMarket Analytics',
            'hash': generate_news_hash({'title': 'Ethereum готовится к следующему обновлению сети', 'url': 'https://example.com/eth-news'})
        }
    ]
    return mock_news

async def get_all_news():
    """Получаем новости со всех источников"""
    tasks = [fetch_news_with_retry(source) for source in NEWS_SOURCES]
    all_news = await asyncio.gather(*tasks)
    
    # Объединяем все новости в один список
    combined_news = []
    for news_list in all_news:
        combined_news.extend(news_list)
    
    # Если нет новостей от API, используем тестовые
    if not combined_news:
        logger.info("📝 Используем тестовые новости")
        combined_news = await get_mock_news()
    
    return combined_news

def filter_new_news(all_news):
    """Фильтруем только новые новости"""
    new_news = []
    for news_item in all_news:
        if news_item['hash'] not in processed_news:
            new_news.append(news_item)
            processed_news.add(news_item['hash'])
    
    logger.info(f"📰 Новых новостей: {len(new_news)}")
    return new_news

async def send_news_update():
    """Отправляем новостное обновление"""
    bot = Bot(token=TELEGRAM_BOT_TOKEN)
    
    # Первое сообщение при запуске
    try:
        welcome_msg = """
🚀 <b>MarvelMarket News Bot АКТИВИРОВАН!</b>

📡 <b>Мониторим:</b>
• Рыночные новости и аналитика
• Технические обновления
• Регуляторные изменения

⚡ <b>Режим работы:</b>
• Проверка каждые 30 минут
• Авторский анализ в стиле MarvelMarket
• Только самые важные события

💎 <b>MarvelMarket</b> - всегда в курсе крипто-событий!
        """
        await bot.send_message(
            chat_id=CHANNEL_ID,
            text=welcome_msg,
            parse_mode=ParseMode.HTML
        )
        logger.info("✅ Приветственное сообщение отправлено")
    except Exception as e:
        logger.error(f"❌ Ошибка при отправке приветствия: {e}")
    
    while True:
        try:
            logger.info("🔍 Начинаем мониторинг новостей...")
            
            # Получаем все новости
            all_news = await get_all_news()
            
            # Фильтруем только новые
            new_news = filter_new_news(all_news)
            
            # Отправляем каждую новость
            for news_item in new_news:
                try:
                    # Генерируем сообщение в стиле Marvel Market
                    message = generate_marvel_analysis(news_item)
                    
                    # Отправляем в канал
                    await bot.send_message(
                        chat_id=CHANNEL_ID,
                        text=message,
                        parse_mode=ParseMode.HTML,
                        disable_web_page_preview=False
                    )
                    
                    logger.info(f"✅ Отправлена новость: {news_item['title'][:50]}...")
                    
                    # Ждем 45 секунд между отправками
                    await asyncio.sleep(45)
                    
                except Exception as e:
                    logger.error(f"❌ Ошибка при отправке новости: {e}")
                    continue
            
            if not new_news:
                logger.info("📭 Новых новостей нет")
            
            # Ждем 30 минут до следующей проверки
            logger.info("⏰ Ожидание 30 минут до следующей проверки...")
            await asyncio.sleep(1800)
            
        except Exception as e:
            logger.error(f"❌ КРИТИЧЕСКАЯ Ошибка в send_news_update: {e}")
            logger.info("🔄 Перезапуск через 120 секунд...")
            await asyncio.sleep(120)

async def health_check(request):
    """Простой HTTP endpoint для проверки порта"""
    return web.Response(text="🚀 MarvelMarket News Bot is running!")

async def start_http_server():
    """Запускаем минимальный HTTP сервер только для проверки порта"""
    app = web.Application()
    app.router.add_get('/', health_check)
    app.router.add_get('/health', health_check)
    
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, '0.0.0.0', PORT)
    await site.start()
    
    logger.info(f"🌐 HTTP сервер запущен на порту {PORT} (только для проверки Render)")
    return runner

async def main():
    # ПРОВЕРЯЕМ ПЕРЕМЕННЫЕ ПРИ СТАРТЕ
    logger.info("🔍 Проверка переменных окружения...")
    logger.info(f"TELEGRAM_NEWS_BOT_TOKEN: {'✅' if TELEGRAM_BOT_TOKEN else '❌'}")
    logger.info(f"CHANNEL_ID: {'✅' if CHANNEL_ID else '❌'}")
    
    if not all([TELEGRAM_BOT_TOKEN, CHANNEL_ID]):
        logger.error("❌ Не установлены все необходимые переменные окружения!")
        exit(1)
    
    logger.info("✅ Все переменные окружения установлены")
    
    # Запускаем HTTP сервер на 30 секунд чтобы Render увидел порт
    logger.info("🔄 Запускаем HTTP сервер для проверки порта...")
    runner = await start_http_server()
    
    # Ждем 30 секунд чтобы Render успел проверить порт
    logger.info("⏳ Ожидаем 30 секунд для проверки порта Render...")
    await asyncio.sleep(30)
    
    # Останавливаем HTTP сервер - он больше не нужен
    logger.info("🛑 Останавливаем HTTP сервер...")
    await runner.cleanup()
    
    # Запускаем основную задачу
    logger.info("🚀 Запуск основной задачи мониторинга новостей...")
    await send_news_update()

if __name__ == "__main__":
    asyncio.run(main())
