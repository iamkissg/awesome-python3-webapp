#!/usr/bin/env python3
# -*- coding: utf-8 -*-

''

__author__ = 'Engine'

import models
from coroweb import get, post # 导入装饰器,这样就能很方便的生成request handler


# 此处所列所有的handler都会在app.py中通过add_routes自动注册到app.router上
# 因此,在此脚本尽情地书写request handler即可

# 对于首页的get请求的处理
@get('/')
def index(request):
    users = yield from models.User.findAll()
    return {
        "__template__": "test.html",
        "users": users
    }
