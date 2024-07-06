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
                if result_dict["action"] == "started":
                    print("handshake success, result: " + result)

                if result_dict["action"] == "result":
                    result_1 = result_dict
                    print("rtasr result: " + result_1["data"])
                    text = ''.join([word['cw'][0]['w'] for word in json.loads(result_1["data"])['cn']['st']['rt'][0]['ws']])
                    return text

                if result_dict["action"] == "error":
                    print("rtasr error: " + result)
                    self.ws.close()
                    return
        except websocket.WebSocketConnectionClosedException:
            print("receive result end")

    def close(self):
        self.ws.send(bytes(self.end_tag.encode('utf-8')))
        print("send end tag success")
        self.ws.close()
        print("connection closed")

def record_and_send_audio(client):
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

    print("Recording...")

    try:
        while True:
            data = stream.read(CHUNK)
            client.send(data)
            time.sleep(0.04)  # 这里控制发送的频率
    except KeyboardInterrupt:
        print("Recording stopped")
        client.close()

    stream.stop_stream()
    stream.close()
    p.terminate()

if __name__ == '__main__':
    logging.basicConfig()

    app_id = "fe3506b5"
    api_key = "2d473887b44f3e6e10f6fac2a7503b50"

    client = Client(app_id, api_key)
    record_and_send_audio(client)
