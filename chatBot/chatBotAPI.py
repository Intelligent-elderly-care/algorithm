import asyncio
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import List, Tuple
from motor.motor_asyncio import AsyncIOMotorClient
from concurrent.futures import ThreadPoolExecutor
from langchain_community.chat_models import ChatOpenAI
from langchain.chains import ConversationChain
from langchain.memory import ConversationSummaryBufferMemory
import os
import openai
import uvicorn

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

# FastAPI应用实例
app = FastAPI()

# MongoDB配置
mongo_client = AsyncIOMotorClient("mongodb://root:GJyg6841!@127.0.0.1:27017/")
db = mongo_client["chatHistory"]
conversations_collection = db["conversations"]

# 最大并发数
max_concurrent_requests = 5
semaphore = asyncio.Semaphore(max_concurrent_requests)

# 线程池
threadpool = ThreadPoolExecutor(max_workers=5)

# Pydantic模型
class PredictRequest(BaseModel):
    user_id: str
    input: str

class PredictResponse(BaseModel):
    responses: List[Tuple[str, str]]
    history: List[str]

async def predict_response(input_text):
    retry_count = 3
    for _ in range(retry_count):
        try:
            async with semaphore:
                response = await asyncio.get_event_loop().run_in_executor(threadpool, lambda: conversation.predict(input=input_text))
            return response
        except Exception as e:
            await asyncio.sleep(1)
    raise HTTPException(status_code=500, detail="Error generating response after retries")

@app.post("/predict", response_model=PredictResponse)
async def predict(request: PredictRequest):
    user_id = request.user_id
    input_text = request.input

    conversation_record = await conversations_collection.find_one({"user_id": user_id})
    if conversation_record:
        history = conversation_record["history"]
    else:
        history = []

    history.append(input_text)
    try:
        response = await predict_response(input_text)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error generating response: {str(e)}")
    
    history.append(response)

    if conversation_record:
        await conversations_collection.update_one({"user_id": user_id}, {"$set": {"history": history}})
    else:
        await conversations_collection.insert_one({"user_id": user_id, "history": history})

    responses = [(u, b) for u, b in zip(history[::2], history[1::2])]
    return PredictResponse(responses=responses, history=history)

# 运行FastAPI应用
if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
