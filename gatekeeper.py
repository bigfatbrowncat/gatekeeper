#!/usr/bin/python3.7

import aiohttp
from aiohttp import web, WSCloseCode
import asyncio
import typing as t
import logging

logging.basicConfig(level=logging.DEBUG)

hostName = "0.0.0.0"
serverPort = 8080

CONFIG_PATH = "gatekeeper.conf"


class ConfigReader:
    STATUS_READ_SUCCESSFULLY = 0
    STATUS_NOT_FOUND = 1
    STATUS_EMPTY = 2
    STATUS_CAN_NOT_CREATE = 3

    def __init__(self):
        try:
            with open(CONFIG_PATH, 'r') as f:
                self.__ip = f.readline()
                if self.__ip is None or self.__ip == '':
                    self.__ip = None
                    self.__status = ConfigReader.STATUS_EMPTY
                else:
                    self.__status = ConfigReader.STATUS_READ_SUCCESSFULLY
        except FileNotFoundError as e:
            self.__ip = None
            try:
                with open(CONFIG_PATH, 'w') as f:
                    f.write('')
                self.__status = ConfigReader.STATUS_NOT_FOUND
            except PermissionError:
                self.__status = ConfigReader.STATUS_CAN_NOT_CREATE

    def status(self):
        return self.__status


# Globals
configReader: ConfigReader

HTML_DOCTYPE = '<!DOCTYPE HTML PUBLIC "-//W3C//DTD HTML 4.01//EN" "http://www.w3.org/TR/html4/strict.dtd">'
HTML_META = '<meta http-equiv="Content-Type" content="text/html;charset=utf-8">'
CSS = '''
body { font-family: sans-serif; margin: auto; max-width: 600pt; padding: 20pt; }
h1 { text-size: 200%; }
'''


def get_no_permission_page(request: aiohttp.web.Request):
    response = f'''{HTML_DOCTYPE}
    <html>
        <head>
            {HTML_META}
            <title>The Gatekeeper</title>
            <style>{CSS}</style>
        </head>
        <body>
            <h1>Gatekeeper can not proceed!</h1>
            <p>The Gatekeeper has no writing access to its configuration file: <code>{CONFIG_PATH}</code>. Please stop the server and grant it the proper permissions</p>
        </body>
    </html>
    '''

    return response


def get_welcome_page(request: aiohttp.web.Request):
    # A bit of magic
    server_ip = request.transport._sock.getsockname()[0]

    response = f'''{HTML_DOCTYPE}
    <html>
        <head>
            {HTML_META}
            <title>The Gatekeeper</title>
            <style>{CSS}</style>
        </head>
        <body>
            <h1>Welcome to the Gatekeeper!</h1>
            <p>The server can not find its configuration file at <code>{CONFIG_PATH}</code> or the file is empty. We have to configure the Gatekeeper.</p>
            <p>The server was reached at IP <code>{server_ip}</code>. May we assume this IP address to be the client network address? If not, open the Gatekeeper page from the client network.</p>
        </body>
    </html>
    '''
    return response


async def http_handler(request: aiohttp.web.Request):
    if configReader.status() == ConfigReader.STATUS_CAN_NOT_CREATE:
        page = get_no_permission_page(request)
    elif configReader.status() == ConfigReader.STATUS_NOT_FOUND or configReader.status() == ConfigReader.STATUS_EMPTY:
        page = get_welcome_page(request)
    else:
        page = "Done"

    return  web.Response(
        text=page,
        status=200,
        headers={"Content-type": "text/html"}
    )


async def websocket_handler(request):
    ws = web.WebSocketResponse()
    await ws.prepare(request)

    async for msg in ws:
        if msg.type == aiohttp.WSMsgType.TEXT:
            if msg.data == 'close':
                await ws.close()
            else:
                await ws.send_str('some websocket message payload')
        elif msg.type == aiohttp.WSMsgType.ERROR:
            print('ws connection closed with exception %s' % ws.exception())

    return ws


def create_runner():
    app = web.Application()
    app.add_routes([
        web.get('/',   http_handler),
        web.get('/ws', websocket_handler),
    ])
    return web.AppRunner(app)


async def start_server(host=hostName, port=serverPort):
    global configReader
    configReader = ConfigReader()

    runner = create_runner()
    await runner.setup()
    site = web.TCPSite(runner, host, port)
    await site.start()
    logging.info('Serving on http://%s:%s' % site._server.sockets[0].getsockname())
    return site


async def stop_server(site: web.TCPSite):
    await site.stop()
    logging.log(logging.INFO, "Server stopped")

if __name__ == "__main__":
    loop = asyncio.get_event_loop()
    site = loop.run_until_complete(start_server())

    try:
        loop.run_forever()
    except KeyboardInterrupt:
        pass

    loop.run_until_complete(stop_server(site))
