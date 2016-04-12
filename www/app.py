#!/usr/bin/env python3
# -*- coding: utf-8 -*-

''

__author__ = 'Engine' 

import logging

# 设置日志等级,默认为WARNING.只有指定级别或更高级的才会被追踪记录
logging.basicConfig("logfile", level=logging.INFO) 

import asyncio, os, json, time
from datetime import datetime

from aiohttp import web

# 对根目录请求的处理函数
def index(request):
    return web.Response(body=b"<h1>To be Awesome.</h1>")

# 初始化协程
@asyncio.coroutine
def init(loop):
    app = web.Application(loop = loop) # 创建一个循环类型是消息循环的web应用对象
    app.router.add_route("GET", '/', index) # 为"/"路径的"GET"请求添加处理,处理函数为index
    # 调用子协程:创建一个TCP服务器,绑定到"127.0.0.1:9000"socket,并返回一个服务器对象
    srv = yield from loop.create_server(app.make_handler(), "127.0.0.1", 9000)
    logging.info("server started at http://127.0.0.1:9000")
    return srv

loop = asyncio.get_event_loop() # loop是一个消息循环对象
loop.run_until_complete(test(loop)) #在消息循环中执行协程
loop.run_forever()
