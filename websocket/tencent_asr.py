#! /usr/bin env python3
# -*- coding: utf-8 -*-
"""
实时流式识别
需要安装websocket-client库: pip3 install websocket-client
使用方式 python tencent_asr.py
"""
import base64
import datetime
import hashlib
import hmac
import ssl
import urllib
import websocket
import threading
import time
import json
import logging
import sys


# if len(sys.argv) < 2:
#     file_name = "audio/16k.pcm"
# else:
#     file_name = sys.argv[1]


logger = logging.getLogger()

"""

1. 连接 ws_app.run_forever()
2. 连接成功后发送数据 on_open()
2.1 发送开始参数帧 send_start_params()
2.2 发送音频数据帧 send_audio()
2.3 库接收识别结果 on_message()
2.4 发送结束帧 send_finish()
3. 关闭连接 on_close()

库的报错 on_error()
"""


def create_url():
    """
    生成websocket url
    :return request url:
    """
    timestamp = int(round(time.time()))
    print(timestamp)
    AppKey = ""
    AccessToken = ""
    try:
        url = 'wss://gw.tvs.qq.com/ws/ai/asr'
        # 私有化场景请使用ws协议：ws://192.168.1.2:8080/ws/ai/asr
        signature_origin = "appkey=" + AppKey + "&timestamp=" + str(timestamp)
        print(signature_origin)
        # 进行hmac-sha256进行加密
        signature_sha = hmac.new(AccessToken.encode('utf-8'), signature_origin.encode('utf-8'),
                                 digestmod=hashlib.sha256).digest()
        signature_sha = base64.b64encode(signature_sha)
        print("sign:", signature_sha)
        # 将请求的鉴权参数组合为字典
        v = {
            "appkey": AppKey,
            "timestamp": timestamp,
            "signature": signature_sha
        }
        # 拼接鉴权参数，生成url
        url = url + '?' + urllib.parse.urlencode(v)
        print("Request Url is " + url)
        return url
    except Exception as e:
        print("Create Url error ", e)


def send_start_params(ws):
    """
    开始参数帧
    :param websocket.WebSocket ws:
    :return:
    """
    req = {
        "type": "start",
        "data": {
                "engineType": "yxw",
                "format": "pcm",
                "sampleRate": "16K",
                "channel": 1,
                "domain": 400,
                "useCloudVad": False,
                "vadThreshold": 500
        }
    }
    body = json.dumps(req)
    ws.send(body, websocket.ABNF.OPCODE_TEXT)
    logger.info("send START frame with params:" + body)


def send_audio(ws):
    """
    发送二进制音频数据，注意每个帧之间需要有间隔时间
    :param  websocket.WebSocket ws:
    :return:
    """
    file_name = "audio/16k.pcm"
    chunk_ms = 160  # 160ms的录音
    chunk_len = int(16000 * 2 / 1000 * chunk_ms)
    with open(file_name, 'rb') as f:
        pcm = f.read()

    index = 0
    total = len(pcm)
    logger.info("send_audio total={}".format(total))
    while index < total:
        end = index + chunk_len
        if end >= total:
            # 最后一个音频数据帧
            end = total
        body = pcm[index:end]
        logger.debug("try to send audio length {}, from bytes [{},{})".format(len(body), index, end))
        ws.send(body, websocket.ABNF.OPCODE_BINARY)
        index = end
        time.sleep(chunk_ms / 1000.0)

    # for i in range(10):
    #     print(i)
    #     body = pcm[0:129600]
    #     ws.send(body, websocket.ABNF.OPCODE_BINARY)
    #     time.sleep(chunk_ms / 1000.0)



def send_finish(ws):
    """
    发送结束帧
    :param websocket.WebSocket ws:
    :return:
    """
    req = {
        "type": "end"
    }
    body = json.dumps(req)
    ws.send(body, websocket.ABNF.OPCODE_TEXT)
    logger.info("send FINISH frame")


def on_open(ws):
    """
    连接后发送数据帧
    :param  websocket.WebSocket ws:
    :return:
    """

    def run(*args):
        """
        发送数据帧
        :param args:
        :return:
        """
        send_start_params(ws)
        send_audio(ws)
        send_finish(ws)
        logger.debug("thread terminating")

    threading.Thread(target=run).start()


def on_message(ws, message):
    """
    接收服务端返回的消息
    :param ws:
    :param message: json格式，自行解析
    :return:
    """
    if isinstance(type(message), bytes):
        json_message = json.loads(message.decode("UTF-8"))
    else:
        json_message = json.loads(message)
    logger.info(json_message)
    if json_message['header']['code'] != 200:
        print(str(datetime.datetime.now()) + '>>> error info >>> ' + str(message))
        d = {"type": "end"}
        ws.send(json.dumps(d))


def on_error(ws, error):
    """
    库的报错，比如连接超时
    :param ws:
    :param error: json格式，自行解析
    :return:
    """
    logger.error(str(datetime.datetime.now()) + " >>> on_error >>> " + str(error))
    ws.close


def on_close(ws, close_status_code, close_msg):
    """
    Websocket关闭
    :param websocket.WebSocket ws:
    :return:
    """
    logger.info("----------------------------------WebScoket Closed----------------------------------")
    ws.close()


if __name__ == "__main__":
    logging.basicConfig(format='[%(asctime)-15s] [%(funcName)s()][%(levelname)s] %(message)s')
    logger.setLevel(logging.DEBUG)  # 调整为logging.INFO，日志会少一点
    logger.info("----------------------------------Websocket Started----------------------------------")

    websocket.enableTrace(False)
    uri = create_url()
    ws_app = websocket.WebSocketApp(uri,
                                    on_open=on_open,  # 连接建立后的回调
                                    on_message=on_message,  # 接收消息的回调
                                    on_error=on_error,  # 库遇见错误的回调
                                    on_close=on_close)  # 关闭后的回调
    ws_app.run_forever(sslopt={"cert_reqs": ssl.CERT_NONE, "check_hostname": False}, ping_interval=0.01)
