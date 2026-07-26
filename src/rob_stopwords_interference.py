"""
3.7 停用词变换的增删干扰 关联语义鲁棒性

版本迭代情况:
[脱敏] 版本迭代记录
[脱敏] 版本迭代记录
[脱敏] 版本迭代记录
[脱敏] 版本迭代记录

库依赖情况:
无

本组件存在文档依赖和内部依赖：
文档依赖：停用词表
内部依赖：调用3.21和3.23接口

配置变量使用情况：
STOPWORDS_FILE_DIR：停用词文件目录路径
"""

import json
from time import time
from typing import List, Dict, Set
from pathlib import Path
from config.config_choice import STOPWORDS_FILE_DIR
from src.log_manager import LogManager
from src.make_json import make_JSON


class RobStopwordsInterference:
    """ 在之前构建了知识语法树的基础上，对其内的停用词进行重复、删除，得到干扰的选项。

        属性：
            log_manager：日志管理类
            path：停用词表路径
            stopwords：停用词集合
    """

    def __init__(self, log_manager):
        """
        类初始化函数
        
        异常处理:
            读取文件抛出异常，属于corrupt情况
            
        参数：
            log_manager：日志管理类
            
        返回值：
            无
        """
        self.log_manager = log_manager
        self.path = STOPWORDS_FILE_DIR
        self.stopwords = set()

        file_path = Path(self.path)
        if not file_path.exists():
            self.log_manager.generate_error_log(time(),"system_init","rob_stopwords_interference","corrupt",2,"停用词表文件不存在。")
            return
            """表为空的情况不处理，继续执行后续代码"""
            
        with open(file_path, 'r', encoding='GBK') as f:
            self.stopwords = {line.strip() for line in f if line.strip()}
            """调用停用词表"""
            
    def _find_stopwords_positions(self, knowstr, knowtree):
        """
        通过start/end属性定位停用词
        返回格式: [{"word": str, "start": int, "end": int}]

        参数：
            knowstr：知识内容。
            knowtree：知识语法树。

        返回值：
            stopwords：知识中的可用停用词列表
        """
        stopwords = []

        def traverse(node: Dict):
            if "start" in node and "end" in node and not node.get("children"):
                word = knowstr[node["start"]:node["end"]]
                if word in self.stopwords:
                    stopwords.append({
                        "word": word,
                        "start": node["start"],
                        "end": node["end"]
                    })
            elif "children" in node:
                for child in node["children"]:
                    traverse(child)

        traverse(knowtree)
        return stopwords

    def generate_choice(self, knowid, knowstr, knowcata, knowtree):
        """
        选项生成函数

        参数：
            knowid：知识唯一标识。
            knowstr：知识内容。
            knowcata：知识所在的目录，指向目录节点的唯一标识。
            knowtree：知识语法树

        返回值：
            generate_result：一个列表，列表中的每个元素为一个满足选项schema的JSON。

        异常处理：
            知识中没有可用停用词，属于notice情况

        运行日志记录：
            成功生成选项时，将生成选项信息写入运行日志。
        """

        generate_result = []
        stopwords = self._find_stopwords_positions(knowstr, knowtree)

        # 知识中没有可用停用词，属于notice情况
        if not stopwords:
            self.log_manager.generate_error_log(time(), knowid, "rob_stopwords_interference", "notice", 3, "知识中没有可用停用词。") 
            return generate_result

        for i, stopword in enumerate(stopwords, 0):
            # 为每个停用词生成两个选项（增+删）
            generate_result.append(make_JSON(knowid + "07" + str(i * 2).zfill(2), knowstr[:stopword["end"]] + stopword["word"] + knowstr[stopword["end"]:],
                                             True, 2, knowcata))

            generate_result.append(make_JSON(knowid + "07" + str(i * 2 + 1).zfill(2), knowstr[:stopword["start"]] + knowstr[stopword["end"]:],
                                             True, 2, knowcata))

        self.log_manager.generate_run_log(time(), knowid, "rob_stopwords_interference", len(generate_result))
        return generate_result
