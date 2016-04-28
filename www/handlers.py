#!/usr/bin/env python3
# -*- coding: utf-8 -*-

''

__author__ = 'Engine'

import time
import re
import json
import logging
import hashlib
import base64
import asyncio
import markdown2
from aiohttp import web
from coroweb import get, post # 导入装饰器,这样就能很方便的生成request handler
from models import User, Comment, Blog, next_id
from apis import APIResourceNotFoundError, APIValueError, APIError, APIPermissionError, Page
from config import configs


# 此处所列所有的handler都会在app.py中通过add_routes自动注册到app.router上
# 因此,在此脚本尽情地书写request handler即可

COOKIE_NAME = 'awesession'             # cookie名,用于设置cookie
_COOKIE_KEY = configs.session.secret   # cookie密钥,作为加密cookie的原始字符串的一部分

# 验证用户身份
def check_admin(request):
    # 检查用户是否管理员
    # 对于已登录的用户,检查其admin属性. 管理员的admin为真
    if request.__user__ is None or not request.__user__.admin:
        raise APIPermissionError()

# 取得页码
def get_page_index(page_str):
    # 将传入的字符串转为页码信息, 实际只是对传入的字符串做了合法性检查
    p = 1
    try:
        p = int(page_str)
    except ValueError as e:
        pass
    if p < 1:
        p = 1
    return p

