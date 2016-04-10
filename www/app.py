#!/usr/bin/env python3
# -*- coding: utf-8 -*-

''

__author__ = 'Engine' 

import logging
logging.basicConfig(level=logging.INFO) # 设置根记录器,具体的有待查明

import asyncio, os, json, time
from datetime import datetime

from aiohttp import web

from orm import Model, StringField, IntegerField

def index(request):
    return web.Response(body=b"<h1>To be Awesome.</h1>")

@asyncio.coroutine
def init(loop):
    app = web.Application(loop = loop)
    app.router.add_route("GET", '/', index) # 为"/"路径的"GET"添加index处理
    # 每当有一个对Socket的访问,产生一个处理
    srv = yield from loop.create_server(app.make_handler(), "127.0.0.1", 9000)
    logging.info("server started at http://127.0.0.1:9000")
    return srv

# 创建全局数据库连接池,使每个http请求都能从连接池中直接获取数据库连接
@asyncio.coroutine
def create_pool(loop, **kw):
    logging.info("create database connection pool...")
    global __pool
    __pool = yield from aiomysql.create_pool(
            host      = kw.get("host", "localhost"),
            post      = kw.get("post", 3306),
            user      = kw["user"],
            password  = kw["password"],
            db        = kw["db"],
            charset   = kw.get("charset", "utf8"),
            autocommit= kw.get("autocommit", True), # 自动提交事务
            maxsize   = kw.get("maxsize", 10),
            minsize   = kw.get("minsize", 1),
            loop      = loop
            )

# 将数据库的select操作封装在select函数中
@asyncio.coroutine
def select(sql, args, size=None):
    log(sql, args)
    global __pool
    # 从连接池获取数据库连接,生成游标,执行sql语句,关闭游标,全都采用异步处理方式
    with (yield from __pool) as conn:
        cur = yield from conn.cursor(aiomysql.DictCursor)
        # sql语句的占位符为"?", mysql的占位符为"%s"
        yield from cur.execute(sql.replace("?", "%s"), args or ())
        if size:
            rs = yield from cur.fetchmany(size)
        else:
            rs = yield from cur.fetchall()
        yield from cur.close()
        logging.info("row return %s" % len(rs))
        return rs


# 封装增删改到一个execute函数
@asyncio.coroutine
def execute(sql, args):
    log(sql)
    with (yield from __pool) as conn:
        try:
            cur = yield from conn.cursor()
            yield from cur.execute(sql.replace("?", "%s"), args)
            affected = cur.rowcount # 增删改,返回结果数即可
            yield from cur.close()
        except BaseException as e:
            raise
        return affected

# ORM映射基类,继承自dict,又实现__getattr__()和__setattr__()
class Model(dict, metaclass=ModelMetaclass):
    
    def __init__(self, **kw):
        super(Model, self).__init__(**kw)

    def __getattr__(self, key):
        try:
            return self[key]
        except KeyError:
            raise AttributeError(r"'Model' object has no attribute'%s'" % key)

    def __setattr__(self, key, value):
        self[key] = value

    def getValue(self, key):
        return getattr(self, key, None)

    def getValueOrDefault(self, key):
        value = getattr(self, key, None)
        if value is None:
            field = self.__mappings__[key]
            if field.default is not None:
                value = field.default() if callable(field.default) else field.default
                logging.debug("using default value for %s: %s", % (key, str(value)))
                setattr(self, key, value)
        return value

    @asyncio.coroutine
    def save(self):
        args = list(map(self.getValueOrDefault, self.__fields__))
        args.append(self.getValueOrDefault(self.__primary_key__))
        rows = yield from execute(self.__insert__, args)
        if rows != 1:
            logging.warn("failed to insert recored: affected rows: %s", % rows)

class Field(object):

    def __init__(self, name, column_type, primary_key, default):
        self.name = name
        self.column_type = column_type
        self.primary_key = primary_key
        seflf.default = default

    def __str__(self):
        return "<%s, %s:%s>" % (self.__class_.__name__, self.column_type, self.name)

class StringFiled(Field):
    def __init__(self, name=None, primary_key=False, default=None, ddl="varchar(100)"):
        super().__init__(name, ddl, primary_key, default)

# 任何继承自Model的类,都会自动通过ModelMetaclass扫描映射关系,并存储到自身的类属性
class ModelMetaclass(type):
    
    def __new__(cls, name, bases, attrs):

        if name == "Model":
            return type.__new__(cls, name, bases, attrs)

        tableName = attrs.get("__table__", None) or name
        logging.inof("found model: %s (table: %s)" % (name, tableName))

        mappings = dict()
        fileds = []
        primaryKey = None
        for k, v in attrs.items():
            if isinstance(v, Filed):
                logging.info(" found mapping: %s ==> %s" % (k, v))
                mapping[k] = v
                if v.primary_key:
                    if primaryKey:
                        raise RuntimeError("Duplicate primary key for field: %s", % s)
                    primaryKey = k
                else:
                    fileds.append(k)
        if not primaryKey:
            raise RuntimeError("Primary key not found")
        for k in mapping.keys():
            attrs.pop(k)
        escaped_fields = list(map(lambda f: "`%s`" % f, fields))
        attrs.["__mappings__"] = mappings
        attrs.["__table__"] = tableName
        attrs.["__primary_key__"] = primaryKey
        attrs.["__fields__"] = fields
        attrs.["__select__"] = "select `%s`, %s from `%s`" % (primaryKey, ', '.join(escaped_fields), tableName)
        attrs.["__insert__"] = "insert into `%s` (%s, `%s`) values (%s)" % (tableName, ', '.join(escaped_fields), primaryKey, create_args_string(len(escaped_fields) +1 ))
        attrs.["__update__"] = "update `%s` set %s where `%s`=?" % (tableName, ', '.join(map(lambda f: "`%s`" % mappings(.get(f).name or f), fields)), primaryKey)
        attrs["__delete__"] = "delete from `%s` where `%s`=?" % (tableName, primaryKey)
        return type.__new__(cls, name, bases, attrs)


# ORM 映射,用户表
class User(Model):
    __table__ = "users"

    id = IntegerField(primary_key=True)
    name = StringFiled()



    
loop = asyncio.get_event_loop() # loop是一个消息循环对象
loop.run_until_complete(init(loop))
loop.run_forever()
user = User=(id = 1007, name  = "Engine")
user.insert()
users = User.findAll()
user = yield from User.find("1007")

