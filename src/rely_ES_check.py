"""
3.2基于实体库的一致性核查

版本迭代情况：
[脱敏] 版本迭代记录
[脱敏] 版本迭代记录
[脱敏] 版本迭代记录

库依赖情况：
无库依赖

本组件存在外部依赖：
外部依赖：知识实体建模过程的实体库（此处用桩程序替代）

配置变量使用情况：
无
"""

from typing import List, Optional
from src.stack import has_entity_false

def check_entity_consistency(entity: str, pos_list: Optional[List[int]] = None) -> bool:
    """
    基本功能：
        对于给定的字符串和整数列表，来判断待检查实体（即给定的字符串）是否存在于指定查询的实体库中

    函数参数：
        entity：待检查实体，一个字符串
        pos_list:指定查询的实体库词性范围，一个整数列表（整数列表可以留空，此时默认指定查询全部实体库）
 
    返回值：
        bool值：True存在于指定查询的实体库，False为不存在

    异常处理：
        抛出外部依赖的异常
    
    运行日志记录：
        无运行日志记录
    
    基本思想：
    1. 使用知识实体建模过程模块中的内容，查找待检查实体是否存在于各个实体库中
    2. 如果待检查实体能在实体库中查到，返回结果为True，否则返回False
    """

    # 如果pos_list为空，默认查询全部实体库
    if pos_list is None or len(pos_list) == 0:
        search_pos_list = [1, 2, 3, 4]
    else:
        search_pos_list = pos_list

    # 词性映射数组
    pos_types = ["noun", "verb", "adjective", "adverb"]

    for pos_code in search_pos_list:
        if has_entity_false(entity, pos_types[pos_code - 1]):
            return True
            
    return False
