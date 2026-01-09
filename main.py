import asyncio
import sys
from telethon import TelegramClient
from google import genai

# НАЛАШТУВАННЯ 
API_ID = 36201763  #Telegram API ID
API_HASH = '-------------'  #Telegram API Hash
GEMINI_KEY = '--------------'  #Gemini API Key
MODEL_NAME = '--------------'  # Модель: gemini-2.0-flash або gemini-3-flash-preview
MSG_LIMIT = 7  # Кількість останніх повідомлень з кожного каналу

ai_client = genai.Client(api_key=GEMINI_KEY)
tg_client = TelegramClient('uankee_session', API_ID, API_HASH)

def parse_selection(selection_str, max_val):
    indices = set()
    parts = selection_str.replace(',', ' ').split()
    for part in parts:
        try:
            if '-' in part:
                start, end = map(int, part.split('-'))
                indices.update(range(start, end + 1))
            elif part.isdigit():
                indices.add(int(part))
        except ValueError:
            continue
    return sorted([i for i in indices if 1 <= i <= max_val])

async def main():
    try:
        await tg_client.start()
    except Exception as e:
        print(f"Помилка авторизації: {e}")
        return

    print("Отримую список каналів...")
    channels = []
    async for dialog in tg_client.iter_dialogs():
        if dialog.is_channel:
            channels.append(dialog)

    if not channels:
        print("Каналів не знайдено.")
        return

    for i, ch in enumerate(channels, 1):
        print(f"{i}. {ch.name}")

    selected_indices = []
    while not selected_indices:
        print(f"\nВведіть діапазони (1-{len(channels)}) або 'exit':")
        user_input = input("> ").strip().lower()
        if user_input == 'exit': return
        selected_indices = parse_selection(user_input, len(channels))

    full_news_text = ""
    print(f"\nЗбираю новини...")
    
    for idx in selected_indices:
        target = channels[idx-1]
        print(f"[{idx}] Читаю: {target.name}...")
        try:
            async for msg in tg_client.iter_messages(target, limit=MSG_LIMIT):
                if msg.text and len(msg.text) > 15:
                    full_news_text += f"Джерело [{target.name}]: {msg.text}\n\n"
        except Exception as e:
            print(f"Помилка: {e}")

    if full_news_text:
        print(f"Генерую дайджест ({MODEL_NAME})...")
        try:
            # --- ПРОМТ (Налаштування логіки ШІ) ---
            prompt = (
                "Ти — професійний аналітик новин. Твоє завдання: опрацювати вхідний масив повідомлень і створити сухий, інформативний дайджест.\n\n"
                "ПРАВИЛА ОФОРМЛЕННЯ:\n"
                "1. ГРУПУВАННЯ: Розділи новини за логічними категоріями (наприклад: Політика, Економіка, Технології, Події).\n"
                "2. ЗАГОЛОВКИ: Використовуй **жирний шрифт** для назв категорій та ключових тез.\n"
                "3. СТИЛЬ: Максимально лаконічно, лише факти. Без оціночних суджень та емоцій.\n"
                "4. ЗАБОРОНИ: Не використовуй емодзі. Не пиши вступних фраз.\n"
                "5. ДЖЕРЕЛА: В кінці кожного пункту вказуй джерело у квадратних дужках [Джерело].\n\n"
                "6. ОБСЯГ: Весь дайджест має бути максимально коротким (до 4000 символів). Вибирай тільки найважливіші 10-12 новин з усього масиву.\n"
                f"ТЕКСТ ДЛЯ АНАЛІЗУ:\n{full_news_text}"
            )

            response = ai_client.models.generate_content(model=MODEL_NAME, contents=prompt)
            
            if response.text:
                await tg_client.send_message('me', f"🆕 **Ваш дайджест:**\n\n{response.text}")
                print("\n✅ Надіслано в 'Saved Messages'!")
            else:
                print("⚠️ ШІ повернув порожню відповідь.")

        except Exception as e:
            print(f"❌ Помилка Gemini API: {e}")
    else:
        print("\nℹ️ Немає тексту для обробки.")

if __name__ == "__main__":
    with tg_client:
        tg_client.loop.run_until_complete(main())