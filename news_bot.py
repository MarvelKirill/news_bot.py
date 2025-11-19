import asyncio
import schedule
import time
from datetime import datetime, timedelta
import hashlib
import logging

class NewsManager:
    def __init__(self):
        self.last_news_hash = None
        self.is_processing = False
        self.last_news_time = None
        self.news_cooldown = timedelta(minutes=25)  # Защита от дублирования
        
    def get_news_hash(self, news_data):
        """Создает хеш новости для проверки дублирования"""
        content = f"{news_data.get('title', '')}{news_data.get('content', '')}"
        return hashlib.md5(content.encode()).hexdigest()
    
    async def fetch_news_data(self):
        """Получение данных новостей - замените на ваш реальный метод"""
        # Ваш код для получения новостей
        # Возвращает словарь с русским и английским текстом
        return {
            'russian': 'Текст новости на русском',
            'english': 'News text in English'
        }
    
    async def send_news_update(self):
        """Основная функция отправки новостей с защитой от дублирования"""
        
        # Защита от параллельного выполнения
        if self.is_processing:
            logging.info("Новость уже обрабатывается, пропускаем")
            return
            
        # Проверка временного интервала
        if self.last_news_time and datetime.now() - self.last_news_time < self.news_cooldown:
            logging.info("Слишком рано для следующей новости, пропускаем")
            return
        
        self.is_processing = True
        try:
            logging.info("Начало обработки новости...")
            
            # Получаем данные
            news_data = await self.fetch_news_data()
            if not news_data:
                logging.warning("Нет данных новостей")
                return
            
            # Проверяем на дублирование
            current_hash = self.get_news_hash(news_data)
            if current_hash == self.last_news_hash:
                logging.info("Дубликат новости, пропускаем")
                return
                
            # Формируем ОДНО сообщение
            message = self.format_news_message(news_data)
            
            # Отправляем сообщение
            await self.send_telegram_message(message)
            
            # Обновляем состояние
            self.last_news_hash = current_hash
            self.last_news_time = datetime.now()
            
            logging.info(f"Новость отправлена: {self.last_news_time}")
            
        except Exception as e:
            logging.error(f"Ошибка отправки новости: {e}")
        finally:
            self.is_processing = False
    
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
        # Ваш код отправки через бота
        # Убедитесь, что вызывается ТОЛЬКО ОДИН РАЗ
        pass

# Инициализация
news_manager = NewsManager()

def setup_news_schedule():
    """Настройка расписания для новостей"""
    schedule.clear()  # Очищаем ВСЕ предыдущие задания
    
    # ТОЛЬКО ОДИН вызов для новостей
    schedule.every(30).minutes.do(
        lambda: asyncio.create_task(news_manager.send_news_update())
    )
    
    logging.info("Расписание новостей установлено: каждые 30 минут")

# Запуск
setup_news_schedule()

# Основной цикл (упрощенный)
async def main_loop():
    while True:
        schedule.run_pending()
        await asyncio.sleep(60)  # Проверяем каждую минуту

# Запустить
# asyncio.run(main_loop())
