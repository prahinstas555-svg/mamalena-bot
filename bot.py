import os
import logging
import json
import asyncio
from dotenv import load_dotenv
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes, MessageHandler, filters
from supabase import create_client, Client
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

load_dotenv()

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
WEBAPP_URL = os.getenv("WEBAPP_URL")

# Gmail настройки
GMAIL_EMAIL = os.getenv("GMAIL_EMAIL")          # mamalena.zakazy@gmail.com
GMAIL_APP_PASSWORD = os.getenv("GMAIL_APP_PASSWORD")  # pzol panq mcin rkch

if not all([SUPABASE_URL, SUPABASE_KEY, TELEGRAM_TOKEN, GMAIL_EMAIL, GMAIL_APP_PASSWORD]):
    raise ValueError("Проверь .env — не все переменные заполнены")

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user
    await update.message.reply_html(
        rf"Привет, {user.mention_html()}! Нажми кнопку ниже, чтобы открыть меню 🍽",
        reply_markup={
            "inline_keyboard": [[{
                "text": "🍽 Открыть меню",
                "web_app": {"url": WEBAPP_URL}
            }]]
        }
    )


async def handle_web_app_data(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    try:
        data = json.loads(update.message.web_app_data.data)
        logger.info(f"Получены данные из WebApp: {data}")
        await update.message.reply_text(
            f"✅ Заказ на сумму {data.get('total', 0)} руб. принят!"
        )
    except Exception as e:
        logger.error(f"Ошибка WebApp данных: {e}")


def send_order_email(order_data: dict, user_name: str, user_phone: str) -> bool:
    """Отправка email о новом заказе через Gmail"""
    try:
        message = MIMEMultipart()
        message["From"] = GMAIL_EMAIL
        message["To"] = GMAIL_EMAIL
        message["Subject"] = f"🔔 Новый заказ #{order_data['id']} — {order_data['total']} ₽"

        items = order_data.get("items", [])
        items_text = ""
        for item in items:
            price = item.get('price', 0) * item.get('quantity', 1)
            items_text += f"  • {item['name']} x{item['quantity']} — {price} ₽\n"

        payment_text = "💵 Наличные" if order_data.get("payment") == "cash" else "💳 Картой"

        body = f"""🔔 НОВЫЙ ЗАКАЗ #{order_data['id']}

👤 Клиент: {user_name}
📱 Телефон: {user_phone}
🆔 Telegram ID: {order_data['telegram_id']}

🍽 Состав заказа:
{items_text}
💰 Итого: {order_data['total']} ₽
{payment_text}
📍 Адрес: {order_data.get('address', 'Самовывоз')}
📝 Комментарий: {order_data.get('comment', '—')}
🕐 Время: {order_data.get('created_at', '—')}
"""
        message.attach(MIMEText(body, "plain", "utf-8"))

        with smtplib.SMTP_SSL('smtp.gmail.com', 465) as server:
            server.login(GMAIL_EMAIL, GMAIL_APP_PASSWORD)
            server.sendmail(GMAIL_EMAIL, GMAIL_EMAIL, message.as_string())

        logger.info(f"✅ Email отправлен для заказа #{order_data['id']}")
        return True
    except Exception as e:
        logger.error(f"❌ Ошибка email: {e}")
        return False


async def check_new_orders(context: ContextTypes.DEFAULT_TYPE) -> None:
    """Проверка новых заказов каждые 30 секунд"""
    try:
        response = supabase.table("orders") \
            .select("*") \
            .eq("status", "new") \
            .execute()

        orders = response.data
        if not orders:
            return

        for order in orders:
            user_resp = supabase.table("users") \
                .select("name, phone") \
                .eq("telegram_id", order["telegram_id"]) \
                .single() \
                .execute()

            user_name = user_resp.data.get("name", "Неизвестный") if user_resp.data else "Неизвестный"
            user_phone = user_resp.data.get("phone", "—") if user_resp.data else "—"

            payment_text = "💵 Наличные" if order.get("payment") == "cash" else "💳 Картой"

            sent = send_order_email(order, user_name, user_phone)

            if sent:
                supabase.table("orders") \
                    .update({"status": "notified"}) \
                    .eq("id", order["id"]) \
                    .execute()

                try:
                    await context.bot.send_message(
                        chat_id=order["telegram_id"],
                        text=f"✅ Ваш заказ #{order['id']} на сумму {order['total']} ₽ принят!\n\n{payment_text}\nОжидайте доставку! 🚗"
                    )
                except Exception as e:
                    logger.warning(f"Не удалось отправить сообщение в Telegram: {e}")

    except Exception as e:
        logger.error(f"Ошибка проверки заказов: {e}")


def main() -> None:
    application = Application.builder().token(TELEGRAM_TOKEN).build()

    application.add_handler(CommandHandler("start", start))
    application.add_handler(MessageHandler(filters.StatusUpdate.WEB_APP_DATA, handle_web_app_data))

    application.job_queue.run_repeating(check_new_orders, interval=30, first=10)

    logger.info("🚀 Бот запущен. Проверка заказов каждые 30 сек.")
    application.run_polling()


if __name__ == "__main__":
    main()














