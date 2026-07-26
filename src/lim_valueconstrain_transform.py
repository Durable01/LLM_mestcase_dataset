"""
3.14 数值约束的条件更改-覆盖条件敏感性

版本迭代情况:
[脱敏] 版本迭代记录
[脱敏] 版本迭代记录
[脱敏] 版本迭代记录

本组件存在库依赖和文档依赖
库依赖:
numpy==1.26.4
pandas==2.3.0
schema==0.7.7
文档依赖:
使用pandas读取 document下的transform_unit 单位表

配置变量使用情况:
TRANSFORM_UNIT_DIR:单位表路径
"""

import json
import copy
import random
from time import time
from config.config_choice import TRANSFORM_UNIT_DIR
import jsonschema
import jsonschema.exceptions
import numpy as np
import pandas as pd
from jsonschema import validate
from config import config_choice
from src.make_json import make_JSON

class LimValueConstraintTransform:
    """
    数值约束转换类-组件3.14
    类变量：
    cond_validation_string:推理前后件schema字符串
    cond_validation_schema:判断是否符合推理后件/前件的schema
    log_manager:日志管理类
    path:单位转换表的路径
    knowid:知识id
    unit_table:从csv文件中读取的单位表
    np_data:单位表生成的numpy数组
    compare:数值约束条件列表
    """
    def __init__(self,log_manager):
        """
        类初始化函数

        参数：log_manager:日志管理类
        """
        cond_validation_string = config_choice.CONSTRAINT_SCHEMA
        self.cond_validation_schema = json.loads(cond_validation_string)
        self.log_manager = log_manager
        self.path = TRANSFORM_UNIT_DIR
        self.knowid = ""
        try:
            self.unit_table = pd.read_csv(self.path)
        except Exception as e:
            self.log_manager.generate_error_log(time(), self.knowid, "lim_valueconstrain_transform", "corrupt", 2,
                                                str(e))
        self.np_data = np.array(self.unit_table)
        #随机生成一个0-5的随机数，从list中获取
        self.compare=["large","equal","below","largeequal","notequal","belowequal"]


    def generate_choice(self, knowid, knowstr, knowcata, inference):
        """ 算法的核心部分，通过这里完成选项的生成任务。

            函数参数：
                knowid：知识唯一标识，一个字符串。
                knowstr：知识内容，一个字符串。
                knowcata：知识目录标识，一个字符串。
                inference：推理规则，它是符合inference schema的JSON格式。

            返回值：
                generate_result，一个列表，列表中的每个元素为一个满足选项schema的JSON。

            异常处理：notice和corrupt
                notice:
                     1.知识推理列表为空
                     2.知识列表没有数值约束
                     3.数值约束中的单位在常用单位表中无法查到。
                 corrupt:
                     1.jsonschema验证抛出jsonschema.exceptions.SchemaError异常。
                     2.类构造函数读取文档抛出异常。

            运行日志记录：
                成功生成选项时，将生成选项信息写入运行日志

        """
        # 存储生成选项结果，初始列表为空。
        self.knowid=knowid
        generate_result = []

        # 如果inference为空，长度为0，直接返回结果。
        if len(inference) == 0:
            self.log_manager.generate_error_log(time(), knowid, "lim_valueconstrain_transform", "notice", 9, "推理列表为空")
            return generate_result
        #保证推理前件和后件都有cond 否则直接返回
        try:
            #推理前件
            antecedent_constraint = inference['antecedent']['cond']
            #推理后件
            consequence_constraint = inference['consequence']['cond']
        except jsonschema.exceptions.SchemaError as e:
            self.log_manager.generate_error_log(time(),knowid,"lim_valueconstrain_transform","corrupt",1,str(e))
            return generate_result

        whether_validate = 0
        try:  # 验证推理前件
            validate(schema=self.cond_validation_schema, instance=antecedent_constraint)
        except jsonschema.exceptions.SchemaError as e:
            #不符合约束schema是触发corrupt，输出到日志中
            self.log_manager.generate_error_log(time(),knowid,"lim_valueconstrain_transform","corrupt",1,str(e))
            whether_validate = 1
        except jsonschema.exceptions.ValidationError as e:
            # jsonschema.exceptions.ValidationError异常，属于notice情况
            self.log_manager.generate_error_log(time(),knowid,"lim_valueconstrain_transform","notice",9,str(e))
            whether_validate = 1

        try:  # 验证推理后件
            validate(schema=self.cond_validation_schema, instance=consequence_constraint)
        except jsonschema.exceptions.SchemaError as e:
            # 不符合约束schema是触发corrupt，输出到日志中
            self.log_manager.generate_error_log(time(),knowid,"lim_valueconstrain_transform","corrupt",1,str(e))
            whether_validate = 1
        except jsonschema.exceptions.ValidationError as e:
            #推理列表为空的情况走的jsonschema.exceptions.ValidationError异常，属于notice情况
            self.log_manager.generate_error_log(time(),knowid,"lim_valueconstrain_transform","notice",9,str(e))
            whether_validate = 1
        if whether_validate != 0:  # 此时约束不满足条件，返回空列表。
            return generate_result
 
        '''
        如果推理前件和推理后件均不含数值约束，直接返回空集合
        '''
        if ("verb" in antecedent_constraint["constraint"] or "entity" in antecedent_constraint["constraint"]) and ("verb" in consequence_constraint["constraint"] or "entity" in consequence_constraint["constraint"]):
            self.log_manager.generate_error_log(time(),knowid,"lim_valueconstrain_transform","notice",11,"推理列表中不含数值约束")
            return generate_result


        '''
        用list存储前件，后件处理后的推理关系
        '''
        antecedent_constraint_list=[]
        consequence_constraint_list=[]

        if ("compare" in antecedent_constraint["constraint"]):
            #如果前件有数值约束，对推理前件进行处理
            antecedent_constraint_list=self._transform_constraint(antecedent_constraint)
        if ("compare" in consequence_constraint["constraint"]):
            # 如果后件有数值约束，对推理后件进行处理
            consequence_constraint_list = self._transform_constraint(consequence_constraint)
        '''
        如果集合为空，说明推理前/后件不是数值约束，不能处理。
        '''

        #前件是数值约束，后件不是，组合有三种
        cnt = 0
        if(len(antecedent_constraint_list)!=0 and len(consequence_constraint_list)==0):
            '''
            tran表示修改
            value/compare/unit表示改动的具体约束元素
            ante/cons表示推理前件和推理后件
            str为字符串 
            '''

            #将改动后的约束变成字符串
            tran_value_ante_str=self._make_string(antecedent_constraint_list[0],consequence_constraint)
            tran_compare_ante_str=self._make_string(antecedent_constraint_list[1],consequence_constraint)

            #收集结果
            generate_result.append(make_JSON(knowid + "14" + str(cnt).zfill(2),tran_value_ante_str,False,6,knowcata))
            cnt += 1
            generate_result.append(make_JSON(knowid + "14" + str(cnt).zfill(2), tran_compare_ante_str, False, 6, knowcata))
            cnt += 1
            #单位替换需要有判空操作，
            if(len(antecedent_constraint_list)==3):
                tran_unit_ante_str = self._make_string(antecedent_constraint_list[2], consequence_constraint)
                generate_result.append(make_JSON(knowid + "14" + str(cnt).zfill(2), tran_unit_ante_str, False, 6, knowcata))
                cnt += 1

        #后件是数值约束，前件不是，组合三种
        elif(len(antecedent_constraint_list)==0 and len(consequence_constraint_list)!=0):
            #将改动后的推理后件转变成字符串
            tran_value_cons_str=self._make_string( antecedent_constraint,consequence_constraint_list[0])
            tran_compare_cons_str=self._make_string(antecedent_constraint,consequence_constraint_list[1])

            #收集结果
            generate_result.append(make_JSON(knowid + "14" + str(cnt).zfill(2),tran_value_cons_str,False,6,knowcata))
            cnt += 1
            generate_result.append(make_JSON(knowid + "14" + str(cnt).zfill(2), tran_compare_cons_str, False, 6, knowcata))
            cnt += 1

            if (len(consequence_constraint_list) == 3):
                tran_unit_cons_str = self._make_string(antecedent_constraint, consequence_constraint_list[2])
                generate_result.append(make_JSON(knowid + "14" + str(cnt).zfill(2), tran_unit_cons_str, False, 6, knowcata))
                cnt += 1
        else:
            '''
            前件和后件都是数值约束，组合一共六种,
            如果单位替换在表中找不到，那么就不替换，有可能少于六种但是不低于四种
            '''

            tran_value_ante_str = self._make_string( antecedent_constraint_list[0], consequence_constraint)
            tran_compare_ante_str = self._make_string( antecedent_constraint_list[1], consequence_constraint)

            # 收集结果
            generate_result.append(make_JSON(knowid + "14" + str(cnt).zfill(2), tran_value_ante_str, False, 6, knowcata))
            cnt += 1
            generate_result.append(make_JSON(knowid + "14" + str(cnt).zfill(2), tran_compare_ante_str, False, 6, knowcata))
            cnt += 1

            if (len(antecedent_constraint_list) == 3):
                tran_unit_ante_str = self._make_string(antecedent_constraint_list[2], consequence_constraint)
                generate_result.append(make_JSON(knowid + "14" + str(cnt).zfill(2), tran_unit_ante_str, False, 6, knowcata))
                cnt += 1
            tran_value_cons_str = self._make_string(antecedent_constraint, consequence_constraint_list[0])
            tran_compare_cons_str = self._make_string( antecedent_constraint, consequence_constraint_list[1])

            # 收集结果
            generate_result.append(make_JSON(knowid + "14" + str(cnt).zfill(2), tran_value_cons_str, False, 6, knowcata))
            cnt += 1
            generate_result.append(make_JSON(knowid + "14" + str(cnt).zfill(2), tran_compare_cons_str, False, 6, knowcata))
            cnt += 1

            if (len(consequence_constraint_list) == 3):
                tran_unit_cons_str = self._make_string(antecedent_constraint, consequence_constraint_list[2])
                generate_result.append(make_JSON(knowid + "14" + str(cnt).zfill(2), tran_unit_cons_str, False, 6, knowcata))

        #运行到最后没有问题，输出到运行日志
        self.log_manager.generate_run_log(time(), knowid, "lim_valueconstrain_transform", len(generate_result))
        return generate_result

    def _number_to_string(self, cond):
        ''' 将数值约束转换为字符串。
        函数参数：
            cond：约束，一个JSON。
        返回值：
            merge_string，一个组合后的字符串。

        '''
        merge_string = ""
        merge_string = merge_string + cond["entity"]
        if cond["bool"] == False:
            merge_string = merge_string + "没有"
        # 为了便于表示，条件约束单独提出来。
        cond_constraint = cond["constraint"]
        # 枚举六种比较符，依次插入对应的表示词。
        if cond_constraint["compare"] == "large":
            merge_string = merge_string + "大于"
        elif cond_constraint["compare"] == "equal":
            merge_string = merge_string + "等于"
        elif cond_constraint["compare"] == "below":
            merge_string = merge_string + "小于"
        elif cond_constraint["compare"] == "largeequal":
            merge_string = merge_string + "大于等于"
        elif cond_constraint["compare"] == "notequal":
            merge_string = merge_string + "不等于"
        elif cond_constraint["compare"] == "belowequal":
            merge_string = merge_string + "小于等于"
        # 为数值和单位插入比较符，并返回。
        merge_string = merge_string + str(cond_constraint["index"]) + cond_constraint["unit"]
        return merge_string

    def _existence_to_string(self, cond):
        ''' 将存在约束转换为字符串。

        函数参数：
            cond：约束，一个JSON。

        返回值：
            merge_string，一个组合后的字符串。

        '''

        merge_string = ""
        merge_string = merge_string + cond["entity"]
        if cond["bool"] == False:
            merge_string = merge_string + "没有"
        cond_constraint = cond["constraint"]
        if "verb" in cond_constraint:
            merge_string = merge_string + cond_constraint["verb"]
        if len(cond_constraint["entity"]) == 1:
            merge_string = merge_string + cond_constraint["entity"][0]
        elif len(cond_constraint["entity"]) > 1:
            for i in range(len(cond_constraint["entity"])):
                if i != 0:
                    merge_string = merge_string + "、"
                merge_string = merge_string + cond_constraint["entity"][i]
        return merge_string

    def _make_string(self, front, back):
        ''' 字符串构造函数，采用“<front部分>时，<back>”的格式。
            对推理前件取反
        函数参数：
            front：推理前件，一个JSON，符合cond schema。
            back：推理后件，一个JSON，符合cond schema。

        返回值：
            merge_string，一个组合后的字符串。

        '''
        # 存储返回结果，初始为初始衔接词
        merge_string = "如果"
        # 对推理前件分情况讨论
        if "verb" in front["constraint"] or "entity" in front["constraint"]:  # verb字段只出现在存在约束中，此时调用存在约束转换函数
            merge_string = merge_string + self._existence_to_string(front)
        elif "compare" in front["constraint"]:  # compare字段只出现在数值约束中，此时调用数值约束转换函数
            merge_string = merge_string + self._number_to_string(front)
        # 添加描述衔接词
        merge_string = merge_string + "，那么"  # 添加分隔符
        # 对推理后件分情况讨论
        if "verb" in back["constraint"] or "entity" in back["constraint"]:
            merge_string = merge_string + self._existence_to_string(back)
        elif "compare" in back["constraint"]:
            merge_string = merge_string + self._number_to_string(back)
        # 添加描述结尾词，返回结果
        return merge_string


    def _transform_compare(self):
        #生成一个0-5的随机数作为索引，从compare表中获取
        return self.compare[random.randint(0,5)]

    def _transform_value(self,value):
        '''
        为了让随机的数值改动不要太离谱，限定是原数值的2倍-3倍的随机数,如果数值约束出现0则限定为1~3的随机数

        参数：value：从推理列表中获取的数值
        '''
        if (value == 0) :
            return random.randint(1, 3)
        else :
            return random.randint(value*2,value*3)
    def _transform_unit(self,origin_unit,table):
        """
        使用numpy从单位表读取一个单位

        参数：
        origin_unit:原单位
        table:单位表

        返回值：一个新单位
        """
        while(True):
            '''
            表的定义是直接写死的，第一列为单位名，第三列为表示方法，
            思路是：匹配原单位名称->原单位表示方法->随机匹配同样表示方法的行->返回该行的单位名称
            即只有同样表示方法的单位才能够返回，这样保证了真值为False
            '''
            unit_representation = table[table[:, 0] == origin_unit, 2]

            # 如果该单位在表中不存在，直接返回一个空串
            if len(unit_representation) == 0:
                self.log_manager.generate_error_log(time(), self.knowid, "lim_valueconstrain_transform", "notice", 12,
                                                    "原单位" + origin_unit + "在单位表找不到")
                return ""
            # 找到所有具有相同表示方法的单位
            same_notation_indices = table[(table[:, 2] == unit_representation) & (table[:, 0] != origin_unit), 0]

            # 随机选择一个不同的单位
            valid_indices = np.random.choice(same_notation_indices)

            return valid_indices

    def _transform_constraint(self,constraint):
        """
        对约束条件进行改动

        参数：推理前件

        返回值是一个约束列表 包含了所有改动后的约束，包括 单位，比较，数值
        """

        constraint_value=copy.deepcopy(constraint)

        # 对compare进行改动，包括 单位，比较，数值
        constraint_compare = copy.deepcopy(constraint)

        #对unit进行改动
        constraint_unit = copy.deepcopy(constraint)
        while(True):#循环保证获取的value和compare和原先不一致
             original_value=constraint_value["constraint"]["index"]
             constraint_value["constraint"]["index"]=self._transform_value(original_value)
             #保证生成的value和原来不一样
             if constraint_value["constraint"]["index"] != original_value:
                break
        while(True):
            original_compare=constraint_compare["constraint"]["compare"]
            constraint_compare["constraint"]["compare"]=self._transform_compare()
            #保证和原来生成的compare不一致
            if constraint_compare["constraint"]["compare"] != original_compare:
                break
                #返回list
        transform_unit=self._transform_unit(constraint_unit["constraint"]["unit"], self.np_data)

        #判断返回的单位是否为空串
        if(transform_unit==""):
            return  constraint_value, constraint_compare

        constraint_unit["constraint"]["unit"]=transform_unit
        return constraint_value, constraint_compare, constraint_unit
