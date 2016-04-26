import orm
from models import User, Blog, Comment
import asyncio

@asyncio.coroutine
def test(loop):
    yield from orm.create_pool( loop =loop, user="root", password="Engine,618251", db="awesome")

    u = User(name="kissg", email="kissg@kissg.com", passwd="110110110", image="handsome")

    yield from u.save()


loop = asyncio.get_event_loop()
loop.run_until_complete(test(loop))
loop.close()
