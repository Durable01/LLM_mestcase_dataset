"""
3.5 知识图谱相近概念混淆-覆盖知识准确性

版本迭代情况:
[脱敏] 版本迭代记录
[脱敏] 版本迭代记录
[脱敏] 版本迭代记录
[脱敏] 版本迭代记录

库依赖情况:
无

本组件存在内部依赖和外部依赖
内部依赖:调用3.21,3.23接口
外部依赖:知识图谱-给定语义相似度范围的实体获取

配置变量使用情况:
无
"""
import random
import json
from time import time

from src.make_json import make_JSON
# 桩程序
from src.stack import get_similar_entity

class AccKGConfuse:
    """
    知识图谱相近概念混淆-覆盖知识准确性

    类变量：
    log_manager:日志管理类
    """
    def __init__(self,log_manager):
        """
        初始化函数

        参数：
            log_manager:日志管理类
        """
        self.log_manager = log_manager


    def generate_choice(self, knowid, knowstr, knowcata, entityrelation):
        """
        生成选项的函数

        参数：
            knowid：知识唯一标识，一个字符串
            knowstr：知识描述内容，一个字符串
            knowcata：知识所在目录唯一标识，一个字符串
            entityrelation：知识的三元组列表，每个元素包含"frontentity","relation","endentity"

        返回值：
            生成的选项 JSON 列表。

        异常处理：
            提示(notice)情况:
                1.知识中没有三元组实体关系
            警告(warning)情况:
                1.使用外部依赖时出现异常

        运行日志记录：
            成功生成选项时，将生成选项信息写入运行日志
        """
        # 选项列表
        generate_result = []
        # 没有三元组关系不能执行，写入error_log中，异常类型为notice
        if not entityrelation:
            self.log_manager.generate_error_log(time(), knowid, "acc_KG_confuse", "notice", 2, "知识不存在三元组实体关系")
            return generate_result

        # 随机选一个三元组
        rand_triple = random.choice(entityrelation)
        frontentity = rand_triple["frontentity"]
        endentity = rand_triple["endentity"]
        # 随机替换frontentity/endentity
        target_entity = random.choice([frontentity, endentity])
        similar_entity_list=[]
        try:
            # 调用桩程序，获取相似实体列表
            similar_entity_list = get_similar_entity(target_entity, 0.5, 0.8)
        except Exception as e:
            # 调用外部依赖的时候出现错误
            self.log_manager.generate_error_log(time(), knowid, "acc_KG_confuse", "warning", 2, str(e))
            return generate_result

        # 为每个相近实体生成错误选项
        for i, similar_entity in enumerate(similar_entity_list):
            new_text = knowstr.replace(target_entity, similar_entity) # 替换
            option_id = knowid # 选项id

            json_choice = make_JSON(option_id + "05" + str(i).zfill(2), new_text, False, 1, knowcata)
            generate_result.append(json_choice)

        # 如果运行到最后没有出现错误，就写入run_log
        self.log_manager.generate_run_log(time(), knowid, "acc_KG_confuse", len(generate_result))

        # 返回结果
        return generate_result