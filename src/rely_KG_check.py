'''
3.1 基于知识图谱的一致性核查

版本迭代情况：
[脱敏] 版本迭代记录
[脱敏] 版本迭代记录
[脱敏] 版本迭代记录

库依赖情况：无

本组件存在外部依赖。
外部依赖：知识图谱的一致性核查

配置变量使用情况：无
'''
import sys
import os
base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(base_dir)

# 桩程序
from src.stack import KG_check

def check_KG_consistency(entity_front, relation, entity_back):
    """
    基于给定的三元组，在知识图谱中进行一致性核查

    参数：
        entity_front：KG三元组中第一个实体
        relation：三元组中关系
        entity_back：三元组中第二个实体

    返回值：
        bool值：True表示该三元组在知识图谱中存在（一致）；False表示不一致或核查失败

    异常处理：
        不捕获异常，直接由调用组件处理

    运行日志记录：
        由调用组件实现
    """
    
    result = KG_check(entity_front, relation, entity_back)
    return result













