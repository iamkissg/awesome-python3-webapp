#!/usr/bin/env python3
# -*- coding: utf-8 -*-

''

__author__ = 'Engine' 

import functools
import asyncio
import os
import inspect      #the module provides several useful functions to help get informationabout live objects
import logging
from urllib import parse
from aiohttp import web
from apis import APIError

# 定义了一个装饰器
# 将一个函数映射为一个URL处理函数
def get(path):
    '''define decorator @get('/path')'''
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kw):
            return func(*args, **kw)
        wrapper.__method__ = "GET"
        wrapper.__route__  = path
        return wrapper
    return decorator

# 与@get类似
def post(path):
    '''define decorator @post('/path')'''
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kw):
            return func(*args, **kw)
        wrapper.__method__ = "POST"
        wrapper.__route__  = path
        return wrapper
    return decorator

# 用于获取命名关键字参数名
def get_required_kw_args(fn):
    args = []
    # 获得函数fn的全部参数
    params = inspect.signature(fn).parameters
    for name, param, in param.items():
        # 获取是命名关键字,且未指定默认值的参数名
        if param.kind == inspect.Parameter.KEYWORD_ONLY and param.default == inspect.Parameter.empty:
            args.append(name)
    return tuple(args)

# 用于获取命名关键字参数名
def get_named_kw_args(fn):
    args = []
     # 获得函数fn的全部参数
    params = inspect.signature(fn).parameters
    for name, param, in param.items():
        # KEYWORD_ONLY, 表示命名关键字参数.
        # 因此下面的操作就是获得命名关键字参数名
        if param.kind == inspect.Parameter.KEYWORD_ONLY:
            args.append(name)
    return tuple(args)


# 用于判断函数fn是否带有命名关键字参数
def has_named_kw_args(fn):
    params = inspect.signature(fn).parameters
    for name, parse in params.items():
        if param.kind == inspect.Parameter.KEYWORD_ONLY:
            return True

# 用于判断函数fn是否带有关键字参数
def has_var_kw_arg(fn):
    params = inspect.signature(fn).parameters
    for name, param in params.items():
        # VAR_KEYWORD, 表示关键字参数, 匹配**kw
        if param.kind == inspect.Parameter.VAR_KEYWORD:
            return True

# 是否函数请求关键字
def has_request_arg(fn):
    sig = inspect.signature(fn)
    params = sig.parameters
    found = False
    for name, param in params.items():
        if name == "request": # 找到名为"request"的参数,置found为真
            found = True
            continue
        # VAR_POSITIONAL,表示可选参数,匹配*args
        # 若已经找到"request"关键字,在其后又发现参数,将报错
        # request参数必须是最后一个命名参数
        if found and (param.kind != inspect.Parameter.VAR_POSITIONAL and param.kind != inspect.Parameter.KEYWORD_ONLY and param.kind != inspect.Parameter.VAR_KEYWORD):
            raise ValueError("request parameter must be the last named parameter in function: %s%s" % (fn.__name__, str(sig)))
    return found

# 定义RequestHandler,封装url处理函数
# RequestHandler的目的是从url函数中分析需要提取的参数,从request中获取必要的参数
# 调用url参数,将结果转换为web.response
class RequestHandler(object):

    def __init__(self, app, fn):
        self._app = app # web application
        self._func = fn # 处理函数
        self._has_request_arg = has_request_arg(fn)
        self._has_var_kw_arg = has_var_kw_arg(fn)
        self._has_named_kw_args = has_named_kw_args(fn)
        self._named_kw_args = get_named_kw_args(fn)
        self._required_kw_args = get_required_kw_args(fn)


    # 定义了__call__,则其实例可以被视为函数
    @asyncio.coroutine
    def __call__(self, request):
        kw = None
        # 存在关键字参数/命名关键字参数
        if self._has_var_kw_arg or self._has_named_kw_args or self._required_kw_args:
            if request.method == "POST":
                if not request.content_type:
                    return web.HTTPBadRequest("Missing Content-Type")
                ct = request.content_type.lower()
                if ct.startswith("application/json"):
                    params = yield from request.json()
                    if not isinstance(params, dict):
                        return web.HTTPBadRequest("JSON body must be object.")
                    kw = params
                elif ct.startswith("application/x-www-form-urlencoded") or ct.startswith("multipart/form-data"):
                    params = yield from request.post()
                    kw = dict(**params)
                else:
                    return web.HTTPBadRequest("Unsupported Content-Type: %s" % request.content_type)
            if request.method == "GET":
                qs = request.query_string
                if qs:
                    kw = dict()
                    for k, v in parse.parse_qs(qs, True).items():
                        kw[k] = v[0]
        if kw is None:
            kw = dict(**request.match_info)
        else:
            if not self._has_var_kw_arg and self._named_kw_args:
                copy = dict()
                for name in self._named_kw_args:
                    if name in kw:
                        copy[name] = kw[name]
                kw = copy
            for k, v in request.match_info.items():
                if k in kw:
                    logging.warning("Duplicate arg name in named arg and kw args: %s" % k)
                kw[k] = v
        if self._has_request_arg:
            kw["request"] = request
        if self._required_kw_args:
            for name in self._required_kw_args:
                if not name in kw:
                    return web.HTTPBadRequest("Missing argument: %s" % name)
        logging.info("call with args: %s" % str(kw))
        try:
            r = yield from self._func(**kw)
            return r
        except APIError as e:
            return dict(error = e.error, data = e.data, message = e.message)
    
    def add_static(app):
        path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "static")
        app.router.add_static("/static/", path)
        logging.info("add static %s => %s" % ("/static/", path))

    # 将处理函数注册到app上
    # 处理将针对http method 和path进行
    def add_route(app, fn):
        method = getattr(fn, "__method__", None)
        path = getattr(fn, "__route__", None)
        # http method 或 path 路径未知,将无法进行处理,因此报错 
        if path is None or method is None:
            raise ValueError("@get or @post not defined in %s." % str(fn))
        # 将非协程或生成器的函数变为一个协程.
        if not asyncio.iscoroutinefunction(fn) and not inspect.isgeneratorfunction(fn):
            fn = asyncio.coroutine(fn)
        logging.info("add route %s %s => %s(%s)" % (method, path, fn.__name__, '. '.join(inspect.signature(fn).parameters.keys())))
        # 注册请求处理
        app.router.add_route(method, path, RequestHandler(app, fn))

    # 自动注册所有请求处理函数
    def add_routes(app, module_name):
        n = module_name.rfind(".")
        if n == (-1):
            mod = __import__(module_name[:n], globals(), locals())
        else:
            name = module_name[n+1:]
            mod = getattr(__import__(module_name[:n], globals(), locals(), [name]), name)
        for attr in dir(mod):
            if attr.startswith("_"):
                continue
            fn = getattr(mod, attr)
            if callable(fn):
                method = getattr(fn, "__method__", None)
                path = getattr(fn, "__route__",None)
                if method and path:
                    add_route(app, fn)