# 文本转html
def text2html(text):
    '''文本转html'''
    # 先用filter函数对输入的文本进行过滤处理: 断行,去首尾空白字符
    # 再用map函数对特殊符号进行转换,在将字符串装入html的<p>标签中
    lines = map(lambda s: '<p>%s</p>' % s.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;'), filter(lambda s: s.strip() != '', text.split('\n')))
    # lines是一个字符串列表,将其组装成一个字符串,该字符串即表示html的段落
    return ''.join(lines)

# 通过用户信息计算加密cookie
def user2cookie(user, max_age):
    '''Generate cookie str by user.'''
    # build cookie string by: id-expires-sha1
    expires = str(int(time.time() + max_age)) # expires(失效时间)是当前时间加上cookie最大存活时间的字符串
    # 利用用户id,加密后的密码,失效时间,加上cookie密钥,组合成待加密的原始字符串
    s = "%s-%s-%s-%s" % (user.id, user.passwd, expires, _COOKIE_KEY)
    # 生成加密的字符串,并与用户id,失效时间共同组成cookie
    L = [user.id, expires, hashlib.sha1(s.encode("utf-8")).hexdigest()]
    return "-".join(L)

# 解密cookie
@asyncio.coroutine
def cookie2user(cookie_str):
    '''Parse cookie and load user if cookie is valid'''
    # cookie_str就是user2cookie函数的返回值
    if not cookie_str:
        return None
    try:
        # 解密是加密的逆向过程,因此,先通过'-'拆分cookie,得到用户id,失效时间,以及加密字符串
        L = cookie_str.split("-") # 返回一个str的list
        if len(L) != 3: # 由上可知,cookie由3部分组成,若拆分得到不是3部分,显然出错了
            return None
        uid, expires, sha1 = L
        if int(expires) < time.time(): # 时间是浮点表示的时间戳,一直在增大.因此失效时间小于当前时间,说明cookie已失效
            return None
        user = yield from User.find(uid)  # 在拆分得到的id在数据库中查找用户信息
        if user is None:
            return None
        # 利用用户id,加密后的密码,失效时间,加上cookie密钥,组合成待加密的原始字符串
        # 再对其进行加密,与从cookie分解得到的sha1进行比较.若相等,则该cookie合法
        s = "%s-%s-%s-%s" % (uid, user.passwd, expires, _COOKIE_KEY)
        if sha1 != hashlib.sha1(s.encode("utf-8")).hexdigest():
            logging.info("invalid sha1")
            return None
        # 以上就完成了cookie的验证,过程非常简单,但个人认为效率不高
        # 验证cookie,就是为了验证当前用户是否仍登录着,从而使用户不必重新登录
        # 因此,返回用户信息即可
        user.passwd = "*****"
        return user
    except Exception as e:
        logging.exception(e)
    return None

# 对于首页的get请求的处理
@get('/')
def index(request):
    # summary用于在博客首页上显示的句子,这样真的更有feel
    summary = "Lorem ipsum dolor sit amet, consectetur adipisicing elit, sed do eiusmod tempor incididunt ut labore et dolore magna aliqua."
    # 这里只是手动写了blogs的list, 并没有真的将其存入数据库
    blogs_list = yield from Blog.findAll(orderBy = "created_at desc")
    blogs = list(blogs_list)
    [
        Blog(id="1", name="Test1 Blog", summary=summary, created_at=time.time()-120),
        Blog(id="2", name="Test2 Blog", summary=summary, created_at=time.time()-3600),
        Blog(id="3", name="Test3 Blog", summary=summary, created_at=time.time()-7200)
    ]
    # 返回一个字典, 其指示了使用何种模板,模板的内容
    # app.py的response_factory将会对handler的返回值进行分类处理
    return {
        "__template__": "blogs.html",
        "blogs": blogs  # 参数blogs将在jinja2模板中被解析
    }

# 返回注册页面
@get("/register")
def register():
    return{
        "__template__": "register.html"
    }

# 返回登录页面
@get("/signin")
def signin():
    return{
        "__template__": "signin.html"
    }

# 用户信息接口,用于返回机器能识别的用户信息
@get('/api/users')
def api_get_users():
    users = yield from User.findAll(orderBy="created_at desc")
    for u in users:
        u.passwd = "*****"
    # 以dict形式返回,并且未指定__template__,将被app.py的response factory处理为json
    return dict(users=users)

# 匹配邮箱与加密后密码的证得表达式
_RE_EMAIL = re.compile(r'^[a-z0-9\.\-\_]+\@[a-z0-9\-\_]+(\.[a-z0-9\-\_]+){1,4}$')
_RE_SHA1 = re.compile(r'[0-9a-f]{40}$')

# 这是实现用户注册的api,注册到/api/users路径上,http method为post
@post('/api/users')
def api_register_user(*,name, email, passwd): # 注册信息包括用户名,邮箱与密码
    # 验证输入的正确性
    if not name or not name.strip():
        raise APIValueError("name")
    if not email or not _RE_EMAIL.match(email):
        raise APIValueError("email")
    if not passwd or not _RE_SHA1.match(passwd):
        raise APIValueError("passwd")
    # 在数据库里查看是否已存在该email
    users = yield from User.findAll('email=?', [email]) # mysql parameters are listed in list
    if len(users) > 0: # findAll的结果不为0,说明数据库已存在同名email,抛出异常报错
        raise APIError('register:failed', 'email', 'Email is already in use.')

    # 数据库内无相应的email信息,说明是第一次注册
    uid = next_id() # 利用当前时间与随机生成的uuid生成user id
    sha1_passwd = '%s:%s' % (uid, passwd) # 将user id与密码的组合赋给sha1_passwd变量
    # 创建用户对象, 其中密码并不是用户输入的密码,而是经过复杂处理后的保密字符串
    # unicode对象在进行哈希运算之前必须先编码
    # sha1(secure hash algorithm),是一种不可逆的安全算法.这在一定程度上保证了安全性,因为用户密码只有用户一个人知道
    # hexdigest()函数将hash对象转换成16进制表示的字符串
    # md5是另一种安全算法
    # Gravatar(Globally Recognized Avatar)是一项用于提供在全球范围内使用的头像服务。只要在Gravatar的服务器上上传了你自己的头像，便可以在其他任何支持Gravatar的博客、论坛等地方使用它。此处image就是一个根据用户email生成的头像
    user = User(id=uid, name=name.strip(), email=email, passwd=hashlib.sha1(sha1_passwd.encode('utf-8')).hexdigest(), image="http://www.gravatar.com/avatar/%s?d=mm&s=120" % hashlib.md5(email.encode('utf-8')).hexdigest())
    yield from user.save() # 将用户信息储存到数据库中,save()方法封装的实际是数据库的insert操作

    # 这其实还是一个handler,因此需要返回response. 此时返回的response是带有cookie的响应
    r = web.Response()
    # 刚创建的的用户设置cookiei(网站为了辨别用户身份而储存在用户本地终端的数据)
    # http协议是一种无状态的协议,即服务器并不知道用户上一次做了什么.
    # 因此服务器可以通过设置或读取Cookies中包含信息,借此维护用户跟服务器会话中的状态
    # user2cookie设置的是cookie的值
    # max_age是cookie的最大存活周期,单位是秒.当时间结束时,客户端将抛弃该cookie.之后需要重新登录
    # r.set_cookie(COOKIE_NAME, user2cookie(user, 600), max_age=600, httponly=True)  # 设置cookie最大存会时间为10min
    r.set_cookie(COOKIE_NAME, user2cookie(user, 86400), max_age=86400, httponly=True)  #86400s=24h
    user.passwd = '*****' # 修改密码的外部显示为*
    # 设置content_type,将在data_factory中间件中继续处理
    r.content_type = 'application/json'
    # json.dumps方法将对象序列化为json格式
    r.body = json.dumps(user, ensure_ascii=False).encode('utf-8')
    return r

# 用户登录的验证api
@post("/api/authenticate")
def authenticate(*, email, passwd): # 通过邮箱与密码验证登录
    # 验证邮箱与密码的合法性
    if not email:
        raise APIValueError("email", "Invalid email")
    if not passwd:
        raise APIValueError("passwd", "Invalid password")
    users = yield from User.findAll("email=?", [email]) # 在数据库中查找email,将以list形式返回
    if len(users) == 0: # 查询结果为空,即数据库中没有相应的email记录,说明用户不存在
        raise APIValueError("email", "Email not exits")
    user = users[0] # 取得用户记录.事实上,就只有一条用户记录,只不过返回的是list
    # 验证密码
    # 数据库中存储的并非原始的用户密码,而是加密的字符串
    # 我们对此时用户输入的密码做相同的加密操作,将结果与数据库中储存的密码比较,来验证密码的正确性
    # 以下步骤合成为一步就是:sha1 = hashlib.sha1((user.id+":"+passwd).encode("utf-8"))
    # 对照用户时对原始密码的操作(见api_register_user),操作完全一样
    sha1 = hashlib.sha1()
    sha1.update(user.id.encode("utf-8"))
    sha1.update(b":")
    sha1.update(passwd.encode("utf-8"))
    if user.passwd != sha1.hexdigest():
        raise APIValueError("passwd", "Invalid password")
    # 用户登录之后,同样的设置一个cookie,与注册用户部分的代码完全一样
    r = web.Response()
    r.set_cookie(COOKIE_NAME, user2cookie(user, 86400), max_age=86400, httponly=True)
    # r.set_cookie(COOKIE_NAME, user2cookie(user, 600), max_age=600, httponly=True)
    user.passwd = "*****"
    r.content_type = "application/json"
    r.body = json.dumps(user, ensure_ascii=False).encode("utf-8")
    return r

# 用户登出
@get("/signout")
def signout(request):
    # 请求头部的referer,表示从哪里链接到当前页面,即上一个页面
    # 用户登出时,实际转到了/signout路径下,因此为了使登出毫无维和感,获得"当前"url
    referer = request.headers.get("Referer")
    # 若无前一个网址,可能是用户新打开了一个标签页,则登录后转到首页
    r = web.HTTPFound(referer or '/')
    # 以设置cookie的最大存活时间来删除cookie
    r.set_cookie(COOKIE_NAME, "-deleted-", max_age=0, httponly=True)
    logging.info("user signed out.")
    return r

# 获取单条博客的api
@get('/api/blogs/{id}')
def api_get_blog(*, id):
    blog = yield from Blog.find(id)
    return blog

# 创建博客的api,从js的postJSON函数接收表单信息
@post('/api/blogs')
def api_create_blog(request, *, name, summary, content):
    check_admin(request) # 检查用户权限
    # 验证博客信息的合法性
    if not name or not name.strip():
        raise APIValueError("name", "name cannot be empty")
    if not summary or not summary.strip():
        raise APIValueError("summary", "summary cannot be empty")
    if not content or not content.strip():
        raise APIValueError("content", "content cannot be empty")
    # 创建博客对象
    blog = Blog(user_id=request.__user__.id, user_name=request.__user__.name, user_image=request.__user__.image, name=name.strip(),summary=summary.strip(), content=content.strip())
    yield from blog.save() # 储存博客入数据库
    return blog # 返回博客信息

# 获取博客页面
@get('/blog/{id}')
def get_blog(id):
    blog = yield from Blog.find(id) # 通过id从数据库拉取博客信息
    # 从数据库拉取指定blog的全部评论,按时间降序排序,即最新的排在最前
    comments = yield from Comment.findAll('blog_id=?', [id], orderBy='created_at desc')
    # 将每条评论都转化为html格式(根据text2html代码可知,实际为html的<p>)
    for c in comments:
        c.html_content = text2html(c.content)
    blog.html_content = markdown2.markdown(blog.content) # blog是markdown格式,将其转换为html格式
    return {
        # 返回的参数将在jinja2模板中被解析
        "__template__": "blog.html",
        "blog": blog,
        "comments": comments
    }

# 获取blog信息的api
@get('/api/blogs')
def api_blogs(*, page='1'):
    page_index = get_page_index(page)
    num = yield from Blog.findNumber('count(id)')  # num为博客总数
    p = Page(num, page_index) # 创建page对象
    if num == 0:
        return dict(page=p, blogs=())  # 若博客数为0,返回字典,将被app.py的response中间件再处理
    # 博客总数不为0,则从数据库中抓取博客
    # limit强制select语句返回指定的记录数,前一个参数为偏移量,后一个参数为记录的最大数目
    blogs = yield from Blog.findAll(orderBy="created_at desc", limit=(p.offset, p.limit))
    return dict(page=p, blogs=blogs)  # 返回字典,以供response中间件处理

# 写博客的页面
@get('/manage/blogs/create')
def manage_create_blog():
    return {
        "__template__": "manage_blog_edit.html",
        'id': '',    # id的值将传给js变量I
        # action的值也将传给js变量action
        # 将在用户提交博客的时候,将数据post到action指定的路径,此处即为创建博客的api
        'action': '/api/blogs'
    }

# 管理博客的页面
@get('/manage/blogs')
def manage_blogs(*, page='1'):  # 管理页面默认从"1"开始
    return {
        "__template__": "manage_blogs.html",
        "page_index": get_page_index(page)  #通过page_index来显示分页
    }
