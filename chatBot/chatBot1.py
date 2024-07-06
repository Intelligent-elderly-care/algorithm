import openai
import os
import gradio as gr
from langchain_community.chat_models import ChatOpenAI
from langchain.chains import ConversationChain
from langchain.memory import ConversationSummaryBufferMemory
import pyttsx3
import threading
import hashlib
import hmac
import base64
import json
import time
import pyaudio
from websocket import create_connection
from urllib.parse import quote
import logging
import websocket

# Initialize OpenAI API
os.environ["OPENAI_API_KEY"] = "1f03a3f84ab5b311a52af51aa00b2fb9.VMD0UYN2N5Ps9358"
openai.api_key = os.environ["OPENAI_API_KEY"]

# Initialize memory and conversation
memory = ConversationSummaryBufferMemory(llm=ChatOpenAI(), max_token_limit=1024)
conversation = ConversationChain(
    llm=ChatOpenAI(
        temperature=0.95,
        max_tokens=2048,
        model="glm-4-flash",
        openai_api_base="https://open.bigmodel.cn/api/paas/v4/"
    ),
    memory=memory,
)

# Global variables
recording = False
client = None  # Global variable to hold Client instance
history = []

# Initialize pyttsx3 engine
def play_audio(response):
    engine = pyttsx3.init()
    engine.say(response)
    engine.runAndWait()

def predict(input, history=[]):
    if not input.strip():
        return gr.update(value="您的输入为空，请重新输入！"), history
    
    history.append(input)
    try:
        response = conversation.predict(input=input)
        history.append(response)
        
        # Start a new thread to play the audio
        threading.Thread(target=play_audio, args=(response,)).start()
        
        responses = [(u, b) for u, b in zip(history[::2], history[1::2])]
        return responses, history
    except Exception as e:
        return gr.update(value="暂时遇到了一点问题，请重新发送！"), history

# Initialize ASR client
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
        self.transcript = []
        self.last_text_time = time.time()

    def send(self, audio_data):
        self.ws.send(audio_data)

    def recv(self):
        try:
            while self.ws.connected:
                result = str(self.ws.recv())
                if len(result) == 0:
                    break
                result_dict = json.loads(result)

                if result_dict["action"] == "result":
                    result_1 = result_dict
                    text = ''.join([word['cw'][0]['w'] for word in json.loads(result_1["data"])['cn']['st']['rt'][0]['ws']])
                    print("text:" + text)
                    self.transcript.append(text)
                    if text.strip():
                        self.last_text_time = time.time()
                
                if result_dict["action"] == "error":
                    self.ws.close()
                    return
        except websocket.WebSocketConnectionClosedException:
            pass

    def close(self):
        if self.ws.connected:
            self.ws.send(bytes(self.end_tag.encode('utf-8')))
            self.ws.close()
        return ''.join(self.transcript)

# Function to handle voice input
def handle_voice_input():
    global recording, client
    app_id = "fe3506b5"
    api_key = "2d473887b44f3e6e10f6fac2a7503b50"
    client = Client(app_id, api_key)  # Save Client instance globally
    recording = True
    threading.Thread(target=record_and_send_audio, args=(client,)).start()

def stop_voice_input():
    global recording, client, history
    recording = False

    # Get the transcribed text from the saved Client instance
    if client:
        text = client.close()
        print("responseText:" + text)
        if text:
            responses, history = predict(text, history)
            print(f'responses: {responses}')
            return responses, history
        else:
            return gr.update(value="听不到您的声音，请重新录音！"), []
    else:
        return gr.update(value="听不到您的声音，请重新录音！"), []

def record_and_send_audio(client):
    global recording
    CHUNK = 1280
    FORMAT = pyaudio.paInt16
    CHANNELS = 1
    RATE = 16000

    p = pyaudio.PyAudio()
    stream = p.open(format=FORMAT, channels=CHANNELS, rate=RATE, input=True, frames_per_buffer=CHUNK)

    print("Recording...")

    while recording:
        data = stream.read(CHUNK)
        client.send(data)
        if time.time() - client.last_text_time > 3:
            recording = False
            # raise gr.Error("听不到您的声音，请重新录音！")
            gr.Warning("听不到您的声音，请重新录音！")
            break
        time.sleep(0.04)

    text = client.close()
    stream.stop_stream()
    stream.close()
    p.terminate()
    print("Recording stopped text:" + text)
    if text:
        return text
    else:
        # gr.Info("您的输入为空,请重新输入!")
        raise gr.Error("您的输入为空,请重新输入!")

with gr.Blocks(css="""
#chatbot {height: 100vh; overflow-y: auto;}
.custom-button {height: 50px; width: 150px; display: inline-block;}
.custom-button img {height: 20px; width: 20px; vertical-align: middle; margin-right: 5px;}
.custom-textbox {display: flex; align-items: center;}
.custom-textbox input {flex-grow: 1;}
.custom-textbox img {height: 20px; width: 20px; vertical-align: middle; margin-right: 5px;}
.user-avatar, .bot-avatar {height: 30px; width: 30px; border-radius: 50%; display: inline-block; margin-right: 5px;}
.user-avatar {background-image: url('./avatars/chatBot.png');}
.bot-avatar {background-image: url('./avatars/elderly.png');}
""") as demo:
    chatbot = gr.Chatbot(elem_id="聊天机器人")
    state = gr.State([])

    with gr.Row():
        txt = gr.Textbox(show_label=False, placeholder="请您输入文字...", elem_classes="custom-textbox")
        voice_btn = gr.Button("开始录音", elem_classes="custom-button")
        stop_btn = gr.Button("停止录音", elem_classes="custom-button")

    # 清空输入框 
    def clear_text():
        return ""
    
    def on_submit(input, state):
        responses, updated_state = predict(input, state)
        return responses, updated_state, clear_text()
    
    txt.submit(on_submit, [txt, state], [chatbot, state, txt])
    voice_btn.click(handle_voice_input)
    stop_btn.click(stop_voice_input, outputs=[chatbot, state])

demo.launch()
