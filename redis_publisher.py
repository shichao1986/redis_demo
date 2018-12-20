# coding: utf-8

import sys
import time
import redis

REDIS_HOST = '10.6.3.29'
REDIS_PORT = 16379

pool = None

p = lambda msg,a:print('{}:{}'.format(msg, a))

def lock(r, name, value):
    while not r.set(name, value, nx=True):
        pass

def unlock(r, name):
    r.delete(name)

def lock_init(r, name):
    r.delete(name)

def main(argv=None):
    if not argv:
        argv = sys.argv

    global pool

    pool = redis.BlockingConnectionPool(max_connections=10, host=REDIS_HOST, port=REDIS_PORT)
    # 使用此方法连接redis时 所有连接参数的配置在BlockingConnectionPool中配置，例如db=0，1，2，3...
    r = redis.Redis(connection_pool=pool)

    # String 操作
    a = r.set('string_arg1', 'value1')
    p('common set', a)

    # 超时事件会由订阅者接收
    r.set('sub_topic', 222, ex=10)

    # 分布式锁的一种实现，当lcok1不存在时写入，
    # 分布式系统中一个时刻只能有一个服务返回True
    # 即为获取锁
    a = r.delete('lock1')
    p('init lock', a)
    a = r.set('lock1', 'locked', nx=True)
    p('try lock', a)
    a = r.delete('lock1')
    p('release lock', a)

    lock_init(r, 'lock2')
    lock(r, 'lock2', 'locked')
    unlock(r, 'lock2')

    a = r.setrange('offstring', 10, 'start')
    a = r.setrange('offstring', 2, 'ss')
    p('offstring', a)


if __name__ == '__main__':
    sys.exit(main(argv=None))