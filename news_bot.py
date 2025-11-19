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
    }
]

# Хранилище обработанных новостей
processed_news = set()

# ================ ПЕРЕВОД И АНАЛИЗ ================
CRYPTO_TERMS = {
    # Основные термины
    'bitcoin': 'Биткоин', 'btc': 'BTC', 'ethereum': 'Ethereum', 'eth': 'ETH',
    'crypto': 'криптовалюта', 'cryptocurrency': 'криптовалюта', 'blockchain': 'блокчейн',
    'defi': 'DeFi', 'nft': 'NFT', 'exchange': 'биржа', 'wallet': 'кошелек',
    
    # Действия
    'rise': 'рост', 'grow': 'рост', 'increase': 'увеличение', 'up': 'вверх',
    'fall': 'падение', 'drop': 'снижение', 'decrease': 'снижение', 'down': 'вниз',
    'surge': 'резкий рост', 'plunge': 'обвал', 'crash': 'крах', 'rally': 'ралли',
    
    # Компании и проекты
    'binance': 'Binance', 'coinbase': 'Coinbase', 'kraken': 'Kraken',
    'solana': 'Solana', 'cardano': 'Cardano', 'polkadot': 'Polkadot',
    'uniswap': 'Uniswap', 'chainlink': 'Chainlink', 'litecoin': 'Litecoin',
    
    # Технические термины
    'mining': 'майнинг', 'staking': 'стейкинг', 'yield': 'доходность',
    'liquidity': 'ликвидность', 'volatility': 'волатильность',
    'market cap': 'капитализация', 'trading volume': 'объем торгов',
    
    # Регуляция
    'regulation': 'регулирование', 'sec': 'SEC', 'securities': 'ценные бумаги',
    'lawsuit': 'иск', 'legal': 'юридический', 'government': 'правительство',
    
    # Безопасность
    'hack': 'взлом', 'security': 'безопасность', 'vulnerability': 'уязвимость',
    'attack': 'атака', 'exploit': 'эксплойт', 'scam': 'мошенничество'
}

def translate_to_russian(text):
    """Переводим ключевые термины на русский"""
    if not text:
        return ""
    
    text_lower = text.lower()
    translated = text
    
    # Заменяем термины сохраняя регистр
    for eng, rus in CRYPTO_TERMS.items():
        if eng in text_lower:
            # Сохраняем регистр первого символа
            if text_lower[text_lower.index(eng)].isupper():
                rus = rus.capitalize()
            translated = translated.replace(eng, rus).replace(eng.capitalize(), rus)
    
    return translated

def generate_russian_analysis(news_item):
    """Генерируем анализ на русском с полезной информацией"""
    title = translate_to_russian(news_item['title'])
    summary = translate_to_russian(news_item.get('summary', title))[:250] + '...'
    source = news_item['source']
    
    # Анализируем тональность
    text_for_analysis = f"{title} {summary}".lower()
    
    # Определяем категорию новости
    if any(word in text_for_analysis for word in ['взлом', 'атака', 'мошенничество', 'кража', 'хакер']):
        category = "БЕЗОПАСНОСТЬ"
        emoji = "🛡️"
    elif any(word in text_for_analysis for word in ['регулирование', 'правительство', 'закон', 'sec', 'иск']):
        category = "РЕГУЛЯЦИЯ"
        emoji = "⚖️"
    elif any(word in text_for_analysis for word in ['обновление', 'технология', 'протокол', 'сеть', 'масштабируемость']):
        category = "ТЕХНОЛОГИИ"
        emoji = "🔧"
    elif any(word in text_for_analysis for word in ['партнерство', 'интеграция', 'сотрудничество', 'запуск']):
        category = "ПАРТНЕРСТВА"
        emoji = "🤝"
    else:
        category = "РЫНОК"
        emoji = "📊"
    
    # Генерируем полезные инсайты
    insights = [
        "📈 <b>Влияние на BTC/ETH:</b> " + get_btc_eth_impact(text_for_analysis),
        "💰 <b>Торговая идея:</b> " + get_trading_idea(text_for_analysis),
        "⏰ <b>Временной горизонт:</b> " + get_time_horizon(text_for_analysis)
    ]
    
    # Формируем сообщение
    message = f"{emoji} <b>НОВОСТЬ {category}</b> {emoji}\n\n"
    message += f"🔥 <b>{title.upper()}</b>\n\n"
    message += f"📌 <b>СУТЬ СОБЫТИЯ:</b>\n{summary}\n\n"
    message += "💡 <b>ПОЛЕЗНЫЕ ИНСАЙТЫ:</b>\n"
    for insight in insights:
        message += f"• {insight}\n"
    message += f"\n🎯 <b>РЕКОМЕНДАЦИЯ:</b> {get_recommendation(text_for_analysis)}\n"
    message += f"\n🔗 <b>Источник:</b> {source}\n"
    message += f"⏰ <b>Время анализа:</b> {datetime.now().strftime('%d.%m.%Y %H:%M')}\n"
    message += "\n💎 <b>MarvelMarket</b> - умные инсайты для твоих инвестиций!"
    
    return message

