import openai, os
import gradio as gr
from langchain_community.chat_models import ChatOpenAI
from langchain.chains import ConversationChain
from langchain.memory import ConversationSummaryBufferMemory
from langchain.chat_models import ChatOpenAI
import pyttsx3
import threading

os.environ["OPENAI_API_KEY"] = "1f03a3f84ab5b311a52af51aa00b2fb9.VMD0UYN2N5Ps9358"
openai.api_key = os.environ["OPENAI_API_KEY"]

memory = ConversationSummaryBufferMemory(llm=ChatOpenAI(), max_token_limit=2048)
conversation = ConversationChain(
    llm=ChatOpenAI(
        temperature=0.95,
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

def predict(input, history=[]):
    history.append(input)
    response = conversation.predict(input=input)
    history.append(response)
    
    # 启动新线程播放语音
    threading.Thread(target=play_audio, args=(response,)).start()
    
    responses = [(u, b) for u, b in zip(history[::2], history[1::2])]
    print("取出输入：", history[::2])
    print("取出输出：", history[1::2])
    print("组合元组：", responses)
    return responses, history

with gr.Blocks(css="#chatbot{height:800px} .overflow-y-auto{height:800px}") as demo:
    chatbot = gr.Chatbot(elem_id="chatbot")
    state = gr.State([])

    with gr.Row():
        txt = gr.Textbox(show_label=False, placeholder="Enter text and press enter")
        
    txt.submit(predict, [txt, state], [chatbot, state])

demo.launch()
