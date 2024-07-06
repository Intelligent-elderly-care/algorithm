from fastapi import FastAPI, Request, Response
import uvicorn
import time
import asyncio
from concurrent.futures import ThreadPoolExecutor

# 创建Web
app = FastAPI()

# 创建线程池
threadpool = ThreadPoolExecutor(max_workers=200)

@app.get('/ver2')
async def ver2(request: Request):
    # 获取参数
    msg = request.query_params.get('msg')

    # 获取async io event loop
    loop = asyncio.get_event_loop()

    # 准备计算任务
    task = {
        'msg':msg,
    }

    # 计算函数
    def handle_task():
        print('task recived:',task['msg'])
        result = task['msg'].lower()

        return result
    
    # 提交并等待结果
    result = await loop.run_in_executor(threadpool, handle_task)
    print('task ends:',result,asyncio.get_event_loop)
    return Response(result)

if __name__ == '__main__':
    uvicorn.run(app, host='localhost', port=8000) # asyncio(linux epoll)