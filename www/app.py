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
from jinja2 import Environment, FileSystemLoader

import orm
from coroweb imort add_routes, add_static


# 初始化模板
# 选择jinja2作为模板
def init_jinja2(app, **kw):
    logging.info("init jinja2...")
    # 设置jinja2的Environment参数
    options = dict(
        autoescape = kw.get("autoescape", True), # 自动转义xml/html的特殊字符
        block_start_string = kw.get("block_start_string", "{%"), # 代码块开始标志
        block_end_string = kw.get("block_end_string", "%}"),     # 代码块结束标志
        variable_start_string = kw.get("variable_start_string", "{{"), # 变量开始标志
        variable_end_string = kw.get("variable_end_string", "}}"),     # 变量结束标志
        auto_reload = kw.get("auto_reload", True) # 每当对模板发起请求,加载器首先检查模板是否发生改变.若是,则重载模板
        )
    path = kw.get("path", None)  # 获取(模板所在)路径
    if path is None:
        # 若路径不存在,则将当前目录下的templates设为jinja2的目录
        # os.path.abspath(__file__), 返回当前脚本的绝对路径(包括文件名)
        # os.path.dirname(), 去掉文件名,返回目录路径
        # os.path.join(), 将分离的各部分组合成一个路径名
        path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "templates")
    logging.info("set jinja2 template path: %s" % path)
    # 初始化jinja2环境
    # 加载器负责从何处加载模板, 此处选择FileSystemLoader,顾名思义就是从文件系统加载模板
    # options参数,之前已经进行过设置
    env = Environment(loader = FileSystemLoader(path), **options)
    filters = kw.get("filters", None) # 获取过滤器
    if filters is not None:
        # 设置模板的过滤器
        for name, f in filters.items():
            env.filters[name] = f
    app["__templating__"] = env

# 这是一个middleware(中间件), 可以在url处理函数处理之前对url进行处理
# 记录url日志
@asyncio.coroutine
def logger_factory(app, handler):
    @asyncio.coroutine
    def logger(request):
        # 记录日志,包括http method, 和path
        logging.info("Request: %s %s" % (request.method, request.path))
        # 继续处理请求
        return (yield from handler(request))
    return logger

# 解析数据
@asyncio.coroutine
def data_factory(app, handler):
    @asyncio.coroutine
    def parse_data(request):
        if request.method == "POST":
            if request.content_type.startswith("application/json"):
                request.__data__ = yield from request.json()
                logging.info("request json: %s" % str(request.__data__))
            elif request.content_type.startswith("application/x-www-form-urlencoded"):
                request.__data__ = yield from request.post()
                logging.info("request form: %s" % str(request.__data__))
        return (yield from handler(request))
    return parse_data

# 将返回值转换为web.Response对象
@asyncio.coroutine
def repsponse_factory(app, handler):
    @asyncio.coroutine
    def response(request):
        logging.info("Response handler...")
        # 调用handler来处理url请求,并返回响应结果
        r = yield from handler(request)
        # 若响应结果为StreamResponse,直接返回
        if isinstance(r, web.StreamResponse):
            return r
        # 若响应结果为字节流,则将其作为应答的body部分,并设置应答的类型为流型
        if isinstance(r, bytes):
            resp = web.Response(body=r)
            resp.content_type = "application/octet-stream"
            return resp
        # 若响应结果为字符串
        if isinstance(r, str):
            # 判断响应结果是否为重定向.若是,则返回重定向的地址
            if r.startswith("redirect:"):
                return web.HTTPFound(r[9:])
            # 响应结果不是重定向,则以utf-8对字符串进行编码,作为body.设置相应的响应类型
            resp = web.Response(body = r.encode("utf-8"))
            resp.content_type = "text/html;charset=utf-8"
            return resp
        # 若响应结果为字典,则获取它的模板属性
        if isinstance(r, dict):
            template = r.get("__template__")
            # 若不存在对应模板,则将字典调整为json格式返回,并设置响应类型为json 
            if template is None:
                resp = web.Response(body=json.dump(r, ensure_ascii=False, default=lambda o: o.__dict__).encode("utf-8"))
                resp.content_type = "application/json;charset=utf-8"
                return resp
            # 存在对应模板的,则将套用模板
            else:
                resp = web.Response(body=app["__templating__"].get_template(template).render(**r).encode("utf-8"))
                resp.content_type = "text/html;charset=utf-8"
                return resp
        # 若响应结果为整形的,并且满足以下条件,直接返回
        if isinstance(r, int) and r >=100 and r<600:
            return web.Response
        # 若响应结果为元组,并且长度为2
        if isinstance(r, tuple) and len(r) == 2:
            t, m = r
            # 判断元组的第一个元素是否符合条件的整型
            # 认定t为htto状态码,m为错误描述
            if isinstance(t, int) and t>= 100 and t < 600:
                return web.Response(t, str(m))
        # 默认以字符串形式返回响应结果,设置类型为普通文本
        resp = web.Response(body=str(r).encode("utf-8"))
        resp.content_type = "text/plain;charset=utf-8"
        return resp
    return response

# 时间过滤器
def datetime_filter(t):
    # 定义时间差
    delta = int(time.time()-t)
    # 针对时间分类
    if delta < 60:
        return u"1分钟前"
    if delta < 3600:
        return u"%s分钟前" % (delta // 60)
    if delta < 86400:
        return u"%s小时前" % (delta // 3600)
    if delta < 604800:
        return u"%s天前" % (delta // 86400)
    dt = datetime.fromtimestamp(t)
    return u"%s年%s月%s日" % (dt.year, dt.month, dt.day)

# 初始化协程
@asyncio.coroutine
def init(loop):
    # 创建全局数据库连接池
    yield from orm.create_pool(loop = loop, host="127.0.0.1", port = 3306, user = "www", password = "www", db = "awesome")
    # 创建web应用,
    # middleware是一种拦截器,在一个url被某个函数处理之前,可以先经过一系列middleware的处理
    # middleware的用处在于把通用的功能从每个url处理函数中拿出来,集中放到一个地方
    app = web.Application(loop = loop, middlewares=[logger_factory, response_factory]) # 创建一个循环类型是消息循环的web应用对象
    # 设置模板为jiaja2, 并以时间为过滤器
    init_jinja2(app, filters=dict(datetime=datetime_filter))
    # 注册所有url处理函数
    add_routes(app, "handlers")
    add_statis(app)
    # 调用子协程:创建一个TCP服务器,绑定到"127.0.0.1:9000"socket,并返回一个服务器对象
    srv = yield from loop.create_server(app.make_handler(), "127.0.0.1", 9000)
    logging.info("server started at http://127.0.0.1:9000")
    return srv

loop = asyncio.get_event_loop() # loop是一个消息循环对象
loop.run_until_complete(init(loop)) #在消息循环中执行协程
loop.run_forever()
