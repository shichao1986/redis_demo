# coding: utf-8

import sys
import time
import redis

REDIS_HOST = '10.6.3.29'
REDIS_PORT = 16379

pool = None

p = lambda msg,a:print('{}:{}'.format(msg, a))

# 分布式锁一半和pipeline 事务共同使用
def lock(r, name, value):
    while not r.set(name, value, nx=True):
        pass
    # 设定锁的超时时间，防止crush导致其他线程卡死
    # 同时使用pipeline watch 监控锁的改变，防止
    # 自身处理过慢，导致锁自动过期后与其他线程
    # 共同操作
    r.setex(name=name, time=20, value=value)

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

    r.set('ex_test', 1, ex=30)

    # 更新redis中的值的内容不会影响之前设定的超时时间
    # for i in range(20):
    #     r.incr('ex_test', 1)
    #     time.sleep(1)
    # r.set('ex_test', 1, ex=30)

    print(r.get('testtttt'))
    r.set('sss:sss:ddd/222', 222)

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
    # 本函数执行成功时返回被pop出的值，若src list中没有没有值则返回None
    # 特别的，当src 与 dst 相同时， 实际上是一种环形队列的实现，client对该队列
    # 的pop和push动作一起执行，防止了pop后client挂掉导致队列变短的问题，使用
    # rpoplpush对环形队列进行遍历时无法对队列的内容进行修改
    ret = r.rpoplpush('list1', 'list2')
    p('rpoplpush list1 list2', ret)
    ret = r.rpoplpush('list1', 'list2')
    p('rpoplpush list1 list2', ret)

    # 函数brpoplpush 为rpoplpush的阻塞版，意为一直等待src list有元素可以push入dst list
    # 该阻塞可用于消息的指定分发，弥补了pub/sub使用广播方式的不足，例子剑redis_subscribe.py
    pass

def Set_examples(r, r1):
    print(r.delete('set1', 'set2', 'set3', 'set4', 'set5', 'set6', 'set7'))

    # sadd 返回成功添加入集合中的元素的个数
    print(r.sadd('set1', 'abc'))
    print(r.sadd('set1', 'ddd', 123, 4, 5, 6, 7, 8, 9))
    print(r.sadd('set1', 123))
    print(r.scard('set1'))

    print(r.sadd('set2', 'abc'))
    print(r.sadd('set2', 'ddd', 123, 4, 5, 6))
    print(r.sadd('set2', 123))
    print(r.scard('set2'))

    print(r.sadd('set3', 8))

    # sdiff 返回在第一个集合中，但是不再后续所有集合中的元素组成的集合
    # 即差集运算
    print(r.sdiff(['set1', 'set2']))
    print(r.sdiff('set1', 'set2', 'set3'))

    # sdiffstore 将sdiff 函数返回的集合存储到指定的集合中去
    # 返回值为将要存入的元素的数量,该返回值实际上为
    # scard(sidff(keys))，并不是真正存入的数量
    print(r.sdiffstore('set4', 'set1', 'set2', 'set3'))
    print(r.sdiffstore('set4', 'set1', 'set2', 'set3'))
    print(r.sdiffstore('set4', 'set1', 'set2', 'set3'))
    print(r.sdiffstore('set4', 'set1', 'set2', 'set3'))
    print(r.sdiffstore('set4', 'set1', 'set2', 'set3'))

    # 返回交集
    print(r.sinter('set1', 'set2'))
    print(r.sinter('set1', 'set2', 'set3'))

    # 将交集插入指定集合，返回值为交集的元素个数
    print(r.sinterstore('set5', 'set1', 'set2'))
    print(r.sinterstore('set5', 'set1', 'set2'))

    # 返回并集
    print(r.sunion('set2', 'set3'))

    # 将并集插入指定集合，返回值为并集的元素个数
    print(r.sunionstore('set6', 'set2', 'set3'))
    print(r.sunionstore('set6', 'set2', 'set3'))

    print(r.sismember('set1', 'abc'))
    print(r.sismember('set1', 'abcc'))
    print(r.smembers('set1'))

    # 移除集合中所有的指定value的元素，返回值为成功移除的元素个数
    print(r.srem('set1', 'kkk'))
    print(r.srem('set1', 'ddd'))
    print(r.srem('set1', 'abc', 123, '000'))
    print(r.smembers('set1'))
    print(r.smembers('set2'))

    # 将集合src 中的 val  添加入集合 dst
    # src 中不存在val 返回false
    # src 中存在val ，dst 不存在 返回false
    # src 中存在val ，dst 存在 返回true  （无论dst中是否已经有了 val）
    print(r.smove('set1', 'set2', 'aaa'))
    print(r.smove('set1', 'set2', 5))
    print(r.smove('set1', 'set2', 7))
    print(r.smove('set1', 'set7', 7))
    print(r.smembers('set2'))
    print(r.smembers('set7'))

    # 获取集合中的指定数量的随机元素
    print(r.srandmember('set1', number=0))
    print(r.srandmember('set1', number=1))
    print(r.srandmember('set1', number=3))
    print(r.srandmember('set1', number=10))

    # 随机pop出指定集合中的 number个元素
    print(r.spop('set1', count=0))
    print(r.smembers('set1'))
    print(r.spop('set1', count=1))
    print(r.smembers('set1'))
    print(r.spop('set1', count=3))
    print(r.smembers('set1'))
    print(r.spop('set1', count=5))
    print(r.smembers('set1'))

    # sscan sscan_iter 与 hscan hscan_iter的用法类似,不再介绍

    pass

