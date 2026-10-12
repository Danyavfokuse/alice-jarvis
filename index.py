from flask import Flask, request, jsonify
import google.generativeai as genai
from duckduckgo_search import DDGS
import os
import traceback

app = Flask(__name__)

# Настройка Gemini API
genai.configure(api_key=os.environ.get("GEMINI_API_KEY"))
model = genai.GenerativeModel('gemini-1.5-flash')

def search_web(query):
    try:
        results = DDGS().text(query, max_results=3)
        if results:
            return "\n".join([f"- {r['title']}: {r['body']}" for r in results])
        return "Нет результатов поиска."
    except Exception as e:
        print(f"Search error: {e}")
        return "Ошибка поиска."

@app.route('/api', methods=['POST', 'GET', 'HEAD'])
@app.route('/api/', methods=['POST', 'GET', 'HEAD'])
@app.route('/', methods=['POST', 'GET', 'HEAD'])
def webhook():
    # Логируем любой входящий запрос
    print(f"--- INCOMING REQUEST --- Method: {request.method}")
    
    if request.method in ['GET', 'HEAD']:
        return "Сервер Джарвиса успешно запущен и готов к работе!", 200
        
    try:
        data = request.json or {}
        print(f"Request data: {data}")
        
        user_message = data.get('request', {}).get('original_utterance', '')
        session_state = data.get('state', {}).get('session', {})
        history = session_state.get('history', [])
        
        if not user_message:
            return jsonify({
                "response": {
                    "text": "Джарвис на связи. Что ищем сегодня?",
                    "end_session": False
                },
                "version": "1.0"
            })

        search_keywords = ['найди', 'новости', 'погода', 'что такое', 'кто такой', 'курс', 'сегодня']
        search_results = ""
        if any(word in user_message.lower() for word in search_keywords):
            search_results = search_web(user_message)
            
        messages = [{"role": "user", "parts": ["Ты голосовой ассистент Джарвис. Отвечай кратко и естественно. "
                                             f"Результаты поиска: {search_results}"]}]
        
        for msg in history[-4:]:
            messages.append({"role": msg['role'], "parts": [msg['text']]})
            
        messages.append({"role": "user", "parts": [user_message]})
        
        response = model.generate_content(messages)
        bot_reply = response.text.strip()[:1024]
        
        history.append({"role": "user", "text": user_message})
        history.append({"role": "model", "text": bot_reply})

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
        
    except Exception as e:
        print("CRITICAL ERROR IN WEBHOOK:")
        traceback.print_exc()
        # Возвращаем Яндексу корректный JSON даже при ошибке, чтобы не было падения 500
        return jsonify({
            "response": {
                "text": "Произошла ошибка обработки запроса на сервере.",
                "end_session": False
            },
            "version": "1.0"
        })

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=10000)
