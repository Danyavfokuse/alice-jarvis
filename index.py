from flask import Flask, request, jsonify
import google.generativeai as genai
from duckduckgo_search import DDGS
import os

app = Flask(__name__)

# Подключаем ключ Gemini из переменных окружения
genai.configure(api_key=os.environ.get("GEMINI_API_KEY"))

# Используем быструю модель для голосовых ответов
model = genai.GenerativeModel('gemini-1.5-flash')

def search_web(query):
    """Быстрый поиск свежей информации"""
    try:
        results = DDGS().text(query, max_results=3)
        if results:
            return "\n".join([f"- {r['title']}: {r['body']}" for r in results])
        return "Нет результатов поиска."
    except Exception:
        return "Ошибка поиска."

@app.route('/api', methods=['POST', 'GET', 'HEAD'])
@app.route('/api/', methods=['POST', 'GET', 'HEAD'])
@app.route('/', methods=['POST', 'GET', 'HEAD'])
def webhook():
    if request.method in ['GET', 'HEAD']:
        return "Сервер Джарвиса успешно запущен и готов к работе!", 200
        
    data = request.json or {}

    # Запрос от Алисы
    user_message = data.get('request', {}).get('original_utterance', '')
    
    # История из хранилища Яндекса (session_state)
    session_state = data.get('state', {}).get('session', {})
    history = session_state.get('history', [])
    
    # Если запуск навыка без вопроса
    if not user_message:
        return jsonify({
            "response": {
                "text": "Джарвис на связи. Что ищем сегодня?",
                "end_session": False
            },
            "version": "1.0"
        })

    # Базовый триггер: ищем в сети, если есть ключевые слова
    search_keywords = ['найди', 'новости', 'погода', 'что такое', 'кто такой', 'курс', 'сегодня']
    search_results = ""
    if any(word in user_message.lower() for word in search_keywords):
        search_results = search_web(user_message)
        
    # Формируем промпт для модели
    messages = [{"role": "user", "parts": ["Ты голосовой ассистент Джарвис. Отвечай кратко и естественно, так как тебя будут слушать, а не читать. "
                                         "Если ниже есть результаты поиска, используй их для ответа.\n"
                                         f"Результаты поиска: {search_results}"]}]
    
    # Добавляем контекст (последние 4 реплики)
    for msg in history[-4:]:
        messages.append({"role": msg['role'], "parts": [msg['text']]})
        
    messages.append({"role": "user", "parts": [user_message]})
    
    try:
        response = model.generate_content(messages)
        bot_reply = response.text.strip()
    except Exception:
        bot_reply = "Связь с сервером потеряна."

    # Ограничение Яндекса на длину текста (не более 1024 символов)
    bot_reply = bot_reply[:1024]

    # Сохраняем ход партии (обновляем историю диалога)
    history.append({"role": "user", "text": user_message})
    history.append({"role": "model", "text": bot_reply})

    # Отправляем ответ обратно в Алису
    return jsonify({
        "response": {
            "text": bot_reply,
            "end_session": False
        },
        "session_state": {
            "history": history
        },
        "version": "1.0"
    })