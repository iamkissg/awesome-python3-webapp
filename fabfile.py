#!/usr/bin/env python3
# -*- coding: utf-8 -*-

''

__author__ = 'Engine'

import os
import re
from datetime import datetime

# fabric使用ssh直接登录服务器并执行部署命令
from fabric.api import *

# 设置环境参数
# 服务器登录用户名
env.user = "ubuntu"
# 服务器sudo用户
env.sudo_user = "root"
# 服务器地址,可以有多个,依次部署
env.hosts = ["115.159.201.95"]
# 服务器mysql的用户名和口令
db_user = "www-data"
db_password = "www-data"


# 打包任务

# 打包的目标文件名
_TAR_FILE = "dist-awesome.tar.gz"
def build():
    # 打包的内容
    includes = ["static", "templates", "favicon.ico", "*.py"]
    excludes = ["test", ".*", "*.pyc", "*.pyo"]  # 不打包的内容
    # local来运行本地命令
    # 删除已存在的打包文件
    local("rm -f dist/%s" % _TAR_FILE)
    # with lcd(path)将当前命令的目录在服务器端设定为lcd()指定的目录
    # os.path.abspath(path) - 取得当前路径的绝对路径
    # os.path.join(a, *p) - 将两部分路径整合到一起
    # 此时lcd的参数为"/home/username/.../www"
    with lcd(os.path.join(os.path.abspath("."), 'www')):
        # shell命令
        cmd = ['tar', "--dereference", "-czvf", "../dist/%s" % _TAR_FILE]
        cmd.extend(["--exclude=%s" % ex for ex in excludes])
        cmd.extend(includes)
        local(" ".join(cmd))  # 将shell命令的各部分组装成一个完整的命令

# 远程临时压缩包
_REMOTE_TMP_TAR = "/tmp/%s" % _TAR_FILE
# 远程应用目录
_REMOTE_BASE_DIR = "/srv/awesome"
def deploy():
    # 用时间来命名新版本
    newdir = "www-%s" % datetime.now().strftime("%y-%m-%d_%H.%M.%S")
    # 删除已有的tar文件
    # run()函数的命令在服务器上运行,需要sudo权限时,用sudo()来代替run()
    run("rm -f %s" % _REMOTE_TMP_TAR)
    # 上传新的tar为文件, 前一个参数指定为本地文件,后一个指定为远程文件
    put("dist/%s" % _TAR_FILE, _REMOTE_TMP_TAR)
    # with cd(path)将当前目录在服务器端设置为cd()指定的目录
    # 当前在awesome/下
    # 创建新目录
    with cd(_REMOTE_BASE_DIR):
        sudo("mkdir %s" % newdir)

    # 解压到新目录
    with cd("%s/%s" % (_REMOTE_BASE_DIR, newdir)):
        sudo("tar -xzvf %s" % _REMOTE_TMP_TAR)
    # 重置软链接
    with cd(_REMOTE_BASE_DIR):
        sudo("rm -fr www")
        sudo("ln -s %s www" % newdir)
        sudo("chown www-data:www-data www")
        sudo("chown -R www-data:www-data %s" % newdir)
    # 重启python服务器和nginx服务器
    with settings(war_only=True):
        sudo("supervisorctl stop awesome")
        sudo("supervisorctl start awesome")
        sudo("/etc/init.d/nginx reload")