def get_btc_eth_impact(text):
    """Определяем влияние на основные активы"""
    if any(word in text for word in ['биткоин', 'btc', 'майнинг']):
        return "Прямое влияние на BTC - следим за ценовой реакцией"
    elif any(word in text for word in ['ethereum', 'eth', 'смарт-контракт']):
        return "Влияние на ETH и экосистему DeFi"
    elif any(word in text for word in ['регулирование', 'правительство']):
        return "Возможна волатильность на всем рынке"
    else:
        return "Локальное влияние - следим за связанными активами"

def get_trading_idea(text):
    """Генерируем торговую идею"""
    if any(word in text for word in ['рост', 'увеличение', 'ралли']):
        return "Рассмотреть покупки на коррекциях"
    elif any(word in text for word in ['падение', 'снижение', 'обвал']):
        return "Осторожность с покупками, возможны тейк-профиты"
    elif any(word in text for word in ['взлом', 'мошенничество']):
        return "Временное снижение - возможность для накопления"
    else:
        return "Следить за развитием ситуации перед сделками"

def get_time_horizon(text):
    """Определяем временной горизонт"""
    if any(word in text for word in ['взлом', 'атака', 'суд']):
        return "Краткосрочный (1-3 дня)"
    elif any(word in text for word in ['регулирование', 'закон']):
        return "Среднесрочный (1-4 недели)"
    elif any(word in text for word in ['технология', 'обновление']):
        return "Долгосрочный (1-6 месяцев)"
    else:
        return "Кратко-среднесрочный (1-2 недели)"

def get_recommendation(text):
    """Даем рекомендацию"""
    if any(word in text for word in ['рост', 'партнерство', 'запуск']):
        return "Позитивный сценарий - искать точки входа"
    elif any(word in text for word in ['падение', 'взлом', 'мошенничество']):
        return "Осторожность - дождаться прояснения"
    elif any(word in text for word in ['регулирование', 'суд']):
        return "Нейтрально - следить за развитием событий"
    else:
        return "Внимательное наблюдение - готовность к действию"

# Остальной код без изменений...
async def fetch_news_with_retry(source):
    """Получаем новости с повторами при ошибках"""
    headers = {
        'User-Agent': random.choice([
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'
        ]),
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
                        for item in data.get('Data', [])[:3]:  # Только 3 новости
                            news_item = {
                                'title': item.get('title', ''),
                                'summary': item.get('body', item.get('title', ''))[:300],
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
            'title': 'Bitcoin Shows Strength Above $40,000 Level',
            'summary': 'Major cryptocurrency holds key support level as investors assess macroeconomic data and institutional interest continues to grow.',
            'url': 'https://example.com/btc-news',
            'source': 'MarvelMarket Analytics',
            'hash': generate_news_hash({'title': 'Bitcoin Shows Strength Above $40,000 Level', 'url': 'https://example.com/btc-news'})
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

def generate_news_hash(news_item):
    """Генерируем уникальный хеш для новости"""
    content = f"{news_item['title']}_{news_item.get('url', '')}"
    return hashlib.md5(content.encode()).hexdigest()

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

📡 <b>Мониторим самые важные новости:</b>
• Безопасность и взломы
• Регуляторные изменения  
• Технические обновления
• Ключевые партнерства

⚡ <b>Режим работы:</b>
• 1 важная новость каждые 30 минут
• Авторский анализ на русском
• Полезные инсайты и рекомендации

💎 <b>MarvelMarket</b> - только самое важное!
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
            
            # Отправляем только ОДНУ самую важную новость
            if new_news:
                # Выбираем самую важную новость (первую в списке)
                most_important_news = new_news[0]
                
                try:
                    # Генерируем сообщение на русском с анализом
                    message = generate_russian_analysis(most_important_news)
                    
                    # Отправляем в канал
                    await bot.send_message(
                        chat_id=CHANNEL_ID,
                        text=message,
                        parse_mode=ParseMode.HTML,
                        disable_web_page_preview=False
                    )
                    
                    logger.info(f"✅ Отправлена новость: {most_important_news['title'][:50]}...")
                    
                except Exception as e:
                    logger.error(f"❌ Ошибка при отправке новости: {e}")
            else:
                logger.info("📭 Новых новостей нет")
            
            # Ждем 30 минут до следующей проверки
            logger.info("⏰ Ожидание 30 минут до следующей проверки...")
            await asyncio.sleep(1800)  # 30 минут
            
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
