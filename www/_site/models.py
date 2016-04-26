#!/usr/bin/env python3
# -*- coding: utf-8 -*-

'定义各类的属性'

__author__ = 'Engine' 

import time
import uuid # the module provides immutable uuid objects, and the functions to generating different versions uuid.
from orm import Model, StringField, BooleanField, FloatField, TextField

# 用当前时间与随机生成的uuid合成作为id
def next_id():
    # uuid4()以随机方式生成uuid,hex属性将uuid转为32位的16进制数
    return "%015d%s000" % (int(time.time() * 1000), uuid.uuid4().hex)

# ORM映射,将User映射到数据库users表
class User(Model):

    # __table__的值将在创建类时被映射为表名
    __table__ = "users"

    # 定义各属性的域,以及是否主键,将在创建类时被映射为数据库表的列
    # 此处default用于存储每个用于独有的id,next_id将在insert的时候被调用
    id = StringField(primary_key=True, default=next_id, ddl="varchar(50)")
    email = StringField(ddl="varchar(50)")
    passwd = StringField(ddl="varchar(50)")
    admin = BooleanField()
    name = StringField(ddl="varchar(50)")
    image = StringField(ddl="varchar(500)")
    # 此处default用于存储创建的时间,在insert的时候被调用
    created_at = FloatField(default=time.time) 

class Blog(Model):

    __table__ = "blogs"

    id = StringField(primary_key=True, default=next_id, ddl="varchar(50)")
    user_id = StringField(ddl="varchar(50)")
    user_name = StringField(ddl="varchar(50)")
    user_image = StringField(ddl="varchar(500)")
    name = StringField(ddl="varchar(50)")
    summary = StringField(ddl="varchar(200)")
    content = TextField()
    created_at = FloatField(default=time.time)

class Comment(Model):

    __table__ = "comments"

    id = StringField(primary_key=True, default=next_id, ddl="varchar(50)") 
    blog_id = StringField(ddl="varchar(50)")
    user_id = StringField(ddl="varchar(50)")
    user_name = StringField(ddl="varchar(50)")
    user_image = StringField(ddl="varchar(500)")
    content = TextField()
    created_at = FloatField(default=time.time)