# 有序集合经常用于排名系统
# bzminpop可以扩展成select功能
def Zset_examplse(r, r1):
    r.delete('zset1','zset2','zset3', 'zset4')
    # zadd 创建 和 更新 有序集合中的元素，返回值为添加的元素的个数
    zdict = dict(a=1,b=2,c=3)
    print(r.zadd("zset1", zdict))
    zdict = dict(a=1, b=4, c=3, d=5)
    print(r.zadd("zset1", zdict))

    # nx=True 时仅创建不更新，重复的元素忽略
    zdict = dict(a=1,b=2,c=3)
    print(r.zadd("zset2", zdict, nx=True))
    zdict = dict(a=1, b=4, c=3, d=5)
    print(r.zadd("zset2", zdict, nx=True))

    # xx=True 时仅更新不创建，不存在的元素忽略
    zdict = dict(a=1, b=2, c=3)
    print(r.zadd("zset3", zdict, xx=True))
    zdict = dict(a=1, b=2, c=3)
    print(r.zadd("zset3", zdict))
    zdict = dict(a=1, b=4, c=3, d=5)
    print(r.zadd("zset3", zdict, xx=True))

    # nx=True xx=True， 既不创建，也不更新，无实际意义
    zdict = dict(a=2, b=12, c=13, e=50)
    print(r.zadd("zset3", zdict, xx=True))
    print(r.zrange('zset3', 0, -1))

    # ch=True 返回值此时为发生变化的元素，包括新创建的元素，和被更新的元素
    zdict = dict(a=2, b=4, c=13, e=50)
    print(r.zadd("zset3", zdict, ch=True))
    print(r.zrange('zset3', 0, -1))

    # incr=True zdict中只能包含一对，且返回值变为key增加过val后的最新结果
    # 若增加的key值不存在，则为在zset中创建key/val
    # 注意：此时设置nx 和 xx标志可能会导致异常的发生
    zdict = dict(a=5)
    print(r.zadd("zset3", zdict, ch=True, incr=True, xx=True))
    print(r.zrange('zset3', 0, -1))
    zdict = dict(dd=5)
    print(r.zadd("zset3", zdict, ch=True, incr=True))

    # 获取有序集中的指定区间的元素， withscores是否返回score desc是否降序，默认为升序
    # score_cast_func 为分数的转换格式，默认为float
    print(r.zrange('zset3', 0, -1, withscores=True, desc=False, score_cast_func=float))

    # score 必须为一个可以转换成float类型的数
    zdict=dict(a=1, b=2, c='3', d='4.44')
    zdict['1'] = 1
    print(r.zadd('zset4', zdict))
    print(r.zcard('zset4'))
    print(r.zcount('zset4', 0, 3))

    # 返回增加过后的值
    print(r.zincrby('zset4', '0.11', 'a'))
    # 不存在的值会创建，并以amount为初值
    print(r.zincrby('zset4', '0.11', 'k'))

    # 将keys的交集合并到dst有序集中
    print(r.zinterstore('zset5', ['zset3','zset4'], aggregate='MIN'))

    # 将keys的并集合并到dst有序集中
    print(r.zunionstore('zset6', ['zset3', 'zset4'], aggregate='SUM'))

    # 按照字典（英文字母字典排序）序列限制min和max区间，
    # 注意使用字典序列返回区间的所有函数的使用隐含前提
    # 是该有序集合内的所有元素的分数相同，在有序集合中
    # 相同分数的元素之间的顺序是通过字典序排列的，比如
    # c=10，再插入a=10，a的顺序会排列在a之前，所以字典序
    # 确定区间的函数都基于这个前置条件，查找时从有序集中
    # 的第一个元素开始，依次和max进行比较，从最后一个元素
    # 开始，依次和min进行比较，确定两边边界后返回元素的数量
    # 所以对于分数不相同的有序集合使用字典序相关的所有函数
    # 都是不恰当的
    print('zlexcount test')
    print(r.zrange('zset6', 0, -1, withscores=True, desc=False, score_cast_func=float))
    print(r.zlexcount('zset6', min='[f', max='[k'))


    # 与zrange 类似，区间选区时使用score
    print(r.zrangebyscore('zset6', 0, 100, withscores=True, score_cast_func=float))
    print(r.zrevrangebyscore('zset6', 100, 0, withscores=True, score_cast_func=float))

    # 获取指定val的排名
    print(r.zrank('zset6', 'dd'))
    # 获取指定val的反向排名，即倒数名次
    print(r.zrevrank('zset6', 'dd'))

    # 删除有序集中的vals，返回成功删除的val的个数
    print(r.zrem('zset6', '11', '22', 'cc'))
    print(r.zrem('zset6', '11','22', 'cc', 'a'))

    # 按照字典序获取指定区间的元素名称，可以通过start 和 num 对返回的结果进行切片，再返回经过切片后的结果
    print(r.zrangebylex('zset6', '[a', '[z'))

    # 此时的有序集中的val的顺序为 [b'k', b'1', b'd', b'dd', b'b', b'a', b'c', b'e']
    # 但是下述例子返回的是8，而不是2，所以要确认zlexcount函数的执行逻辑需要看redis源码
    print(r.zlexcount('zset6', '[a', '[z'))
    print(r.zrangebylex('zset6', '[a', '[z', start=1, num=2))
    print(r.zrangebylex('zset6', '[a', '[z', start=10, num=1))

    # zrevrangebylex 与 zrangebylex 用法类似，是字典排序的一个倒序过滤
    # 返回的结果顺序与 zrangebylex 正好相反
    print(r.zrevrangebylex('zset6', '[z', '[a'))
    print(r.zrevrangebylex('zset6', '[z', '[a', start=1, num=2))
    print(r.zrevrangebylex('zset6', '[z', '[a', start=10, num=1))

    # pop 出给定有序集合中最大或最小的count个元素
    print(r.zpopmax('zset6'))
    print(r.zpopmin('zset6'))
    print(r.zpopmax('zset6', count=2))
    print(r.zpopmax('zset6', count=20))
    print(r.zrange('zset6', 0, -1, withscores=True, desc=False, score_cast_func=float))

    # 按照keys中的有序集的从左到右的顺序pop出第一个非空的元素
    # 返回值为（key， val， score）
    # 当timeout参数设置为0时为阻塞等待
    # 显而易见的是该方法的使用场景类似与select函数，多个有序集为不同的fd
    # 有序集中的val为信息，score可以用于记录到达顺序
    print(r.bzpopmax(['zset5','zset4']))
    print(r.bzpopmax(['zset5', 'zset4']))
    print(r.bzpopmax(['zset5', 'zset4']))
    print(r.bzpopmax(['zset5', 'zset4']))
    print(r.bzpopmax(['zset5', 'zset4']))
    print(r.bzpopmax(['zset5', 'zset4']))
    print(r.bzpopmax(['zset5', 'zset4']))
    print(r.bzpopmax(['zset5', 'zset4']))

    # bzmopmin 用法同bzpopmax，返回的为最小的值

    pass

