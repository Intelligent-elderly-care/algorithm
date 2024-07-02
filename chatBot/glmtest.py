# -*- encoding:utf-8 -*-
import hashlib
import hmac
import base64
import json
import time
import threading
import pyaudio
from websocket import create_connection
from urllib.parse import quote
import logging
import websocket
import openai
import gradio as gr
from langchain_community.chat_models import ChatOpenAI
from langchain.chains import ConversationChain
from langchain.memory import ConversationSummaryBufferMemory
import pyttsx3
import os

# 配置OpenAI API
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

# 模型回复
def predict(input, history=[]):
    # 当用户输入为空时，做一些提示
    if not input.strip():
        return "请输入一些文字.", history
    
    history.append(input)
    response = conversation.predict(input=input)
    history.append(response)
    
    # 启动新线程播放语音
    threading.Thread(target=play_audio, args=(response,)).start()
    
    responses = [(u, b) for u, b in zip(history[::2], history[1::2])]
    return responses, history

# 语音转写服务端
class Client():
    def __init__(self, app_id, api_key):
        base_url = "ws://rtasr.xfyun.cn/v1/ws"
        ts = str(int(time.time()))
        tt = (app_id + ts).encode('utf-8')
        md5 = hashlib.md5()
        md5.update(tt)
        baseString = md5.hexdigest()
        baseString = bytes(baseString, encoding='utf-8')

        apiKey = api_key.encode('utf-8')
        signa = hmac.new(apiKey, baseString, hashlib.sha1).digest()
        signa = base64.b64encode(signa)
        signa = str(signa, 'utf-8')
        self.end_tag = "{\"end\": true}"

        self.ws = create_connection(base_url + "?appid=" + app_id + "&ts=" + ts + "&signa=" + quote(signa))
        self.trecv = threading.Thread(target=self.recv)
        self.trecv.start()
        self.transcription = ""

    def send(self, audio_data):
        self.ws.send(audio_data)

    def recv(self):
        try:
            while self.ws.connected:
                result = str(self.ws.recv())
                if len(result) == 0:
                    print("receive result end")
                    break
                result_dict = json.loads(result)
                
                action = result_dict.get("action")
                if action == "started":
                    print("Handshake success, result: " + result)
                
                elif action == "result":
                    data_cn = result_dict.get("cn", {}).get("st", {}).get("rt", [])
                    if data_cn:
                        for rt in data_cn:
                            ws = rt.get("ws", [])
                            for cw in ws:
                                word = cw.get("w")
                                print("RTASR result: " + word)
                                self.transcription += word
                
                elif action == "error":
                    print("RTASR error: " + result)
                    self.ws.close()
                    return
        except websocket.WebSocketConnectionClosedException:
            print("Receive result end")

    def close(self):
        self.ws.send(bytes(self.end_tag.encode('utf-8')))
        print("send end tag success")
        self.ws.close()
        print("connection closed")

# 录音并发送音频
def record_and_send_audio(client, stop_event):
    CHUNK = 1280
    FORMAT = pyaudio.paInt16
    CHANNELS = 1
    RATE = 16000

    p = pyaudio.PyAudio()

    stream = p.open(format=FORMAT,
                    channels=CHANNELS,
                    rate=RATE,
                    input=True,
                    frames_per_buffer=CHUNK)

    print("正在录音...")

    try:
        while not stop_event.is_set():
            data = stream.read(CHUNK)
            client.send(data)
            time.sleep(0.04)  # 这里控制发送的频率
    except KeyboardInterrupt:
        print("录音结束!")
        client.close()

    stream.stop_stream()
    stream.close()
    p.terminate()

    client.close()

def start_recording():
    app_id = "fe3506b5"
    api_key = "2d473887b44f3e6e10f6fac2a7503b50"
    global stop_event, client, recording_thread
    stop_event.clear()
    client = Client(app_id, api_key)
    recording_thread = threading.Thread(target=record_and_send_audio, args=(client, stop_event))
    recording_thread.start()

def stop_recording():
    global stop_event, recording_thread
    stop_event.set()
    recording_thread.join()
    transcription = client.transcription
    return transcription, transcription

# 初始化事件
stop_event = threading.Event()

# 配置Gradio界面
with gr.Blocks(css="#chatbot{height:800px} .overflow-y-auto{height:800px}") as demo:
    chatbot = gr.Chatbot(elem_id="chatbot")
    state = gr.State([])

    with gr.Row():
        txt = gr.Textbox(show_label=False, placeholder="请输入文字...")
        start_button = gr.Button("开始录音")
        stop_button = gr.Button("停止录音")

    txt.submit(predict, [txt, state], [chatbot, state])
    start_button.click(fn=start_recording, inputs=[], outputs=[])
    stop_button.click(fn=stop_recording, inputs=[], outputs=[txt, state])

demo.launch()
