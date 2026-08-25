import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

# Настройки — вставь свои
SMTP_EMAIL = "mamalena.orders@gmail.com"  # почта-отправитель
SMTP_PASSWORD = "pzol panq mcin rkch"     # App Password (НЕ обычный пароль)
MANAGER_EMAIL = "mamalena.orders@gmail.com"        # почта менеджера (куда приходят заказы)


def send_order_email(order):
    """
    Отправляет email менеджеру о новом заказе.

    order = {
        'id': 15,
        'user_name': 'Анна',
        'phone': '+79001234567',
        'address': 'ул. Ленина 10, кв 5',
        'items': [
            {'name': 'Борщ', 'quantity': 2, 'price': 350},
            {'name': 'Хлеб', 'quantity': 1, 'price': 50},
        ],
        'total': 750,
        'payment': 'card',  # или 'cash'
        'comment': 'Без лука'
    }
    """

    # Формируем список блюд
    items_text = ""
    for item in order.get('items', []):
        items_text += f"  • {item['name']} x{item['quantity']} — {item['price'] * item['quantity']} ₽\n"

    # Текст письма
    body = f"""🔔 НОВЫЙ ЗАКАЗ #{order['id']}

👤 Клиент: {order.get('user_name', 'Не указано')}
📱 Телефон: {order.get('phone', 'Не указано')}
📍 Адрес: {order.get('address', 'Самовывоз')}

🍽 Состав заказа:
{items_text}
💰 Итого: {order['total']} ₽
💳 Оплата: {'Картой' if order.get('payment') == 'card' else 'Наличными'}

📝 Комментарий: {order.get('comment', '—')}
"""

    # Создаём письмо
    msg = MIMEMultipart()
    msg['From'] = SMTP_EMAIL
    msg['To'] = MANAGER_EMAIL
    msg['Subject'] = f"🔔 Новый заказ #{order['id']} — {order['total']} ₽"

    msg.attach(MIMEText(body, 'plain', 'utf-8'))

    # Отправляем
    try:
        with smtplib.SMTP_SSL('smtp.gmail.com', 465) as server:
            server.login(SMTP_EMAIL, SMTP_PASSWORD)
            server.send_message(msg)
        print(f"✅ Email отправлен: заказ #{order['id']}")
        return True
    except Exception as e:
        print(f"❌ Ошибка отправки email: {e}")
        return False


# Пример использования:
if __name__ == "__main__":
    test_order = {
        'id': 1,
        'user_name': 'Анна',
        'phone': '+79001234567',
        'address': 'ул. Ленина 10',
        'items': [
            {'name': 'Борщ', 'quantity': 2, 'price': 350},
            {'name': 'Компот', 'quantity': 1, 'price': 100},
        ],
        'total': 800,
        'payment': 'card',
        'comment': 'Побольше сметаны'
    }
    send_order_email(test_order)
