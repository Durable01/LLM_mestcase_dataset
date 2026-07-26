"""
3.12 并置规则的重组-覆盖一致性

版本迭代情况：
[脱敏] 版本迭代记录
[脱敏] 版本迭代记录
[脱敏] 版本迭代记录
[脱敏] 版本迭代记录
[脱敏] 版本迭代记录

库依赖情况：
jsonschema==4.24.0

本组件存在内部依赖。
内部依赖：调用3.21,3.23接口

配置变量使用情况：
Parallel_SCHEMA：并置关系schema
"""

import json
import random
import jsonschema
from time import time
from jsonschema import validate
from config import config_choice
from src.make_json import make_JSON

class ConsReloadParallelRelation(object):
    """
        并置关系（parallelrelation）重置（reload），

        属性：
            cond_validation_string：并置关系Schema 字符串
            cond_validation_schema：解析后的并置关系Schema
            log_manager：日志管理类
    """

    def __init__(self, log_manager):
        """
        类初始化函数

        参数：
            log_manager: 日志管理类

        返回值：
            无
        """
        self.cond_validation_string = config_choice.Parallel_SCHEMA
        self.cond_validation_schema = json.loads(self.cond_validation_string)
        self.log_manager = log_manager

    def generate_choice(self,knowid,knowstr,knowcata,parallelrelation):
        """
        选项生成函数

        参数：
            knowid：知识唯一标识。
            knowstr：知识内容。
            knowcata：知识所在的目录，指向目录节点的唯一标识。
            parallelrelation：本条知识包含的全部并置关系

        返回值：
            generate_result：一个列表，列表中的每个元素为一个满足选项schema的JSON

        异常处理：
            提示(notice)情况：
                1.jsonschema.exceptions.ValidationError异常
                2.知识没有并置关系
                3.第一条并置关系不在knowstr中
            崩溃(corrupt)情况：
                1.jsonschema.exceptions.SchemaError异常

        运行日志记录：
            成功生成选项时，将生成选项信息写入运行日志。
        """
        #存储最后输出的结果
        generate_result = []
        validate_failed = False
        # 验证输入的并置关系是否符合schema
        try:
            validate(schema=self.cond_validation_schema, instance=parallelrelation)
        except jsonschema.exceptions.SchemaError as e:
            # jsonschema.exceptions.SchemaError异常，属于corrupt情况
            self.log_manager.generate_error_log(time(), knowid, "cons_reload_parallelrelation", "corrupt", 1, str(e))
            validate_failed = True
        except jsonschema.exceptions.ValidationError as e:
            # jsonschema.exceptions.ValidationError异常，属于notice情况
            self.log_manager.generate_error_log(time(), knowid, "cons_reload_parallelrelation", "notice", 8, str(e))
            validate_failed = True

        if validate_failed:
            return generate_result

        # 知识没有并置关系，属于notice情况
        if len(parallelrelation)==0:
            self.log_manager.generate_error_log(time(), knowid, "cons_reload_parallelrelation", "notice", 8, "知识没有并置关系。")
            return generate_result

        # 查找开头部分位置
        first_parallel_str = parallelrelation[0]['Parallel']
        choice_description = self._get_base_desciption(knowstr, first_parallel_str)

        # 第一条并置关系不在knowstr中，属于notice情况
        if choice_description == "":
            self.log_manager.generate_error_log(time(), knowid, "cons_reload_parallelrelation", "notice", 8, "第一条并置关系不在knowstr中。")
            return generate_result

        # 为每一条并置关系生成一个随机浮点数->排序->返回随机前K个并置关系
        choice_topK=self.generate_random_topK(parallelrelation)

        # 选项的真值为True
        value=True

        # 拼接选型
        choice_text=choice_description
        for item in choice_topK:
            # 描述拼接
            choice_text+=","
            # item[0]表示的筛选后的并置关系
            choice_text+=item[0]

        # 收集结果
        generate_result.append(make_JSON(knowid+"1200",choice_text,value,3,knowcata))

        # 成功生成选项时，将生成选项信息写入运行日志。
        self.log_manager.generate_run_log(time(), knowid, "cons_reload_parallelrelation", len(generate_result))
        return generate_result

    def generate_random_topK(self,parallel_data):
        """
        返回随机前K个并置关系

        参数：
            parallel_data：并置关系内容

        返回值：
            sorted_list：一个列表，存放按降序排列取得的前K条并置规则
        """

        # 返回的topK并置关系
        parallel_topK=[]
        for item in parallel_data:
            # 使用元组存储浮点数和相应的并置关系，方便后续排序
            parallel_topK.append((item['Parallel'], random.random()))

        # 随机生成一个随机数K
        k=random.randint(1,len(parallel_topK))

        # lambda表达式排序，reverse=True为降序
        sorted_list = sorted(parallel_topK, key=lambda x: x[1],reverse=True)

        # 返回前k个
        return sorted_list[:k]

    def _get_base_desciption(self,knowstr,first_parallel_str):
        """
        获取开头部分内容，
        根据knowstr和第一条并置关系，使用find函数获取index

        参数：
            knowstr：知识内容

        返回值：
            一个分割后的字符串，如果发生错误返回空串
        """

        index = knowstr.find(first_parallel_str)
        if index == -1:
            return ""

        # 字符串分割
        return knowstr[:index]


