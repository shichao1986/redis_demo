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

# 用户量采用1000万便于测试，若10亿则在初始化时
# 使用多进程分段启动即可
max_account = 1000000

def delete_online_status(r):
    index = 0
    step = 2048
    sum = 0
    while sum < max_account:
        key_name = 'account_online_status_{}'.format(index)
        r.delete(key_name)
        index += 1
        sum += step

# 注意本函数只能由一个线程执行,实际运行时需要加线程锁，或者分布式锁
def init_online_status(r):
    index = 0
    step = 2048
    sum = 0
    while sum < max_account:
        key_name = 'account_online_status_{}'.format(index)
        r.setrange(key_name, 255, '\0');
        index += 1
        sum += step

def get_online_status(account, r):
    key_index = int(account) // 2048
    word_index = int(account) % 2048
    key_name = 'account_online_status_{}'.format(key_index)
    return r.getbit(key_name, word_index)

def set_online(account, r):
    key_index = int(account) // 2048
    word_index = int(account) % 2048
    key_name = 'account_online_status_{}'.format(key_index)
    r.setbit(key_name, word_index, 1)
    return

def set_offline(account, r):
    key_index = int(account) // 2048
    word_index = int(account) % 2048
    key_name = 'account_online_status_{}'.format(key_index)
    r.setbit(key_name, word_index, 0)
    return

def String_examples(r, r1):
    # String 操作
    a = r.set('string_arg1', 'value1')
    p('common set', a)

    a = r.setrange('offstring', 10, 'start')
    a = r.setrange('offstring', 2, 'ss')
    p('offstring', a)

    # 超时事件会由订阅者接收
    r.set('sub_topic', 222, ex=10)

    # 分布式锁的一种实现，当lcok1不存在时写入，
    # 分布式系统中一个时刻只能有一个服务返回True
    # 即为获取锁
    lock_init(r, 'lock2')
    lock(r, 'lock2', 'locked')
    unlock(r, 'lock2')

    # 大数据应用redis记录10亿用户的在线状态1,000,000,000
    # 每一个value为256个子节，256*8=2048位代表2048个用户
    # 的在线状态
    # delete_online_status(r1)
    # init_online_status(r1)
    acc = '0345621'
    status = get_online_status(acc, r1)
    p('get_online_status', status)
    set_online(acc, r1)
    p('set_online', 1)
    status = get_online_status(acc, r1)
    p('get_online_status', status)
    set_offline(acc, r1)
    p('set_online', 0)
    status = get_online_status(acc, r1)
    p('get_online_status', status)

    # 获取增量id
    id = r.incr('identifiers_1')
    p('identifiers_1', id)
    id = r.incr('identifiers_1')
    p('identifiers_1', id)
    id = r.incr('identifiers_1')
    p('identifiers_1', id)
    id = r.incr('identifiers_1')
    p('identifiers_1', id)
    id = r.incr('identifiers_1')
    p('identifiers_1', id)

def Hash_examples(r, r1):
    r.hset('h_dict1', 'key1', '123')
    r.hset('h_dict1', 'key2', '444')
    r.hset('h_dict1', 'key3', '567')
    # 所有判断是否存在的函数都不能用于高并发的场景，因为仅仅判断状态是不具备线程安全的，
    # 例如hexists，在高并发场景下还需要其他的锁来保证操作的原子性
    ret = r.hexists('h_dict1', 'key1')
    p('hexists', ret)
    all = r.hgetall('h_dict1')
    p('hgetall', all)
    keys = r.hkeys('h_dict1')
    p('hkeys', keys)
    length = r.hlen('h_dict1')
    p('hlen', length)
    vals = r.hvals('h_dict1')
    p('hvals', vals)

    dict_2 = dict(key1=123, key3=444, key2=124)
    r.hmset('h_dict2', dict_2)
    # 所有判断是否存在的函数都不能用于高并发的场景，因为仅仅判断状态是不具备线程安全的，
    # 例如hexists，在高并发场景下还需要其他的锁来保证操作的原子性
    ret = r.hmget('h_dict2', r.hkeys('h_dict2'))
    p('hmget keys', ret)
    ret = r.hmget('h_dict2', 'key1', 'key2')
    p('hmget key1 key2', ret)
    ret = r.hmget('h_dict2', ['key2', 'key3'], 'key1', 'key2')
    p('hmget keys key1 key2', ret)

    hs,data =r.hscan('h_dict2')
    p('hscan hs', hs)
    p('hscan data', data)

    # count 设定返回的data中的最大数量，但是仅作为提示，不一定生效
    # cursor填0意为重新迭代获取，返回值不为0则继续使用改值进行下次迭代
    # 返回值为0意为迭代完成
    # match 匹配固定格式的key
    hs, data = r.hscan('h_dict2', cursor=0, count=100, match='*2')
    p('hscan hs', hs)
    p('hscan data', data)

    # scan 返回当前db下的所有key
    s, data = r.scan()
    p('scan s', s)
    p('scan data', data)

    # count 仅作为提示, redis 自己决定...
    s1, data = r1.scan(count=10)
    p('scan s1', s1)
    p('scan data', data)

    total = []
    # 注意scan_iter返回的是所有的key值，而scan返回的是一些key值组成的list
    # scan_iter是对scan返回的list中的key值的进一步遍历，当然也会执行完全部的scan
    for item in r1.scan_iter():
        total += [item]
    p('scan_iter', total)
    print('scan_iter len={}, setlen={}'.format(len(total), len(set(total))))

    # hash 其他用法与String类似的不再举例

