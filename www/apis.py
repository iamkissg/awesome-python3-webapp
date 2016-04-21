#!/usr/bin/env python3
# -*- coding: utf-8 -*-

'Json API definition'

__author__ = 'Engine' 

import json
import logging
import inspect # the module provides several useful functions to help get information about live objects, such as modules, classes, methods, functions.
import functools # 该模块提供有用的高阶函数.总的来说,任何callable对象都可视为函数


class APIError(Exception):
    '''
    定义APIError基类
    '''
    def __init__(self, error, data="", message=""):
        super(APIError, self).__init__(message)
        self.error = error
        self.data = data
        self.message = message

class APIValueError(APIError):
    '''
    定义APIValueError类
    表明输入的值错误或不合法.
    data属性指定为输入表单的错误域
    '''
    def __init__(self, field, message=""):
        super(APIValueError, self).__init__("value:invalid", field, message)


class APIResourceNotFoundError(APIError):
    '''
    定义APIResourceNotFoundError类
    表明找不到指定资源.
    data属性指定为资源名
    '''
    def __init__(self, field, message=""):
        super(APIResourceNotFoundError, self).__init__("value:notfound", field, message)

class APIPermissionError(APIError):
    '''
    定义APIPermissionError类
    表明没有权限
    '''
    def __init__(self, message=""):
        super(APIPermissionError, self).__init__("permission:forbidden", "permission", message)