# 事务
def Pipeline_examples(r, r1):
    # 初始化分布式锁,锁主共享资源
    lock_init(r, 'pipe_lock')
    r.set('pipe', 100)
    with r.pipeline(transaction=True) as p:
        try:
            lock(r, 'pipe_lock', 1)
            # 用锁锁住共享资源
            # watch仅需要监控锁即可
            # 共享资源的操作全部用pipeline的事务实现
            # 如果锁被改动，则放弃事务操作
            # 事务操作本身具有原子性，在事务之前加锁是
            # 为了保证参与事务中的共享资源的数据是最新的
            p.watch('pipe_lock')
            p.multi()
            p.decr('pipe', amount=1)
            p.decr('pipe', amount=2)
            p.decr('pipe', amount=3)
            ret = ''
            ret = p.execute()
        except Exception as e:
            # 锁被篡改，取消事务
            print(e)
            p.unwatch()
        finally:
            unlock(r, 'pipe_lock')
            print(ret)
            # 事务执行成功后，watch自动失效

    pass

# 批处理
def Pipeline_examples2(r, r1):
    with r.pipeline(transaction=False) as p:
        p.lpush('pipe_list1',1)
        p.lpush('pipe_list2', 1)
        p.lpush('pipe_list3', 1)
        p.lpush('pipe_list4', 1)
        p.lpush('pipe_list5', 1)
        p.lpush('pipe_list6', 1)
        ret = p.execute()
        print(ret)

def main(argv=None):
    if not argv:
        argv = sys.argv

    global pool

    pool = redis.BlockingConnectionPool(max_connections=10, host=REDIS_HOST, port=REDIS_PORT)
    # 使用此方法连接redis时 所有连接参数的配置在BlockingConnectionPool中配置，例如db=0，1，2，3...
    r = redis.Redis(connection_pool=pool)

    r1 = redis.Redis(host=REDIS_HOST, port=REDIS_PORT, db=1)

    String_examples(r, r1)

    # Hash_examples(r, r1)

    # List_examples(r, r1)

    # Set_examples(r, r1)

    # Zset_examplse(r, r1)

    # Pipeline_examples(r, r1)
    #
    # Pipeline_examples2(r, r1)

if __name__ == '__main__':
    sys.exit(main(argv=None))