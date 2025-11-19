import os
import asyncio
import aiohttp
import feedparser
from datetime import datetime
from telegram import Bot
from telegram.constants import ParseMode
import logging
import hashlib

# ================ НАСТРОЙКИ ================
TELEGRAM_BOT_TOKEN = os.environ.get('TELEGRAM_NEWS_BOT_TOKEN')
CHANNEL_ID = os.environ.get('CHANNEL_ID')

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ================ ИСТОЧНИКИ НОВОСТЕЙ ================
NEWS_SOURCES = {
    'CoinDesk': 'https://www.coindesk.com/arc/outboundfeeds/rss/',
    'CoinTelegraph': 'https://cointelegraph.com/rss',
    'Decrypt': 'https://decrypt.co/feed',
}

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

def generate_news_hash(news_item):
    """Генерируем уникальный хеш для новости"""
    content = f"{news_item['title']}_{news_item['link']}"
    return hashlib.md5(content.encode()).hexdigest()

def analyze_sentiment(title, summary):
    """Анализируем тональность новости"""
    positive_words = ['рост', 'вырос', 'успех', 'прорыв', 'инновация', 'партнерство', 'одобрение', 'запуск']
    negative_words = ['падение', 'упал', 'сбой', 'запрет', 'регуляция', 'суд', 'хакеры', 'мошенничество']
    
    title_lower = title.lower()
    summary_lower = summary.lower()
    
    positive_score = sum(1 for word in positive_words if word in title_lower or word in summary_lower)
    negative_score = sum(1 for word in negative_words if word in title_lower or word in summary_lower)
    
    if positive_score > negative_score:
        return "🟢 ПОЗИТИВ", "📈 Бычье настроение"
    elif negative_score > positive_score:
        return "🔴 НЕГАТИВ", "📉 Медвежье давление"
    else:
        return "🟡 НЕЙТРАЛ", "⚖️ Баланс сил"

def generate_marvel_analysis(news_item):
    """Генерируем авторский анализ в стиле Marvel Market"""
    title = news_item['title']
    summary = news_item.get('summary', '')[:200] + '...' if news_item.get('summary') else title
    source = news_item['source']
    
    sentiment, sentiment_desc = analyze_sentiment(title, summary)
    
    # Определяем тип новости
    if any(word in title.lower() for word in ['hack', 'attack', 'exploit', 'stolen', 'scam', 'взлом', 'атака']):
        news_type = 'breaking'
    else:
        news_type = 'analysis'
    
    # Генерируем анализ в зависимости от типа
    if news_type == 'analysis':
        analysis_points = [
            "Потенциальное влияние на основные активы",
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
            "Возможная повышенная волатильность",
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

async def fetch_news_from_source(source_name, rss_url):
    """Получаем новости из RSS источника"""
    try:
        logger.info(f"📡 Получаем новости из {source_name}...")
        feed = feedparser.parse(rss_url)
        
        news_items = []
        for entry in feed.entries[:3]:
            news_item = {
                'title': entry.title,
                'link': entry.link,
                'source': source_name,
                'summary': entry.get('summary', ''),
                'published': entry.get('published', ''),
                'hash': generate_news_hash({'title': entry.title, 'link': entry.link})
            }
            news_items.append(news_item)
        
        logger.info(f"✅ Получено {len(news_items)} новостей из {source_name}")
        return news_items
        
    except Exception as e:
        logger.error(f"❌ Ошибка при получении новостей из {source_name}: {e}")
        return []

async def get_all_news():
    """Получаем новости со всех источников"""
    tasks = []
    for source_name, rss_url in NEWS_SOURCES.items():
        task = fetch_news_from_source(source_name, rss_url)
        tasks.append(task)
    
    all_news = await asyncio.gather(*tasks)
    
    # Объединяем все новости в один список
    combined_news = []
    for news_list in all_news:
        combined_news.extend(news_list)
    
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
                    
                    # Ждем 30 секунд между отправками
                    await asyncio.sleep(30)
                    
                except Exception as e:
                    logger.error(f"❌ Ошибка при отправке новости: {e}")
                    continue
            
            if not new_news:
                logger.info("📭 Новых новостей нет")
            
            # Ждем 15 минут до следующей проверки
            logger.info("⏰ Ожидание 15 минут до следующей проверки...")
            await asyncio.sleep(900)
            
        except Exception as e:
            logger.error(f"❌ КРИТИЧЕСКАЯ Ошибка в send_news_update: {e}")
            logger.info("🔄 Перезапуск через 60 секунд...")
            await asyncio.sleep(60)

async def main():
    # ПРОВЕРЯЕМ ПЕРЕМЕННЫЕ ПРИ СТАРТЕ
    logger.info("🔍 Проверка переменных окружения...")
    logger.info(f"TELEGRAM_NEWS_BOT_TOKEN: {'✅' if TELEGRAM_BOT_TOKEN else '❌'}")
    logger.info(f"CHANNEL_ID: {'✅' if CHANNEL_ID else '❌'}")
    
    if not all([TELEGRAM_BOT_TOKEN, CHANNEL_ID]):
        logger.error("❌ Не установлены все необходимые переменные окружения!")
        exit(1)
    
    logger.info("✅ Все переменные окружения установлены")
    logger.info("🚀 MarvelMarket News Bot запущен!")
    
    # Запускаем мониторинг новостей
    await send_news_update()

if __name__ == "__main__":
    asyncio.run(main())
