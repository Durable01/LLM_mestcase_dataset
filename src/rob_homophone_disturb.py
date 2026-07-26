"""
3.8 字典检索的非敏感错别字干扰-覆盖语义鲁棒性
用pypinyin构建同音字索引并随机替换非实体叶子节点汉字

版本迭代情况：
[脱敏] 版本迭代记录
[脱敏] 版本迭代记录
[脱敏] 版本迭代记录
[脱敏] 版本迭代记录

库依赖情况：
无

本组件存在文档依赖
文档依赖：pypinyin库，同音词表

配置变量使用情况：
无
"""
import random
import os
from time import time

from pypinyin import pinyin, Style

from src.make_json import make_JSON

class RobHomophoneDisturb:
    """
    字典检索的非敏感错别字干扰-覆盖语义鲁棒性

    用pypinyin构建同音字索引并随机替换非实体叶子节点汉字
    读取all_3500_chars文档，构建拼音->汉字索引

    类变量：
        _phonetic_index:汉字索引
        log_manager:日志管理组件
        knowid:知识id
    """
    def __init__(self,log_manager):
        """
        参数：
            log_manager：日志管理类
        
        异常处理：
            崩溃(corrupt)情况:
                1.类构造函数读取文档时抛出异常
        """

        self._phonetic_index = {}
        self.log_manager = log_manager
        self.knowid = ""
        try:
            path = os.path.join(os.path.dirname(__file__), '..', 'document', 'all_3500_chars.txt')
            with open(path, encoding='utf-8') as f:
                chars = [line.strip() for line in f if line.strip()]

        except Exception as e:
            self.log_manager.generate_error_log(time(), self.knowid, "rob_homophone_disturb", "corrupt", 2, str(e))
            return
        for character in chars:
            pinyin_list = pinyin(character, style=Style.NORMAL, heteronym=True, strict=False)[0]
            for single_pinyin in pinyin_list:
                if single_pinyin:
                    self._phonetic_index.setdefault(single_pinyin, []).append(character)

    def _get_homophones(self, character):
        '''
        对单个字character，返回除它自身外的同音字

        参数：
            character：单字

        返回值：
            同音字列表
        '''
        pinyin_list = pinyin(character, style=Style.NORMAL, heteronym=False, strict=False)[0]
        if not pinyin_list:
            return []
        pinyin_no_tone = pinyin_list[0]
        homophone_list = self._phonetic_index.get(pinyin_no_tone, [])
        return [h for h in homophone_list if h != character]

    def _extract_leaves(self, node, text, leaves):
        '''
        遍历语法树，提取所有叶子节点信息
        参数：
            node: 当前节点
            text: 知识内容字符串
            leaves: 存储叶子节点的列表

        返回值：
            无
        '''
        # 检查是否为叶子节点
        if not node.get("children"):
            # 获取节点文本
            node_text = text[node["start"]:node["end"]]
            
            # 创建叶子节点
            leaf = {
                "entity": node_text,
                "wordtype": self._map_nodetype_to_wordtype(node["nodetype"]),
                "position": node["start"]
            }
            leaves.append(leaf)
        else:
            # 处理子节点
            for child in node["children"]:
                self._extract_leaves(child, text, leaves)

    def _map_nodetype_to_wordtype(self, nodetype):
        '''
        将节点类型nodetype映射到词性wordtype
        1: 名词, 2: 动词, 3: 形容词, 4: 副词, 0: 其他

        参数：nodetype：节点类型

        返回值：词性对应数值
        '''
        noun_tags = ["NP", "NN", "NR", "NT", "NX"]  # 名词短语/名词
        verb_tags = ["VP", "VV", "VE"]              # 动词短语/动词（把介词和关系动词"VC"剔除了，因为替换VC不会影响整体语义）
        adj_tags = ["AP", "ADJP", "JJ"]             # 形容词短语/形容词
        adv_tags = ["ADVP", "AD"]                   # 副词短语/副词
        
        if nodetype in noun_tags:
            return 1  # 名
        elif nodetype in verb_tags:
            return 2  # 动
        elif nodetype in adj_tags:
            return 3  # 形
        elif nodetype in adv_tags:
            return 4  # 副
        else:
            return 0  # 其他

    def generate_choice(self, knowid, knowstr, knowcata, knowtree):
        """
        生成非敏感错别字干扰项

        参数：
            knowid: 知识唯一标识
            knowstr: 知识描述内容
            knowcata: 知识目录标识
            knowtree: 知识语法树

        返回值：
            选项JSON列表

        异常处理:
            提示(notice)情况:
                1.随机指定的汉字，其同音字不存在
        """
        self.knowid = knowid
        # 主要实体词性（名、动、形容、副）
        PRIMARY_WORDTYPES = [1, 2, 3, 4]
        
        # 从语法树中提取所有叶子节点
        leaves = []
        self._extract_leaves(knowtree, knowstr, leaves)
        
        generate_result = [] # 结果列表
        
        # 筛选非实体单字，并且只保留存在同音字的项（标点符号等会过滤掉）
        candidates_with_homophones = []
        for leaf in leaves:
            entity = leaf["entity"]
            wordtype = leaf["wordtype"]

            if wordtype not in PRIMARY_WORDTYPES and len(entity) == 1:
                homophones = self._get_homophones(entity)
                if homophones:
                    leaf_copy = dict(leaf) # 原leaf的拷贝
                    leaf_copy["_homophones"] = homophones
                    candidates_with_homophones.append(leaf_copy)

        if not candidates_with_homophones:
            # 所有候选都没有同音字，返回空表，异常类型为notice
            self.log_manager.generate_error_log(time(), self.knowid, "rob_homophone_disturb", "notice", 4, "选择的词汇没有同音字")
            return generate_result

        # 随机选一个有同音字的叶子，并从其同音字中随机选择替换字
        selected_leaf = random.choice(candidates_with_homophones)
        char_position = selected_leaf["position"]
        replacement = random.choice(selected_leaf["_homophones"])
        
        # 创建新文本
        new_text = knowstr[:char_position] + replacement + knowstr[char_position+1:]
        
        # 构建选项
        json_choice =make_JSON(knowid + "0800", new_text, True, 2, knowcata)
        generate_result.append(json_choice)

        #如果运行到最后没有问题，就写入运行日志
        self.log_manager.generate_run_log(time(), self.knowid, "rob_homophone_disturb", len(generate_result))
        
        #返回结果
        return generate_result
