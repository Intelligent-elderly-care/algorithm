import openai, os
import gradio as gr
import speech_recognition as sr
from gtts import gTTS
from pydub import AudioSegment
from io import BytesIO
from langchain_community.chat_models import ChatOpenAI
from langchain.chains import ConversationChain
from langchain.memory import ConversationSummaryBufferMemory
from langchain.chat_models import ChatOpenAI

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

def predict(input, history=[]):
    history.append(input)
    response = conversation.predict(input=input)
    history.append(response)
    responses = [(u, b) for u, b in zip(history[::2], history[1::2])]
    return responses, history

def stt(audio):
    recognizer = sr.Recognizer()
    with sr.AudioFile(audio) as source:
        audio_data = recognizer.record(source)
        text = recognizer.recognize_google(audio_data, language="zh-CN")
    return text

def tts(text):
    tts = gTTS(text, lang="zh")
    audio = BytesIO()
    tts.write_to_fp(audio)
    audio.seek(0)
    return audio

def process_audio(audio, history=[]):
    text = stt(audio)
    responses, history = predict(text, history)
    response_text = responses[-1][1]
    audio_response = tts(response_text)
    return responses, history, audio_response

with gr.Blocks(css="#chatbot{height:800px} .overflow-y-auto{height:800px}") as demo:
    chatbot = gr.Chatbot(elem_id="chatbot")
    state = gr.State([])

    with gr.Row():
        txt = gr.Textbox(show_label=False, placeholder="Enter text and press enter")
        audio = gr.Audio(mode="microphone", type="filepath", label="Speak")

    txt.submit(predict, [txt, state], [chatbot, state])
    audio.submit(process_audio, [audio, state], [chatbot, state, audio])

demo.launch()
