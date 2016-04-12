#!/usr/bin/env python3
# -*- coding: utf-8 -*-

''

__author__ = 'Engine'

import orm, asyncio
from models import User, Blog, Comment

def test(loop):
    yield from orm.create_pool( loop =loop, user="www-data", password="www-data", database="awesome")

    b = Comment(blog_id="1", user_id="1", user_name="K", user_image="about:blank", name="ok", summary="fine", content="fff")
    yield from b.save()

loop = asyncio.get_event_loop()
loop.run_until_complete(test(loop))
loop.close()
