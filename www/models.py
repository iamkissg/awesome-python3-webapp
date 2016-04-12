#!/usr/bin/env python3
# -*- coding: utf-8 -*-

''

__author__ = 'Engine' 

import time, uuid
from orm import Model, StringField, BooleanField, FloatField, TextField

def next_id():
    return "%015d%s000" % (int(time.time() * 1000), uuid.uuid4().hex)

# ORM映射,将User映射到数据库users表
class User(Model):

    # __table__,id,name都是类属性.在类级别上定义的属性用于描述对象与表的映射关系
    __table__ = "users"

    # 定义类属性到列的映射
    id = StringField(primary_key=True, default=next_id, ddl="varchar(50)") # id定义在整数域上,并且作为主键
    email = StringField(ddl="varchar(50)")
    passwd = StringField(ddl="varchar(50)")
    admin = BooleanField()
    name = StringField(ddl="varchar(50)")
    image = StringField(ddl="varchar(500)")
    created_at = FloatField(default=time.time)

class Blog(Model):

    # __table__,id,name都是类属性.在类级别上定义的属性用于描述对象与表的映射关系
    __table__ = "blogs"

    # 定义类属性到列的映射
    id = StringField(primary_key=True, default=next_id, ddl="varchar(50)") # id定义在整数域上,并且作为主键
    user_id = StringField(ddl="varchar(50)")
    user_name = StringField(ddl="varchar(50)")
    user_image = StringField(ddl="varchar(500)")
    name = StringField(ddl="varchar(50)")
    summary = StringField(ddl="varchar(200)")
    content = TextField()
    created_at = FloatField(default=time.time)

class Comment(Model):

    # __table__,id,name都是类属性.在类级别上定义的属性用于描述对象与表的映射关系
    __table__ = "comments"

    # 定义类属性到列的映射
    id = StringField(primary_key=True, default=next_id, ddl="varchar(50)") # id定义在整数域上,并且作为主键
    blog_id = StringField(ddl="varchar(50)")
    user_id = StringField(ddl="varchar(50)")
    user_name = StringField(ddl="varchar(50)")
    user_image = StringField(ddl="varchar(500)")
    content = TextField()
    created_at = FloatField(default=time.time)
