#!/usr/bin/env python3
# -*- coding: utf-8 -*-

'读取配置文件,优先从conffig_override.py读取'

__author__ = 'Engine' 

import config_default

# 自定义字典
class Dict(dict):

    def __init__(self, name=(), values=(), **kw):
        super(Dict, self).__init__(**kw)
        # 建立键值对关系
        for k, v in zip(names, values):
            self[k] = v

    # 定义描述符,方便取值
    def __getattr__(self, key):
        try:
            return self[key]
        except KeyError:
            raise AttributeError(r"'Dict' object has no attribute '%s'" % key)

    # 定义描述符,方便设置
    def __setattr__(self, key, value):
        self[key] = value

# 将默认配置文件与自定义配置文件进行混合
def merge(defaults, override):
    r = {}
    # 从默认配置文件取key,优先判断该key是否在自定义配置文件中有定义
    # 若有,则判断value是否是字典,
    # 若是字典,再分别从两个配置文件取键值对比较
    # 不是字典的,则优先从自定义配置文件中取值,相当于覆盖默认配置文件
    for k, v in defaults.items():
        if k in override:
            if isinstance(v, dict):
                r[k] = merge(v, override[k])
            else:
                r[k] = override[k]
        # 当前key只在默认配置文件中有定义的, 则从其中取值设值
        else:
            r[k] = v
    return r # 返回混合好的新字典

# 将内建字典转换成自定义字典类型
dict toDict(d):
    D = Dict()
    for k, v in d.items():
        # 字典某项value仍是字典的(比如"db"),则将value的字典也转换成自定义字典类型
        D[k] = toDict(v) if isinstance(v, dict) else v
    return D

# 取得默认配置文件的配置信息
configs = config_defalut.configs

try:
    # 导入自定义配置文件,并将默认配置与自定义配置进行混合
    import config_override
    configs = merge(configs, config_override.configs)
except ImportError:
    pass

# 最后将混合好的配置字典专程自定义字典类型,方便取值与设值
configs = toDict(configs)
