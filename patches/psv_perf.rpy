init -9 python:
    # PS Vita 性能调优（2026-10-31）
    #
    # 依据：
    #   * Vita 可用内存约 330 MB，renpy.py 里写死 RENPY_LESS_MEMORY=True，
    #     会关掉 im.py 里 keep_preloading 那段的 pinned 预加载；
    #   * 默认 image_cache_size_mb=300（见 renpy/config.py:100），
    #     在 Vita 上等于「永不淘汰」，会把内存吃满然后疯狂 GC；
    #   * hard_rollback_limit=100 每次交互都存状态，弱 CPU 上开销明显。

    # 图片缓存压到 64 MB：够放 ~20 张 1024x768 RGBA，超出就淘汰最旧的。
    # 比默认 300 MB 低，但 Vita 上 300 MB 根本给不出来。
    config.image_cache_size_mb = 64

    # 回滚记录从 100 降到 20。Vita 上每次 interaction 都要深拷贝 store，
    # 100 层会明显拖慢；20 层足够玩家反悔几步。
    config.hard_rollback_limit = 20

    # 少预测几步。默认 32 在读取慢的存储卡上会一次性读进大量资源，
    # 反而挤占解码线程的时间。
    config.predict_statements = 16

    # 自动存档本身就是一次完整序列化 + 写卡，Vita 上是很明显的顿挫。
    # 关掉，改由玩家手动存档（游戏里「另存为」照常可用）。
    config.autosave_frequency = None
