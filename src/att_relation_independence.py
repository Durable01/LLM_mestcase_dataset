'''
3.27 并置关系的并列性检查——覆盖意图并列独立性

版本迭代情况:
[脱敏] 版本迭代记录

本组件存在库依赖,内部依赖
库依赖:
jsonschema==4.24.0
numpy==1.26.4

内部依赖:3.21，3.23，3.24
3.21:make_Json
3.23:日志管理组件
3.24:并置关系头提取
'''
import json
import random
from time import time

import jsonschema
import numpy as np
from jsonschema import validate

from config import config_choice
from src.make_json import make_JSON
# 桩程序；在测试时使用stack，在正式运行时使用get_parallel_head
from src.stack import get_parallel_head
#from src.get_parallel_head import get_parallel_head


class AttRelationIndependence(object):
    '''
    类变量：
    cond_validation_string:并置关系使用校验的Schema
    cond_validation_schema:判断是否符合并置关系schema
    log_manager:日志管理类
    '''

    def __init__(self,log_manager):
        self.log_manager = log_manager
        self.cond_validation_string = config_choice.Parallel_SCHEMA
        self.cond_validation_schema = json.loads(self.cond_validation_string)


    def generate_choice(self,knowid,knowstr,knowcata,parallelrelation):
        """ 算法的核心部分，通过这里完成选项的生成任务。
            函数参数：
                knowid：知识唯一标识，一个字符串。
                knowstr：知识内容，一个字符串。
                knowcata：知识目录标识，一个字符串。
                parallelrelation：并置关系

            返回值：
                generate_result，一个列表，列表中的每个元素为一个满足选项schema的JSON。

            异常处理：notice和error,corrupt
                notice:
                    1.如果并置关系规则列表为空，表明这条知识不能使用这样的算法进行生成。
                error:
                    1.判断并置关系头的结束位置；如果抛出异常，错误类型为error-3
                corrupt:
                    1.当抛出jsonschema.exceptions.SchemaError异常
            运行日志记录：
                成功生成选项时，将生成选项信息写入运行日志

        """

        # 存储最后输出的结果
        generate_result = []
        validate_failed = False
        # 验证输入的并置关系是否符合schema
        try:
            validate(schema=self.cond_validation_schema, instance=parallelrelation)
        except jsonschema.exceptions.SchemaError as e:
            # jsonschema.exceptions.SchemaError异常，属于corrupt情况
            self.log_manager.generate_error_log(time(), knowid, "att_relation_independence", "corrupt", 1, str(e))
            validate_failed = True
        except jsonschema.exceptions.ValidationError as e:
            # jsonschema.exceptions.ValidationError异常，属于notice情况
            self.log_manager.generate_error_log(time(), knowid, "att_relation_independence", "notice", 8, str(e))
            validate_failed = True
        if len(parallelrelation)==0:
            self.log_manager.generate_error_log(time(), knowid, "att_relation_independence", "notice", 8, "并置关系为空，不能执行此算法")
            validate_failed = True

        if validate_failed:
            return generate_result



        try:
            # 调用获取并置关系头
            parallelrelation_head=get_parallel_head(knowstr,parallelrelation)
        except Exception as e:
            #出现错误抛出异常
            self.log_manager.generate_error_log(time(), knowid, "att_relation_independence", "error", 3, str(e))
            return generate_result
        #调用随机数，获取不重复的排列
        combinations=self.get_random_parallelrelation(len(parallelrelation))
        list_two_parallelrelation=combinations[0]
        list_three_parallelrelation=combinations[1]

        #获取混淆后的并置关系
        #排列长度为二获取的字符串
        list_two_string=self.parallel_confuse_two(list_two_parallelrelation,parallelrelation,parallelrelation_head)
        # 排列长度为三获取的字符串
        list_three_string=self.parallel_confuse_three(list_three_parallelrelation,parallelrelation,parallelrelation_head)

        for temp_string in list_two_string:
            generate_result.append(make_JSON(knowid + "27" + str(len(generate_result) + 1).zfill(2), temp_string, False, 12,knowcata))

        for temp_string in list_three_string:
            generate_result.append(make_JSON(knowid + "27" + str(len(generate_result) + 1).zfill(2), temp_string, False, 12,knowcata))

        self.log_manager.generate_run_log(time(), knowid, "att_relation_independence", len(generate_result))
        return generate_result

    def get_random_parallelrelation(self,k):
            '''
            参数：K，表示当前并置关系长度
            返回值：
            两个列表：1.长度为k-1 不重复的长度为2排列
                    2.长度为k-2 不重复的长度为3排列
            '''
            list_two_parallelrelation=[]
            list_three_parallelrelation = []
            all_permutations = []
            #由于并置关系一般不会超过很大 时间复杂度虽然为O(n),资源消耗不大，采取遍历在取随机数的方式
            for a in range(k):
                for b in range(k):
                    if a != b:
                        all_permutations.append((a, b))
            list_two_parallelrelation = random.sample(all_permutations, k - 1)
            if(k==2):
                #如果并置关系长度为2，就不需要获取长度为3的排列
                return list_two_parallelrelation, list_three_parallelrelation

            #通过set进行去重
            permutations = set()
            while(len(list_three_parallelrelation) <k-2):
                a = np.random.randint(0, k)
                b = np.random.randint(0, k)
                c = np.random.randint(0, k)
                if a != b and a != c and b != c:
                    #获取随机数进行校验
                    perm_tuple = (a, b, c)
                    if perm_tuple not in permutations:
                        permutations.add(perm_tuple)
                        # 收集随机k-1
                        list_three_parallelrelation.append(list(perm_tuple))


            #返回结果
            return list_two_parallelrelation, list_three_parallelrelation


    def parallel_confuse_two(self,list_two_parallelrelation,parallelrelation,parallel_head):
            '''
                方法参数：
                list_two_parallelrelation:随机数列表
                parallelrelation:并置关系词典
                parallel_head:并置关系头

                返回值:
                confuse_string_list:拼接后的经过混淆的字符串列表
            '''

            confuse_string_list=[]
            #按照架构设计拼接字符串
            for two_index in list_two_parallelrelation:
                confuse_string1=parallel_head+"中，"+"“"+parallelrelation[two_index[0]]["Parallel"]+"”"+"比"+"“"+parallelrelation[two_index[1]]["Parallel"]+"”"+"重要。"
                confuse_string2=parallel_head+"中，"+"“"+parallelrelation[two_index[0]]["Parallel"]+"”"+"可以代替"+"“"+parallelrelation[two_index[1]]["Parallel"]+"”"+"。"
                confuse_string3=parallel_head+"中，"+"“"+parallelrelation[two_index[0]]["Parallel"]+"”"+"和"+"“"+parallelrelation[two_index[1]]["Parallel"]+"”"+"是互相替代的关系。"
                confuse_string_list.append(confuse_string1)
                confuse_string_list.append(confuse_string2)
                confuse_string_list.append(confuse_string3)
            #收集拼接的字符串返回
            return confuse_string_list

    def parallel_confuse_three(self,list_three_parallelrelation,parallelrelation,parallel_head):
            '''
                方法参数：
                list_two_parallelrelation:随机数列表
                parallelrelation:并置关系词典
                parallel_head:并置关系头

                返回值:
                confuse_string_list:拼接后的经过混淆的字符串列表
            '''
            # 按照架构设计拼接字符串
            confuse_string_list=[]
            for three_index in list_three_parallelrelation:
                    confuse_string=parallel_head+"中，按重要性排序为："+"“" +parallelrelation[three_index[0]]["Parallel"]+"”"+">"+"“"+parallelrelation[three_index[1]]["Parallel"]+"”"+">"+"“"+parallelrelation[three_index[2]]["Parallel"]+"”"+"。"
                    confuse_string_list.append(confuse_string)

            return confuse_string_list
