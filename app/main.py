import httpx
import os
from fastapi import FastAPI, Request
from langchain_groq import ChatGroq

app = FastAPI()

# Configurações via variáveis de ambiente
OLLAMA_URL = "http://host.docker.internal:11434/api/generate"
GROQ_KEY = os.getenv("GROQ_API_KEY")
WAHA_URL = "http://waha:3000/api/sendText"

async def get_ai_answer(prompt: str):
    # 1. Tenta o Ollama Local
    try:
        async with httpx.AsyncClient(timeout=40.0) as client:
            res = await client.post(
                OLLAMA_URL,
                json={"model": "llama3", "prompt": prompt, "stream": False}
            )
            if res.status_code == 200:
                return res.json().get("response")
    except Exception as e:
        print(f"Ollama offline: {e}")

    # 2. Se falhar, vai para a Groq
    if GROQ_KEY:
        print("Usando Groq...")
        llm = ChatGroq(groq_api_key=GROQ_KEY, model_name="llama3-8b-8192")
        response = llm.invoke(prompt)
        return response.content
    
    return "Desculpe, estou com dificuldades técnicas agora."

async def send_to_whatsapp(chat_id: str, text: str):
    async with httpx.AsyncClient() as client:
        payload = {
            "chatId": chat_id,
            "text": text,
            "session": "default"
        }
        await client.post(WAHA_URL, json=payload)

@app.post("/webhook")
async def webhook(request: Request):
    data = await request.json()
    
    # O WAHA envia o evento 'message.upsert' ou similar
    payload = data.get("payload", {})
    message_body = payload.get("body")
    chat_id = payload.get("from") # ID do usuário (ex: 55119... @c.us)

    if message_body and not payload.get("fromMe"):
        print(f"Mensagem recebida: {message_body}")
        answer = await get_ai_answer(message_body)
        await send_to_whatsapp(chat_id, answer)

    return {"status": "ok"}