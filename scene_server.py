import asyncio
import os
import cv2
import aiohttp.web
import numpy as np
import threading
from io import StringIO, BytesIO
import asyncio
from aiohttp import web
import detector
import subprocess
import json
import matplotlib.pyplot as plt

HOST = os.getenv('HOST', '0.0.0.0')
PORT = int(os.getenv('PORT', 8080))
img = None
new_image = False
ws = None
resolution = (180, 320, 4)
resolution_pord = resolution[0] * resolution[1]* resolution[0]
# resolution = (180, 320, 4)
# resolution = (720, 1280, 4)

async def mjpghandler(request):
    global img
    global new_image
    interval = 1
    print("Redirect to MJPEG local host")

    resp = aiohttp.web.StreamResponse()
    resp.content_type = ('multipart/x-mixed-replace; '
                         'boundary=--jpegboundary')
    await resp.prepare(request)
    data = {}

    while True:
        try:
            if new_image and interval % 10 == 0:
            # img = cv2.imdecode(np.fromstring(img, dtype=np.uint8), -1)

                curr_img = np.fromstring(img, dtype=np.uint8).reshape(resolution)[:,:,0:3]
                curr_img = cv2.resize(curr_img,(int(320),int(240)))
                print(curr_img.shape)

                res_image, data = detector.detect(curr_img)

                ret, res_image = cv2.imencode('.jpg', res_image)
                res_image = res_image.tobytes()

                await resp.write(bytes(
                    '--jpegboundary\r\n'
                    'Content-Type: image/jpeg\r\n'
                    'Content-Length: {}\r\n\r\n'.format(len(res_image)), 'utf-8') + res_image + b'\r\n')

                new_image = False
                interval = 0

            await  asyncio.sleep(.000000001)
            interval += 1
        except Exception as e:
            # So you can observe on disconnects and such.
            print(e)
            raise
    return resp


async def testhandle(request):
    resp = aiohttp.web.Response(
        status=200, headers={'Content-Type': 'text/html'})
    await resp.prepare(request)
    await resp.write(b'<html><head></head><body>')
    await resp.write(b'<img src="http://127.0.0.1:8080/mjpg"/>')
    await resp.write(b'</body></html>')
    await resp.drain()

    return resp


async def defaulthandle(request):
    return aiohttp.web.Response(text="Hello World")


async def websocket_handler(request):
    global img
    global new_image
    global ws

    print('Websocket connection starting')
    ws = aiohttp.web.WebSocketResponse()
    await ws.prepare(request)
    print('Websocket connection ready')
    await ws.send_str("welp")
    async for msg in ws:
        if msg.type == aiohttp.WSMsgType.BINARY:
            bytes = msg.data
            try:
                img = bytes
                new_image = True
            except:
                print("gg")

    print('Websocket connection closed')
    return ws


async def websocket_mask_handler(request):
    print('Websocket connection starting')
    ws = aiohttp.web.WebSocketResponse()
    await ws.prepare(request)
    print('Websocket connection readyyyyyyyyyyyyyy')
    data = {}
    await ws.send_str("Start")
    async for msg in ws:
        if msg.type == aiohttp.WSMsgType.BINARY:
            img = msg.data
            curr_img = np.fromstring(img, dtype=np.uint8).reshape(resolution)[:,:,:3]
            res_image, r = detector.detect(curr_img)
            for k, v in r.items():
                data[k] = v.tolist()
            json_string = json.dumps(data)
            await ws.send_str(json_string)

                

    print('Websocket connection closed')
    return ws



def main():
    loop = asyncio.get_event_loop()
    app = aiohttp.web.Application(loop=loop)
    app.router.add_route('GET', '/hello', defaulthandle)
    app.router.add_route('GET', '/', testhandle)
    app.router.add_route('GET', '/mjpg', mjpghandler)
    app.router.add_route('GET', '/ws', websocket_handler)
    app.router.add_route('GET', '/ws_mask', websocket_mask_handler)
    aiohttp.web.run_app(app, host=HOST, port=PORT)


if __name__ == '__main__':
    detector.load_model()
    main()
