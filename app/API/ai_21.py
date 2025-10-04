# ai_21.py
from ai21 import AI21Client
from ai21.models.chat import ChatMessage
from services.rag_system import RAGSystem
import os, logging, re
from datetime import datetime
import pytz

logger = logging.getLogger(__name__)

# Глобальный экземпляр RAG системы
rag_system = RAGSystem(always_enabled=True)

# Короткая память пользователей с сущностями
# {user_id: {"last_queries": [], "last_entities": {}}}
user_memory = {}

# Функция для текущего времени в Беларуси
def get_current_time_belarus():
    tz = pytz.timezone("Europe/Minsk")
    now = datetime.now(tz)
    return now.strftime("%H:%M:%S")

async def ask_ai21_with_rag(messages: list, user_id: str = None, model="jamba-large", max_tokens=1024) -> str:
    """
    Генерация текста через AI21 с RAG, короткой памятью и актуальным временем
    """
    try:
        user_msg = messages[-1]["content"] if messages else ""

        # Проверка на запрос времени
        if any(w in user_msg.lower() for w in ["который час", "сколько сейчас", "время"]):
            current_time = get_current_time_belarus()
            messages.append({"role": "system", "content": f"Текущее время в Беларуси: {current_time}"})

        # Загружаем память пользователя
        last_queries = []
        last_entities = {}
        if user_id and user_id in user_memory:
            last_queries = user_memory[user_id]["last_queries"][-10:]
            last_entities = user_memory[user_id]["last_entities"]

        # Формируем контекст для системного сообщения
        context_hint = ""
        if last_entities:
            entities_text = ", ".join(f"{k}: {v}" for k, v in last_entities.items())
            context_hint = f"\nИспользуй последние сущности из памяти пользователя: {entities_text}"

        system_message = f"""
Ты интеллектуальный ассистент для пользователей в Беларуси.
Отвечай с учётом местных реалий и актуальной информации.
Используй только проверенные данные из интернета.
Память пользователя (последние сообщения): {last_queries if last_queries else 'нет истории'}
{context_hint}
        """

        # Формируем список сообщений для LLM
        chat_messages = [ChatMessage(role="system", content=system_message)]
        chat_messages += [ChatMessage(role=m["role"], content=m["content"]) for m in messages]

        # Генерация ответа
        client = AI21Client(api_key=os.getenv("AI21_API_KEY"))
        response = client.chat.completions.create(
            model=model,
            messages=chat_messages,
            max_tokens=max_tokens,
            temperature=0.1
        )
        answer = response.choices[0].message.content

        # Фактчекинг через RAG (только числа и даты)
        facts = re.findall(r'\d{1,4}|\d{1,2}[./-]\d{1,2}[./-]\d{2,4}', answer)
        verified = {}
        for fact in facts:
            context = await rag_system.get_relevant_context(f"{fact} Беларусь")
            verified[fact] = "✅ подтверждено" if "не найдено" not in context.lower() else "⚠️ не подтверждено"


        # Обновляем память пользователя
        if user_id:
            if user_id not in user_memory:
                user_memory[user_id] = {"last_queries": [], "last_entities": {}}

            # Добавляем последнее сообщение
            user_memory[user_id]["last_queries"].append(user_msg)
            if len(user_memory[user_id]["last_queries"]) > 10:
                user_memory[user_id]["last_queries"].pop(0)

            # Простое извлечение сущностей (например, имена, места)
            entity_match = re.findall(r'\b[А-ЯЁ][а-яё]+\b', user_msg)
            if entity_match:
                user_memory[user_id]["last_entities"]["имя"] = entity_match[-1]  # последнее упомянутое слово с заглавной

        return answer

    except Exception as e:
        logger.error(f"AI21 RAG error: {e}")
        return "🔍 Произошла ошибка при генерации или проверке информации."

async def close_rag_system():
    await rag_system.close()
