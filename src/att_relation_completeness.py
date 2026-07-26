"""
3.26 并置关系的全面验证——覆盖意图并列全面性

版本迭代情况：
[脱敏] 版本迭代记录

库依赖情况：
jsonschema==4.24.0

本组件存在内部依赖:
内部依赖：调用3.24、3.21、3.22接口、日志管理组件
大模型依赖：选项润色（3.22）

配置变量使用情况：
Parallel_SCHEMA：并置关系的schema
"""
import os
import sys
base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(base_dir)

import json
import time
import itertools # 生成组合用
import random
import jsonschema
from jsonschema import validate

from config import config_choice
from src.make_json import make_JSON

# 桩程序；在测试时使用stack，在正式运行时使用get_parallel_head
from src.stack import get_parallel_head
#from src.get_parallel_head import get_parallel_head

class AttRelationCompleteness: 
    """
    并置关系的全面验证——覆盖意图并列全面性
    
    属性：
        cond_validation_string：并置关系Schema字符串
        cond_validation_schema：解析后的并置关系Schema
        log_manager：用于管理日志
    """
    def __init__(self, log_manager):
        """
        初始化函数。

        参数：
            log_manager:日志管理类
        """
        self.cond_validation_string = config_choice.Parallel_SCHEMA
        self.cond_validation_schema = json.loads(self.cond_validation_string)
        self.log_manager = log_manager

    def generate_choice(self, knowid, knowstr, knowcata, parallelrelation):
        """
        根据并置关系生成选项。

        四种格式的选项：
        1.“<备选关系1>”，...，“<备选关系n>”是“<并置关系头>”的全部内容。
        2.“<并置关系头>”的内容只包括“<备选关系1>”，...，“<备选关系n>”。
        3.除了“<备选关系1>”，...，“<备选关系n>”外，“<并置关系头>”不包含其它内容。
        4.除了“<备选关系1>”，...，“<备选关系n>”外，“<并置关系头>”还包含其它内容。

        参数：
            knowid: 知识id
            knowstr: 知识字符串
            knowcata: 知识分类
            parallelrelation: 并置关系列表

        返回值：
            generate_result: 生成的选项列表

        异常处理：
            提示(notice)情况：
                1.并置规则列表为空
            错误(error)情况：
                1.并置关系头获取失败
            崩溃(corrupt)情况：
                1.并置关系不符合schema

        运行日志记录：
            成功生成选项时，将生成选项信息写入运行日志
        """
        # 存储最后输出的结果
        generate_result = []

        # 验证输入的并置关系是否符合schema
        validate_failed = False # 验证失败标记
        try:
            validate(schema=self.cond_validation_schema, instance=parallelrelation)
        except jsonschema.exceptions.SchemaError as e:
            # SchemaError异常，属于corrupt情况
            self.log_manager.generate_error_log(time.time(), knowid, "att_relation_completeness", "corrupt", 1, str(e))
            validate_failed = True
        except jsonschema.exceptions.ValidationError as e:
            # ValidationError异常，属于notice情况
            self.log_manager.generate_error_log(time.time(), knowid, "att_relation_completeness", "notice", 8, str(e))
            validate_failed = True

        if validate_failed:
            return generate_result
        
        # 知识没有并置关系，属于notice情况
        if len(parallelrelation) == 0:
            self.log_manager.generate_error_log(time.time(), knowid, "att_relation_completeness", "notice", 8, "并置规则列表为空")
            return generate_result

        # 根据并置关系头生成选项
        # 获取并置关系头
        try:
            parallel_head = get_parallel_head(knowstr, parallelrelation)
        except Exception as e:
            self.log_manager.generate_error_log(time.time(), knowid, "att_relation_completeness", "error", 3, str(e))
            return generate_result
        
        i = 0  # 选项计数
        parallel_head = "“"+parallel_head+"”"  # 给并置关系头加引号

        # 生成三条关于全部规则的选项
        parallel_item = [] # 存备选关系
        for p in parallelrelation:
            parallel_item.append("“"+p["Parallel"]+"”") # 给备选关系加引号

        all_parallel = "、".join(parallel_item) # 备选关系用顿号连接

        # 三个选项
        # “<备选关系1>”，...，“<备选关系n>”是“<并置关系头>”的全部内容。
        choice_1 = all_parallel+"是"+parallel_head+"的全部内容。"
        generate_result.append(make_JSON(knowid + "26" + str(i).zfill(2), choice_1, True, 11, knowcata))
        i += 1

        # 除了“<备选关系1>”，...，“<备选关系n>”外，“<并置关系头>”不包含其它内容。
        choice_3 = "除了"+all_parallel+"外，"+parallel_head+"不包含其它内容。"
        generate_result.append(make_JSON(knowid + "26" + str(i).zfill(2), choice_3, True, 11, knowcata))
        i += 1

        # 除了“<备选关系1>”，...，“<备选关系n>”外，“<并置关系头>”还包含其它内容。
        choice_4 = "除了"+all_parallel+"外，"+parallel_head+"还包含其它内容。"
        generate_result.append(make_JSON(knowid + "26" + str(i).zfill(2), choice_4, False, 11, knowcata))
        i += 1

        # 生成不完整规则的选项
        combination = self.generate_combination(parallelrelation)  # 不完整规则组合
        for comb in combination:
            curr_combination = [] # 当前遍历到的组合
            for c in comb:
                curr_combination.append("“"+c["Parallel"]+"”")

            all_combination = "、".join(curr_combination)

            # 四个选项
            # “<备选关系1>”，...，“<备选关系n>”是“<并置关系头>”的全部内容。
            choice_1 = all_combination+"是"+parallel_head+"的全部内容。"
            generate_result.append(make_JSON(knowid + "26" + str(i).zfill(2), choice_1, False, 11, knowcata))
            i += 1

            # “<并置关系头>”的内容只包括“<备选关系1>”，...，“<备选关系n>”。
            choice_2 = parallel_head+"的内容只包括"+all_combination+"。"
            generate_result.append(make_JSON(knowid + "26" + str(i).zfill(2), choice_2, False, 11, knowcata))
            i += 1

            # 除了“<备选关系1>”，...，“<备选关系n>”外，“<并置关系头>”不包含其它内容。
            choice_3 = "除了"+all_combination+"外，"+parallel_head+"不包含其它内容。"
            generate_result.append(make_JSON(knowid + "26" + str(i).zfill(2), choice_3, False, 11, knowcata))
            i += 1

            # 除了“<备选关系1>”，...，“<备选关系n>”外，“<并置关系头>”还包含其它内容。
            choice_4 = "除了"+all_combination+"外，"+parallel_head+"还包含其它内容。"
            generate_result.append(make_JSON(knowid + "26" + str(i).zfill(2), choice_4, True, 11, knowcata))
            i += 1
        
        # 如果运行到最后没有问题，就写入运行日志
        self.log_manager.generate_run_log(time.time(), knowid, "att_relation_completeness", len(generate_result))

        return generate_result

    def generate_combination(self, parallelrelation):
        """
        先枚举所有非空真子集，然后从中随机挑n个组合返回。

        参数：
            parallelrelation: 并置关系列表

        返回值：
            combinations: 生成的组合
        """

        # 枚举parallelrelation所有非空真子集
        all_combination = [] 
        for r in range(1, len(parallelrelation)):
            for index in itertools.combinations(range(len(parallelrelation)), r): 
                combination = []
                for i in index:
                    combination.append(parallelrelation[i])
                all_combination.append(combination)

        # 随机选并置关系数量个不重复组合
        rand_combination = random.sample(all_combination, len(parallelrelation))
        return rand_combination
