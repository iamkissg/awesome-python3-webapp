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
    # with lcd(path) - 在本机,执行 cd path
    # os.path.abspath(path) - 取得当前路径的绝对路径
    # os.path.join(a, *p) - 将两部分路径整合到一起
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
    newdir = "www-%s" % datetime.now().strftime("%y-%m-%d_%h.%M.%s")
    # 删除已有的tar文件
    # run()函数的命令在服务器上运行,需要sudo权限时,用sudo()来代替run()
    run("rm -f %s" % _REMOTE_TMP_TAR)
    # 上传新的tar为文件, 前一个参数指定为本地文件,后一个指定为远程文件
    put("dist/%s" % _TAR_FILE, _REMOTE_TMP_TAR)
    # with cd(path) - 在远程计算机上,执行cd path
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


# 返回当前路径
def _current_path():
    return os.path.abspath(".")


# 返回当前格式化的时间
def _now():
    return datetime.now().strftime("%y-%m-%d_%h.%M.%s")


# 将服务器上的数据备份到本地
def backup():
    '''dump entire database on server and backup to local'''
    dt = _now()
    f = "backup-awesome-%s.sql" % dt  # 创建一个包含时间的db文件名
    with cd("/tmp"):  # 远程计算机 "cd /tmp", 以下指令都在该目录下执行
        run("mysqldump --user=%s --password=%s --skip-opt --add-drop-table --default-character-set=utf8 --quick awesome > %s" % (db_user, db_password, f))  # 将awesome的数据转出到f
        run("tar -czvf %s.tar.gz %s" % (f, f))  # 将得到的数据打包
        get("%s.tar.gz" % f, "%s/backup/" % _current_path())  # 从服务器拉取数据包
        run("rm -f %s " % f)  # 删除数据文件与压缩包
        run("rm -f %s.tar.gz" % f)


RE_FILES = re.compile("\r?\n")


# 服务器上应用版本回退
def rollback():
    '''rollback to previous version'''
    with cd(_REMOTE_BASE_DIR):
        r = run("ls -p -1")  # 显示应用目录下的文件,并储存到变量r
        files = [s[:-1] for s in RE_FILES.split(r) if s.startswith("www-") and s.endswith("/")]  # 取得版本的列表
        # cmp参数指定比较函数,用匿名函数lambda表示,将按版本新旧排序
        # 对各版本进行排序
        files.sort(cmp=lambda s1, s2: 1 if s1 < s2 else -1)
        # 由于www通过软链接指向某一版本目录,因此ls -l将显示如下:
        # lrwxrwxrwx 1 root root 21 May  3 17:15 www -> www-16-05-03_17.15.49
        r = run("ls -l www")
        ss  = r.split(" -> ")
        if len(ss) != 2:
            print("ERROR: 'www' is not a symbol link.")
            return
        current = ss[1]   # 取得当前版本号,赋给变量current
        print("Found current symbol link points to: %s\n" % current)
        try:
            index = files.index(current)  # 找到当前在全部版本中的序号
        except ValueError as e:
            print("ERROR: symbol link is invalid")
            raise e
            return
        if len(files) == index + 1:  # 序号是最末尾了,已经是最老的版本了
            print("ERROR: already the oldest version.")
            return
        old = files[index + 1]  # 取得当前版本上一版本号
        print("=" * 80)
        for f in files:  # 显示版次信息,以明确告诉管理员
            if f == current:
                print("        Current ---> %s" % current)
            elif f == old:
                print("    Rollback to ---> %s" % old)
            else:
                print("                     %s" % f)
        print("=" * 80)
        print("")
        yn = raw_input("continue? y/N?")  # 提示管理员是否继续
        if yn != 'y' and yn != 'Y':
            print("Rollback cancelled.")
            return
        print("Start rollbask...")
        sudo("rm -f www")  # 所谓版本回退就是www的软链接指向另一个版本
        sudo("ln -s %s www" % old)
        sudo("chown www-data:www-data www")
        with settings(warn_only=True):  # 版本回退成功,重启服务器
            sudo("supervisor stop awesome")
            sudo("supervisor start awesome")
            sudo("/etc/init.d/nginx reload")
        print("ROLLBACKED OK")


def restore2local():
    backup_dir = os.path.join(_current_path(), "backup")  # 本机的备份目录
    fs = os.listdir(backup_dir)  #备份目录下的文件列表
    files = [f for f in fs if f.startswith("backup-") and f.endswith(".sql.tar.gz")]  # 取得本机已备份的数据库文件压缩包列表
    files.sort("cmp=lambda s1, s2: 1 if s1 < s2 else -1")  # 按时间从新到旧排序
    if len(files) == 0:
        print("No backup files found,")
        return
    print("Found %s backup files:" % len(files))
    print("=" * 80)
    n = 0
    for f in files:  # 打印本机的备份数据信息
        print("%s: %s" % (n, f))
        n += 1
    print("=" * 80)
    print("")
    try:
        num = int(raw_input("Resotre file: "))  # 让管理员选择要恢复的数据号
    except VauleError:
        print("Invalid file number")
        return
    restore_file = files[num]  # 根据管理员的选择,取出要恢复的数据库文件
    # 提醒管理员是否选择恢复
    yn = raw_input ("Restore file %s: %s? y/N" % (num, restore_file))
    if yn != 'y' and yn != 'Y':
        print("Restore cancelled.")
        return
    print("Start restore to local database...")
    p = raw_input("Input mysql root password: ")
    sqls = [  # mysql语句列表
        "drop database if exists awesome;",  # 若本地已存在awesome数据库,删除之
        "create database awesome;",  # 新建数据库
        "grant select, insert, update, delete on awesome.* to '%s'@'localhost' identified by '%s';" % (db_user, db_password)
    ]
    for sql in sqls:
        # 在本地执行数据库操作,即删除旧database,再新建database
        local(r'mysql -u root -p%s -e "%s"' % (p, sql))
    with lcd(backup_dir):
        # 在本地应用备份目录下解压选择的数据库备份文件
        local("tar xzvf %s" % restore_file)
    local(r"mysql -u root -p%s awesome < backup/%s" % (p, restore_file[:-7]))  # 将选择的备份恢复到本地数据库
    with lcd(backup_dir):
        # 删除解压得到的备份文件,仅以压缩包形式储存
        local("rm -f %s" % restore_file[:-7])
