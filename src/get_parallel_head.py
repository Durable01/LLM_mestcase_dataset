"""
3.24 并置规则的规则头提取

版本迭代情况：
[脱敏] 版本迭代记录

库依赖情况：
无

本组件无外部依赖和文档依赖

配置变量使用情况：
SENTENCE_SPLIT_PUNCTUATIONS：足够切分句子的标点符号列表
"""
import os
import sys
base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(base_dir)

from config import config_choice

def get_parallel_head(knowstr, parallelrelation):
    """ 
    从给定的知识文本knowstr与并置关系parallelrelation中提取并置规则头。

    找到并置项在knowstr中最早出现的位置，并提取其并置规则头。
    提取时按最后一个足够切分句子的标点截断，若无标点则截到并置项起始位置。
    最后把“如下”“以下”改为“的”。

    参数：
        knowstr：知识字符串。
        parallelrelation：并置关系列表。

    返回值：
        head：并置规则头，一个字符串。
    """
    # 找每个并置项在knowstr中的首次出现位置
    positions = []
    for para in parallelrelation:
        text = para["Parallel"]
        # 查找匹配位置
        pos = knowstr.find(text)
        positions.append(pos)

    # pos1为所有并置关系中，出现位置最早的那个并置关系的位置
    pos1 = min(positions)

    # 取并置项之前的前缀
    prefix = knowstr[0:pos1]

    # pos2记录最后一个足够切分句子的标点符号位置
    pos2 = -1
    for punc in config_choice.SENTENCE_SPLIT_PUNCTUATIONS:
        index = prefix.rfind(punc)
        if index > pos2:
            pos2 = index

    if pos2 >= 0:
        # 有标点，截到标点处
        head = knowstr[0:pos2]
    else:
        # 无标点，截到并置项起始位置
        head = knowstr[0:pos1]

    # 把“如下”“以下”改为“的”
    head = head.replace("如下", "的").replace("以下", "的")
    return head
