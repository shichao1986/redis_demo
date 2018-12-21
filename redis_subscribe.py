# coding: utf-8

# 本例程介绍了如何使用redis订阅超时事件的方法
# redis允许订阅事件，参考下边的说明（节选自redis.conf）

# Redis can notify Pub/Sub clients about events happening in the key space.
# This feature is documented at http://redis.io/topics/keyspace-events
#
# For instance if keyspace events notification is enabled, and a client
# performs a DEL operation on key "foo" stored in the Database 0, two
# messages will be published via Pub/Sub:
#
# PUBLISH __keyspace@0__:foo del
# PUBLISH __keyevent@0__:del foo
#
# It is possible to select the events that Redis will notify among a set
# of classes. Every class is identified by a single character:
#
# K Keyspace events, published with __keyspace@<db>__ prefix.
# E Keyevent events, published with __keyevent@<db>__ prefix.
# g Generic commands (non-type specific) like DEL, EXPIRE, RENAME, ...
# $ String commands
# l List commands
# s Set commands
# h Hash commands
# z Sorted set commands
# x Expired events (events generated every time a key expires)
# e Evicted events (events generated when a key is evicted for maxmemory)
# A Alias for g$lshzxe, so that the "AKE" string means all the events.

# 本配置文件中使用   notify-keyspace-events "Ex"  意为仅接收超时事件
# 更详细的介绍参考 https://redis.io/topics/notifications

import sys
import time
import threading
import redis

from redis_publisher import REDIS_PORT, REDIS_HOST

r = redis.Redis(host=REDIS_HOST, port=REDIS_PORT)
expire_event = r.pubsub()
expire_event.psubscribe('__key*@0__:*')

def time_expire():
    for msg in expire_event.listen():
        print('receive time_expire msg:{}'.format(msg))

def queue_arive(list_queue):
    count = 0
    while True:
        # timeout = 0 阻塞
        q, msg = r.brpop(list_queue, timeout=0)
        count += 1
        print('{},{},{}'.format(list_queue,msg,count))
        if list_queue == 'list2':
            # 转发，round robin 方式
            forward_list = 'list2_{}'.format(count%5 + 1)
            r.lpush(forward_list, msg)

def main():
    threading.Thread(target=time_expire, daemon=True).start()
    threading.Thread(target=queue_arive, daemon=True, name='list2', args=('list2', )).start()
    threading.Thread(target=queue_arive, daemon=True, name='list2_1', args=('list2_1',)).start()
    threading.Thread(target=queue_arive, daemon=True, name='list2_2', args=('list2_2',)).start()
    threading.Thread(target=queue_arive, daemon=True, name='list2_3', args=('list2_3',)).start()
    threading.Thread(target=queue_arive, daemon=True, name='list2_4', args=('list2_4',)).start()
    threading.Thread(target=queue_arive, daemon=True, name='list2_5', args=('list2_5',)).start()

    while True:
        time.sleep(1)

    return 0

if __name__ == '__main__':
    sys.exit(main())