def List_examples(r, r1):
    r.delete('list1')
    r.lpushx('list1', 'xl')
    r.rpushx('list1', 'xr')
    r.lpush('list1', 1)
    # 从左到右的顺序推入左侧，所以后推入的在最左侧
    r.lpush('list1', 2,3,4, 11, 11, 11)

    # 从例子可以看出，右侧推入与书写顺序保持一致，左侧推入则正好相反
    r.rpush('list1', 5, 7, 7, 7, 7, 6, 7)
    r.rpush('list1', 8)
    r.lpushx('list1', 'xl')
    r.rpushx('list1', 'xr')
    p('list1', r.lrange('list1', 0, -1))
    p('list1 len', r.llen('list1'))

    r.linsert('list1', 'before', 3, 13)
    r.linsert('list1', 'after', 13, 7)
    r.linsert('list1', 'after', 13, 7)
    r.linsert('list1', 'after', 13, 7)
    r.linsert('list1', 'after', 13, 7)
    # lset 的index参数越界会抛出异常，而不是像  linsert函数那样当refvalue不存在时返回-1
    # 再错误处理的机制上这两个函数的表现不一致
    r.lset('list1', 0, 10)
    p('list1', r.lrange('list1', 0, -1))
    p('list1 len', r.llen('list1'))

    # 顺序删除2个7
    r.lrem('list1', 2, 7)
    p('list1', r.lrange('list1', 0, -1))
    p('list1 len', r.llen('list1'))
    # 倒序删除2个7
    r.lrem('list1', -2, 7)
    p('list1', r.lrange('list1', 0, -1))
    p('list1 len', r.llen('list1'))
    # 删除全部7
    r.lrem('list1', 0, 7)
    p('list1', r.lrange('list1', 0, -1))
    p('list1 len', r.llen('list1'))
    # 删除的数不存在或者希望删除的数量大于存在的数量都不会有问题
    # 返回值为实际删除的value的数量
    ret = r.lrem('list1', 0, 'k')
    print('ret', ret)
    ret = r.lrem('list1', 3, 11)
    print('ret', ret)
    # lindex函数数当index越界时返回的为None，与lset index越界的处理结果不一致，
    # 可能是因为lindex是读取操作，看重执行的流畅性，而lset是写入操作，看重执行的正确性
    print(r.lindex('list1', 0), r.lindex('list1', -1), r.lindex('list1', 200))

    p(r.lpop('list1'), r.rpop('list1'))
    p('list1', r.lrange('list1', 0, -1))
    p('list1 len', r.llen('list1'))
    # 移除不在此范围内的其他元素
    r.ltrim('list1', 1, -2)
    p('list1', r.lrange('list1', 0, -1))
    # 当范围不正确时，理解为，若列表中的节点的索引值同时满足>=start  and  <= end，则该节点保留，否则去除
    # 与python list[start:end]的不同在于此处有边界为包含，python list的有边界end对应的节点不包含在内
    r.ltrim('list1', 0, 0)
    p('list1', r.lrange('list1', 0, -1))

    # redis实现的简易消息队列， 另一个服务循环使用r.brpop('list2', timeout=0)阻塞读取该队列的数据
    for i in range(100):
        r.lpush('list2', 99)

    # 提供两个队列的原子操作，例如将准备队列中ok的任务，放入等待队列已等待运行
    r.rpoplpush('list1', 'list2')

    # 函数brpoplpush 为rpoplpush的阻塞版，意为一直等待src list有元素可以push入dst list
    # 该阻塞可用于消息的指定分发，弥补了pub/sub使用广播方式的不足，例子剑redis_subscribe.py
    pass

def main(argv=None):
    if not argv:
        argv = sys.argv

    global pool

    pool = redis.BlockingConnectionPool(max_connections=10, host=REDIS_HOST, port=REDIS_PORT)
    # 使用此方法连接redis时 所有连接参数的配置在BlockingConnectionPool中配置，例如db=0，1，2，3...
    r = redis.Redis(connection_pool=pool)

    r1 = redis.Redis(host=REDIS_HOST, port=REDIS_PORT, db=1)

    # String_examples(r, r1)

    # Hash_examples(r, r1)

    List_examples(r, r1)

if __name__ == '__main__':
    sys.exit(main(argv=None))