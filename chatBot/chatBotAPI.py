import openai
import os
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from langchain_community.chat_models import ChatOpenAI
from langchain.chains import ConversationChain
from langchain.memory import ConversationSummaryBufferMemory
import pyttsx3
import threading
from typing import List, Tuple, Optional
from pymongo import MongoClient
from bson.objectid import ObjectId

# 配置OpenAI API密钥
os.environ["OPENAI_API_KEY"] = "1f03a3f84ab5b311a52af51aa00b2fb9.VMD0UYN2N5Ps9358"
openai.api_key = os.environ["OPENAI_API_KEY"]

# 初始化语言模型和对话链
memory = ConversationSummaryBufferMemory(llm=ChatOpenAI(), max_token_limit=2048)
conversation = ConversationChain(
    llm=ChatOpenAI(
        temperature=0.3,
        max_tokens=2048,
        model="glm-4-flash",
        openai_api_base="https://open.bigmodel.cn/api/paas/v4/"
    ),
    memory=memory,
)

# 初始化pyttsx3引擎
engine = pyttsx3.init()

def play_audio(response):
    engine.say(response)
    engine.runAndWait()

# FastAPI应用实例
app = FastAPI()

# MongoDB配置
mongo_client = MongoClient("mongodb://root:GJyg6841!@127.0.0.1:27017/")
db = mongo_client["chatHistory"]
conversations_collection = db["conversations"]

# Pydantic模型
class PredictRequest(BaseModel):
    user_id: str
    input: str

class PredictResponse(BaseModel):
    responses: List[Tuple[str, str]]
    history: List[str]

@app.post("/predict", response_model=PredictResponse)
async def predict(request: PredictRequest):
    user_id = request.user_id
    input_text = request.input

    # 从数据库中检索用户的对话历史
    conversation_record = conversations_collection.find_one({"user_id": user_id})
    if conversation_record:
        history = conversation_record["history"]
    else:
        history = []

    history.append(input_text)
    try:
        response = conversation.predict(input=input_text)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error generating response: {str(e)}")
    
    history.append(response)
    
    # 启动新线程播放语音
    threading.Thread(target=play_audio, args=(response,)).start()

    # 更新数据库中的对话历史
    if conversation_record:
        conversations_collection.update_one({"user_id": user_id}, {"$set": {"history": history}})
    else:
        conversations_collection.insert_one({"user_id": user_id, "history": history})

    responses = [(u, b) for u, b in zip(history[::2], history[1::2])]
    return PredictResponse(responses=responses, history=history)

# 运行FastAPI应用
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
