"""
3.25 并置关系的规则从属——覆盖意图并列一致性

版本迭代情况：
[脱敏] 版本迭代记录

库依赖情况：
jsonschema==4.24.0
numpy==1.26.4

本组件存在内部依赖。
内部依赖：调用3.22、3.23、3.24接口

配置变量使用情况：
Parallel_SCHEMA：并置关系schema
REFINE_PROMPT_25：润色用prompt
"""

import json
import random
import jsonschema
import numpy as np
from time import time
from jsonschema import validate
from config import config_choice
from src.make_json import make_JSON
from src.call_LLM import call_LLM
from src.stack import get_parallel_head

class AttRelationDomain(object):
    '''
    并置关系的规则从属类

    属性：
        cond_validation_string：并置关系Schema 字符串
        cond_validation_schema：解析后的并置关系Schema
        refine_prompt：精炼用提示词
        log_manager：日志管理类
    '''

    def __init__(self, log_manager):
        '''
        类初始化函数

        参数：
            log_manager: 日志管理类

        返回值：
            无
        '''
        self.cond_validation_string = config_choice.Parallel_SCHEMA
        self.cond_validation_schema = json.loads(self.cond_validation_string)
        self.refine_prompt = config_choice.REFINE_PROMPT_25
        self.log_manager = log_manager
    
    def _get_selected_index(self, random_upper, random_time):
        '''
        在给定范围内不重复地选择序列。

        参数：
            random_upper：选择序列的上限，这使得选择的范围为[0, random_upper)。
            random_time：选择的次数

        返回值：
            selected_index：被选择的数字列表
        '''

        ''' 
        整体的实现思路是类似于统计计算的思想：选择一个数，然后把这个数和队尾对调。
        这里要从0到random_upper - 1的闭区间上选择不相同的整数，所以第n次随机选择0到random_upper - n的随机数。
        这里，randint是左闭右开区间，所以第n次是random_upper - (n-1), 而循环变量i等于n-1。
        这里需要注意“和队尾对调”的实现方式。我们不采用大数组真的对调，但是对调满足一定的数学性质。
        第n次选择了数字m，那么m是和random_upper-n对调的，这也就意味着，如果后续有数字和m相等，相当于这次选择了random_upper-n。
        但是，这里j是数组下标，n等于j+1，因此如果相等，相当于这次选择了random_upper - j - 1.
        '''
        selected_index = []
        for i in range(0, random_time):
            random_index = np.random.randint(0, random_upper - i)
            whether_same = 0
            for j in range(len(selected_index)):
                if selected_index[j] == random_index:
                    # 下面这一行之前出过bug，没有注意到数组下标和次数的关系，错误写了random_upper - j。
                    selected_index.append(random_upper - j - 1)
                    whether_same = 1
            if whether_same == 0:
                selected_index.append(random_index)
        return selected_index
    
    def _get_2_parallel(self, parallelrelation):
        '''
        从并置关系中随机选择两个规则的函数。
        选择的数量 = 并置关系数 - 2。

        参数：
            parallelrelation：本条知识包含的全部并置关系，parallelrelation[i]["Parallel"]即可得到并置关系的字符串。
        
        返回值：
            selected_results：一个字符串列表组成的列表。
                selected_results中的每个元素selected_result表示一次选择的两个并置关系。
        '''

        # 返回的列表。
        selected_results = []
        length = len(parallelrelation)
        # 计算随机的次数，每次随机获得一个列表。
        random_time = length - 2
        # 计算随机数的范围。
        random_upper = length * (length - 1)
        # 被选择的数字的列表。
        selected_index = self._get_selected_index(random_upper, random_time)
        # 对于得到的数字index, index / (length - 1)为第一个元素的下标，index % (length - 1)为第二个元素的下标。
        for index in selected_index:
            selected_result = []
            index_first = int(index / (length - 1))
            selected_result.append(parallelrelation[index_first]["Parallel"])
            index_second = index % (length - 1)
            if index_second >= index_first:
                index_second = index_second + 1
            selected_result.append(parallelrelation[int(index_second)]["Parallel"])
            selected_results.append(selected_result)
        return selected_results
    
    def _get_3_parallel(self, parallelrelation):
        '''
        从并置关系中随机选择三个规则的函数。
        选择的数量 = 并置关系数 - 2。

        参数：
            parallelrelation：本条知识包含的全部并置关系，parallelrelation[i]["Parallel"]即可得到并置关系的字符串。
        
        返回值：
            selected_results：一个字符串列表组成的列表。
                selected_results中的每个元素selected_result表示一次选择的三个并置关系。
        '''

        # 返回的列表。
        selected_results = []
        length = len(parallelrelation)
        # 计算随机的次数，每次随机获得一个列表。
        random_time = length - 2
        # 计算随机数的范围。
        random_upper = length * (length - 1) * (length - 2)
        # 被选择的数字的列表。
        selected_index = self._get_selected_index(random_upper, random_time)
        # 对于得到的数字index, 计算三个元素的下标。
        for index in selected_index:
            selected_result = []
            index_first = int(index / (length - 1) / (length - 2))
            index_middle = index - index_first * (length - 1) * (length - 2)
            index_second = int(index_middle / (length - 2))
            if index_second >= index_first:
                index_second = index_second + 1
            index_third = index_middle % (length - 2)
            cmp_min = index_first
            cmp_max = index_second
            if cmp_min > cmp_max:
                cmp_min = index_second
                cmp_max = index_first
            if index_third >= cmp_min:
                index_third = index_third + 1
            if index_third >= cmp_max:
                index_third = index_third + 1
            selected_result.append(parallelrelation[int(index_first)]["Parallel"])
            selected_result.append(parallelrelation[int(index_second)]["Parallel"])
            selected_result.append(parallelrelation[int(index_third)]["Parallel"])
            selected_results.append(selected_result)
        return selected_results


    def generate_choice(self,knowid,knowstr,knowcata,parallelrelation):
        '''
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
                1. 知识没有并置关系或schema验证抛出ValidationError，错误码8
                2. 知识并置关系数少于3，错误码16
            警告(warning)情况：
                1. 大模型调用失败，错误码1
            错误(error)情况：
                1. 调用3.24组件出现异常，错误码3
            崩溃(corrupt)情况：
                1. schema验证抛出SchemaError，错误码1

        运行日志记录：
            成功生成选项时，将生成选项信息写入运行日志，evaluation为10
        '''

        # 存储返回值
        generate_result = []
        validate_failed = False

        ''' 判断并置关系是否为空，或者不能通过schema验证。
        '''
        if len(parallelrelation) == 0:
            self.log_manager.generate_error_log(time(), knowid, "att_relation_domain", "notice", 8, "知识没有并置关系")
            validate_failed = True
        try:
            validate(schema=self.cond_validation_schema, instance=parallelrelation)
        except jsonschema.exceptions.SchemaError as e:
            # jsonschema.exceptions.SchemaError异常，属于corrupt情况
            self.log_manager.generate_error_log(time(), knowid, "att_relation_domain", "corrupt", 1, str(e))
            validate_failed = True
        except jsonschema.exceptions.ValidationError as e:
            # jsonschema.exceptions.ValidationError异常，属于notice情况
            self.log_manager.generate_error_log(time(), knowid, "att_relation_domain", "notice", 8, str(e))
            validate_failed = True

        if validate_failed == True: 
            # 该变量值为True说明前面抛出过异常，直接返回
            return generate_result
        
        ''' 判断并置关系数是否小于3。
        '''
        if len(parallelrelation) < 3:
            self.log_manager.generate_error_log(time(), knowid, "att_relation_domain", "notice", 16, "知识并置关系数小于3")
            return generate_result

        ''' 调用3.24组件，获取并置规则头。
        '''
        # 并置规则头（parallel relation head)，简写为para_head.
        para_head = ""
        try:
            para_head = get_parallel_head(knowstr, parallelrelation)
        except Exception as e:
            # 出现异常直接结束当前算法运行。
            self.log_manager.generate_error_log(time(), knowid, "att_relation_domain", "error", 3, str(e))
            return generate_result
        
        ''' 
        随机选择若干对、包含2-3个并置关系的组合，每种组合的对数为并置关系数-2。
        这一部分用函数包装实现。
        '''
        selected_2_groups = self._get_2_parallel(parallelrelation)
        selected_3_groups = self._get_3_parallel(parallelrelation)
        
        ''' 按照模板完成选项的构建。
        '''

        generate_middle = []
        for selected in selected_2_groups:
            generated_string = "“" + selected[0] + "”，"
            generated_string = generated_string + "“" + selected[1] + "”，都是“" + para_head + "”包含的内容"
            generate_middle.append(generated_string)
        
        for selected in selected_3_groups:
            generated_string = "“" + selected[0] + "”，“" + selected[1]
            generated_string = generated_string + "”，“" + selected[2] + "”，都是“" + para_head + "”包含的内容"
            generate_middle.append(generated_string)
        
        ''' 原有用大模型润色的步骤取消，这一步直接按照原字符串处理。
        '''
        generate_string = []
        for generate in generate_middle:
            '''
            LLM_input = generate + "\n" + self.refine_prompt
            LLM_output = ""
            try:
                LLM_output = call_LLM(LLM_input)
            except Exception as e:
                self.log_manager.generate_error_log(time(), knowid, "att_relation_domain", "warining", 1, str(e))
                # 此时可以正常生成选项。
                generate_string.append(generate)
                continue
            # 如果正常生成了，以换行符分割，每一段进行匹配。
            output_list = LLM_output.split("\n")
            for output in output_list:
                if len(output) < 4:
                    continue
                match_pos = output.find("陈述：")
                if match_pos != -1:
                    generate_string.append(output[match_pos + 3:])
            '''
            generate_string.append(generate)
        
        ''' 构建JSON，其中value为True，evaluation为10.
        '''
        for i in range(0, len(generate_string)):
            generate_result.append(make_JSON(knowid + "25" + str(i).zfill(2), generate_string[i], True, 10, knowcata))

        # 成功生成选项时，将生成选项信息写入运行日志。
        self.log_manager.generate_run_log(time(), knowid, "att_relation_domain", len(generate_result))
        return generate_result
        
