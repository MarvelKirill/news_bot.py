import asyncio
import time
from datetime import datetime, timedelta
import hashlib
import logging
import aiohttp
import os

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)

class NewsManager:
    def __init__(self):
        self.last_news_hash = None
        self.is_processing = False
        self.last_news_time = None
        self.news_cooldown = timedelta(minutes=25)
        self.bot_token = os.getenv('BOT_TOKEN')
        self.channel_id = os.getenv('CHANNEL_ID')
        
    def get_news_hash(self, news_data):
        """Создает хеш новости для проверки дублирования"""
        content = f"{news_data.get('russian', '')}{news_data.get('english', '')}"
        return hashlib.md5(content.encode()).hexdigest()
    
    async def fetch_news_data(self):
        """Получение данных новостей - ЗАМЕНИТЕ НА ВАШ РЕАЛЬНЫЙ МЕТОД"""
        try:
            # ВРЕМЕННЫЕ ДАННЫЕ ДЛЯ ТЕСТА
            return {
                'russian': 'Это тестовая новость. Бот исправлен - теперь нет дублирования и интервал 30 минут.',
                'english': 'This is a test news. Bot fixed - no duplication and 30 minutes interval.'
            }
        except Exception as e:
            logging.error(f"Ошибка получения новостей: {e}")
            return None
    
    def format_news_message(self, news_data):
        """Форматирует одно сообщение с новостью"""
        return f"""📰 **Актуальная новость**

🇷🇺 **На русском:**
{news_data['russian']}

🇬🇧 **In English:**
{news_data['english']}

⏰ _Следующее обновление через 30 минут_"""
    
    async def send_telegram_message(self, message):
        """Отправка сообщения в Telegram"""
        if not self.bot_token or not self.channel_id:
            logging.error("Не настроен BOT_TOKEN или CHANNEL_ID")
            return False
            
        url = f"https://api.telegram.org/bot{self.bot_token}/sendMessage"
        
        payload = {
            'chat_id': self.channel_id,
            'text': message,
            'parse_mode': 'Markdown'
        }
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(url, json=payload) as response:
                    if response.status == 200:
                        logging.info("✅ Сообщение отправлено в Telegram")
                        return True
                    else:
                        error_text = await response.text()
                        logging.error(f"❌ Ошибка Telegram API: {response.status} - {error_text}")
                        return False
        except Exception as e:
            logging.error(f"❌ Ошибка отправки в Telegram: {e}")
            return False
    
    async def send_news_update(self):
        """Основная функция отправки новостей с защитой от дублирования"""
        
        if self.is_processing:
            logging.info("⏳ Новость уже обрабатывается, пропускаем")
            return
            
        current_time = datetime.now()
        if self.last_news_time and current_time - self.last_news_time < self.news_cooldown:
            time_left = self.news_cooldown - (current_time - self.last_news_time)
            logging.info(f"⏰ Слишком рано. Ждем еще: {time_left}")
            return
        
        self.is_processing = True
        try:
            logging.info("🔄 Начало обработки новости...")
            
            news_data = await self.fetch_news_data()
            if not news_data:
                logging.warning("📭 Нет данных новостей")
                return
            
            current_hash = self.get_news_hash(news_data)
            if current_hash == self.last_news_hash:
                logging.info("🔁 Дубликат новости, пропускаем")
                return
                
            message = self.format_news_message(news_data)
            success = await self.send_telegram_message(message)
            
            if success:
                self.last_news_hash = current_hash
                self.last_news_time = datetime.now()
                logging.info(f"✅ Новость отправлена: {self.last_news_time}")
            else:
                logging.error("❌ Не удалось отправить новость")
            
        except Exception as e:
            logging.error(f"💥 Ошибка: {e}")
        finally:
            self.is_processing = False

async def main():
    """Основная функция бота"""
    news_manager = NewsManager()
    
    logging.info("🚀 Бот новостей запущен!")
    logging.info("📰 Режим: новости каждые 30 минут")
    logging.info("⏰ Первая новость через 1 минуту...")
    
    # Первая новость через 1 минуту
    await asyncio.sleep(60)
    
    # Основной цикл
    while True:
        try:
            await news_manager.send_news_update()
            logging.info("⏳ Ожидание 30 минут до следующей новости...")
            await asyncio.sleep(1800)  # 30 минут
            
        except Exception as e:
            logging.error(f"💥 Ошибка в основном цикле: {e}")
            await asyncio.sleep(60)

if __name__ == "__main__":
    asyncio.run(main())
