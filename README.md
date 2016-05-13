# Asesome Pyhthon3 WebApp 总结与导读

---

> 看山是山, 看山不是山, 看山还是山

----

## 引文

说实话, 我没资格写这样的博客, 因为水平不够. 说出来不怕丢人, 我完完全全没有学过web开发, 是彻头彻尾的大白(比小白还小白). 该项目的代码几乎全是照着廖老师的, 自己一个一个敲出来的. 但是为了理解这些代码, 期间我查阅了许多[资料](#reference), 几乎为每一行代码都加了详尽的注释.

秉承着"无总结, 不学习"的信念, 我选择对这一个月以来跟随廖老师学习 python3 开发 webapp 的过程做一个总结. 而这篇文章将同时作为[该项目](https://github.com/Engine-Treasure/awesome-python3-webapp)的`README`. 因此, 就有了这么个怪异的标题: 于我是"总结", 于读者是"导读".\\

---

Awesome Python3 WebApp 这个博客系统, 我已经部署到服务器上了.


地址       [googlegeeks.xyz:23333](http://googlegeeks.xyz:23333)
管理员帐号 kissg@kissg.com
密码       kissgkissg

---

## 正文

首先, 我觉得最重要的, 要有大局观, 即整体把握能力. 这也正是我作为"过来人", 能为学习中的各位提供的最大帮助.

[廖老师第15天的实战](http://www.liaoxuefeng.com/wiki/0014316089557264a6b348958f449949df42a6d3a2e542c000/0014323392805925d5b69ddad514511bf0391fe2a0df2b0000)已经给出了一个系统的全局模型:

![Nginx-awesome-MySQL](nginx-awesome-mysql.png)

- `Nginx`作为Web服务器, 用于处理静态资源, 同时作为反向代理将动态请求交给python代码处理;
- `awesome`, 即我们用python3写的webapp, 负责事务处理, 并与数据库交互;
- `MySQL`, 提供数据的存储与处理服务.

整个项目的重点, 就在于作为`Nginx`后端和`MySQL`前端的`awesome`.

让我们先来看看, 开发`awesome`主要用到了哪些库. 用好工具的基础, 是了解, 因此有必要花点时间了解一下这些工具都干嘛的:

- `jinja2` - 前端模板引擎. 所有的前端页面都是通过`jinja2`调用模板并渲染得到的 \\
详情: [官方文档](http://jinja.pocoo.org/docs/dev/) \| [我的简单笔记](https://github.com/Engine-Treasure/learning-notebook/blob/master/jinja2-note.markdown)
- `aiohttp` - 基于`asyncio`的异步http框架. 此处主要用于实现 web 服务器, 提供单线程多用户高并发支持\\
详情: [官方文档](http://aiohttp.readthedocs.io/en/stable/) \| [我的简单笔记](https://github.com/Engine-Treasure/learning-notebook/blob/master/aiohttp-note.markdown)
- `aiomysql` - mysql的python异步驱动程序\\
详情: [官方文档](http://aiomysql.readthedocs.io/en/latest/)
- `asyncio` - python内置的异步io库. 几乎所有的异步IO操作都与之有关.\\
详情: [官方文档](https://docs.python.org/3/library/asyncio-task.html)

如上所示, `awesome`为了实现对事务的高效处理, 使用了许多`异步`框架与提供`异步IO`能力的库. 如果忘了什么是`异步IO`, 可翻看[廖老师之前的教程](http://www.liaoxuefeng.com/wiki/0014316089557264a6b348958f449949df42a6d3a2e542c000/00143208573480558080fa77514407cb23834c78c6c7309000). 简而言之, 就是**当程序需要执行耗时的IO操作时, 只发出IO命令, 并不等待IO结果, 让CPU执行其他任务. 当IO结束时, 再通知CPU处理**.

在讲解`awesome`的实现之前, 来看看`awesome`是如何工作的, 或许能对各位接下来的编程有所帮助. 以下是我运行`app.py`后的日志(你也可以观察`app.py`中`init(loop)`的初始化步骤):

```shell
[2016-05-10 15:30:01] found model: User (table: users)
...
[2016-05-10 15:30:01] found model: Blog (table: blogs)
...
[2016-05-10 15:30:01] found model: Comment (table: comments)
...
[2016-05-10 15:30:01] create database connection pool...
# ==============================================================================
[2016-05-10 15:30:01] init jinja2...
[2016-05-10 15:30:01] set jinja2 template path: /home/kissg/Developing/awesome-python3-webapp/www/templates
# ==============================================================================
[2016-05-10 15:30:01] add route GET /api/blogs => api_blogs(page)
...
[2016-05-10 15:30:01] add route get /signin => signin(
# ==============================================================================
[2016-05-10 15:30:01] add static /static/ => /home/kissg/Developing/awesome-python3-webapp/www/static
# ==============================================================================
[2016-05-10 15:30:01] server started at http://127.0.0.1:9000
```

由日志可知, 系统启动之后进行了以下初始化操作:

1. 建立model, 简单点说就是建立python中的`类`与数据库中的`表`的映射关系\\
***补充***: `found model: User (table: users)` 可在`orm.py` 中元类的定义中找到, 可见`orm.py`的重要性. (事实上,我在这一天的内容上停顿了一个多星期, 就是为了**理解元类**, **理解ORM**. 本人特地写了篇[博客](http://kissg.me/2016/04/25/python-metaclass/)记录元类的点点滴滴, 有兴趣的同学可看下)
2. 创建全局数据库连接池\\
***补充***: `create database connection pool` 同样可在`orm.py`中找到. 按廖老师的说法, 这是为了使每个http请求都可以从连接池中直接获取数据库连接, 而不必频繁地打开关闭数据库连接. 现在你真的意识到`orm.py`的重要性了吗? 很重要, 与数据打交道的活在其中都做了定义
3. 初始化`jinja2`引擎, 并设置模板的路径\\
***补充***: 两条日志都可在`app.py`的jinja2初始化函数中找到. 注意, 此初始化函数之前, 已经创建了`aiohttp.web.Application`对象, 即所谓的`webapp`. 该函数主要是初始化了`jinja2 env`(环境), 并将`jinja2 env`绑定到`webapp`的`__templating__`属性上. 后一条日志指出了模板的路径, 这是因为在初始化`jinja2 env`时, 指定了加载器(`loader`)为文件系统加载器(`FileSystemLoader`).
4. 注册处理器(handler)\\
***补充***: `add route ...` 日志可在`corow.py`中找到. `事务处理`的三要素: `方法(http method)` &  `路径(path)` & `处理函数(func)`. 将三者连起来看就是, 将对某路径的某种http请求交给某个函数处理, 而该函数就称为某路径上某种请求的处理器(handler).
5. 添加静态资源
6. 创建服务器对象, 并绑定到socket

仔细看, 你会发现, 从上到下的过程就是一个实现`MVC`模型的过程: `建立model` -> `构建前端视图` -> `注册处理控制`. 而廖老师的实战过程也是按这个顺序一步步下来的.

系统启动之后, 当我访问博客首页, 在首页完全加载出来之后, 日志如下所示, 我们不妨以此来一览事务处理的过程:

```shell
[2016-05-10 17:48:28] Request: GET /
[2016-05-10 17:48:28] check user: GET /
[2016-05-10 17:48:28] Response handler...
# =============================================================================
[2016-05-10 17:48:28] call with args: {}
# =============================================================================
[2016-05-10 17:48:28] SQL: select count(id) _num_ from `blogs`
[2016-05-10 17:48:28] rows return 1
# =============================================================================
[2016-05-10 17:48:28] 127.0.0.1 - - [10/May/2016:09:48:28 +0000] "GET / HTTP/1.1" 200 3513 "-" "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/49.0.2623.110 Safari/537.36"
```

我们还是通过找出日志的出处来分析:

- `Request: method path`, `check user: method path`, `Response handler ...` 分别可在`app.py`的`logger_factory`, `auth_factory`和`response_factory`中找到.
- `call with args: {}` 可在`coroweb.py`中`RequestHandler`的`__call__`方法中找到
- `SQL: sql-statement` 可在`orm.py`中封装了sql语句的函数`select`和`execute`中找到. `rows return n` 仅在`orm.py`的`select`函数中找到.
- 最后一条日志, 对不起~我没找到- -.

找到了这些日志的出处之后, 通过打印日志的先后顺序, 就可以理出事务处理的脉络了:

1. 当客户端发起请求时, 由于`中间件(middlewares)`的存在, 事务处理将被拦截. 根据[aiohttp文档](http://aiohttp.readthedocs.io/en/stable/web.html#middlewares)的说法, `middleware`提供了自定义`handler`的机制, 可以简单地理解成`装饰器(decorator)`;
2. 根据日志, 我们可以知道, 在事务处理之前, `logger_factory`首先执行, 打印一个收到请求的日志;
3. 接着`auth_factory`执行, 验证用户是否登录以及用户权限, 并将用户信息绑定到请求上;
4. 之后进入`response_factory`. `response_factory`实际是根据事务处理的结果向客户端发回响应. 因此, 在`response_factory`中, 事务处理先被执行;
5. 我们注册到webapp上的`handler`实际上是一个`RequestHandler`对象, 由于实现了`__call__`方法, 因此`RequestHandler`对象可以当作函数使用([Duck typing](https://en.wikipedia.org/wiki/Duck_typing)). 因此, 每次事务处理都会打印`call args ...`
6. 此例中, 我们的请求是针对`/`的`GET`, 处理过程中调用了`Blog.findAll`方法, 间接调用了`orm.py`中定义的`select`方法, 因此会有那2条sql相关的日志
7. 事务处理返回的结果是带有模板信息的字典, `response_factory`根据这个结果, 加载模板, 并将渲染之后的`html`作为响应发回给客户端.

以上就是一次事务处理的基本过程, 条理应该是很清晰的.

在对系统有了一个全局概念之后, 编程应该会容易不少, 至少我们知道了要写些什么. 接下来, 看看每个脚本都做了什么:

1. `app.py`: **web app骨架**(廖老师的说法). 在这里, 初始化了`jinja2`环境, 实现了各`middleware factory`, 最重要的是——创建了app对象, 完成系统初始化
2. `orm.py`: 建立ORM(Object, Relational Mapping, 对象关系映射), 此处所有代码都是为此服务的——创建了全局数据库连接池, 封装sql操作, 自定义[元类](http://kissg.me/2016/04/25/python-metaclass/), 定义Model类
3. `models.py`: 在ORM基础上, 建立具体的类, 相对比较简单
4. `coroweb.py`: web框架(廖老师的说法), 说白了就是事务处理(`handler`)的基础准备. 此处定义了`get`与`post`装饰器, 与之对应的是`handler`的`http method`部分概念. 又定义了`RequestHandler`类, 前文说过, 注册到app上的其实就是`RequestHandler`对象, 因为实现了`__call__`方法, 所以可以当函数使用. 可以说, `RequestHandler`起了包装`handler`的作用. 还有一些辅助函数, 比如添加静态文件, 自动注册`handler`等
5. `config*.py`: 配置文件. 在这里多嘴一句, 将默认配置文件与自定义配置文件分离真的是好主意. 很多软件, 比如`rime`, `sublime text`都是这种思路, 没想到这里就用上了.
6. `handlers.py`: 全部的`handlers`及一些辅助函数, 包括验证用户权限, 检查cookie等.
7. `apis.py`: 定义了`APIError`类与`Page`类, 分别用于api错误提示与页面管理
8. `pymonitor.py`: 检测`www`目录下`.py`文件的修改, 自动重启`app.py`\\
(这个脚本不算系统的一部分, 但它给我的启发意义是巨大的. 受其与`fabfile.py`的影响, 以及自己的一些经历, 我发现编程的意义之一就是实现`自动化`. 原谅我, 又多嘴了.)

以上就是对各脚本的简单介绍与梳理, 具体的还请看[廖老师的教程](http://www.liaoxuefeng.com/wiki/0014316089557264a6b348958f449949df42a6d3a2e542c000/001432170937506ecfb2f6adf8e4757939732f3e32b781c000). 我的建议是, 大家编程的时候, 最好有目标, 至少应该知道**要做什么**, 这也是我把这些模块都拎一拎的原因所在. 而根据我的经验, `app.py`, `orm.py`, `coroweb.py`, `handlers.py`几个模块相对比较重要, 建议大家多花点时间, 好好理解.

正文内容就到这里吧, 我也不知道接下来该讲什么了. 更多的, 还是见`代码与注释`吧.

## 小结

作为一个大白, 这次webapp的开发经历给我的感受就如开头引用的偈语所言:

> 看山是山, 看山不是山, 看山还是山

没接触webapp开发之前, 我的想法是: 这个不难, 无非就是请收请求, 根据请求内容进行相应处理, 再返回响应. 这就对应看山是山(1)的阶段.

等到真正开始实战, 我懵逼了. 从第三天开始, 完全不会, 之前学的数据库之前全还给老师了. 当时想过放弃, 后来告诉自己, "勇敢地抄袭吧, 少年! 自己多花点时间理解, 总会有收获的." 然后我真的就这样做了, 也坚持下来了, 最后发现收获真的不少. 我慢慢接触到一些新的概念, 比如`MVC`, `MVVM`等等, 也学会一些技巧, 比如`通过linux软链接实现版本控制`, `watchdog与subprocess提高开发效率`等等. 我也是到最后才真的发觉, 廖老师的教程真的是好教程. 为此, 我还特地给他小额赞助了- -. \\
(插入语: **评判事情好与不好的一个标准可以是, 有没有收获**)

我花了这2天的时间来梳理总结, 发现整个过程, 真的不算复杂, 无非就是...(- -.)

以此文, 与诸君共勉

## 部分学习材料

<p id="reference"></p>

关于元类:

- [e-satis在stackoverflow上的回答](http://stackoverflow.com/questions/100003/what-is-a-metaclass-in-python/6581949#6581949)
- [上述的中译版](http://blog.jobbole.com/21351/)
- [我的元类总结](http://kissg.me/2016/04/25/python-metaclass/)

我看过的一些库的文档:

- [aiohttp官方文档](http://aiohttp.readthedocs.org/en/stable/web.html)
- [aiomysql官方文档](http://aiomysql.readthedocs.io/en/latest/index.html)
- [jinja2官方文档](http://jinja.pocoo.org/docs/latest/)
- [jinja2中文版文档](http://docs.jinkan.org/docs/jinja2/)(翻译不全, 不如看原版)
