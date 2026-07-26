'''
3.28 数值约束的具体数值判定——覆盖数值敏感性

版本迭代情况:
[脱敏] 版本迭代记录

本组件存在库依赖,内部依赖
库依赖:
jsonschema==4.24.0

内部依赖:3.21，3.23
3.21:make_Json
3.23:日志管理组件
'''
import json
from decimal import Decimal
from time import time
import jsonschema
from jsonschema import validate
from config import config_choice
from src.make_json import make_JSON


class AttValueJudge:
    def __init__(self,log_manager):
        '''
        类变量：
        cond_validation_string:推理关系使用校验的Schema
        cond_validation_schema:判断是否符合推理关系schema
        log_manager:日志管理类
        '''
        cond_validation_string = config_choice.CONSTRAINT_SCHEMA
        self.cond_validation_schema = json.loads(cond_validation_string)
        self.log_manager = log_manager

    def generate_choice(self, knowid, knowstr, knowcata, inference):
        """ 算法的核心部分，通过这里完成选项的生成任务。
            函数参数：
                knowid：知识唯一标识，一个字符串。
                knowstr：知识内容，一个字符串。
                knowcata：知识目录标识，一个字符串。
                parallelrelation：并置关系

            返回值：
                generate_result，一个列表，列表中的每个元素为一个满足选项schema的JSON。

            异常处理：notice和corrupt
                notice:
                    1.判断推理规则列表是否为空；如果为空，说明该知识不能应用此算法进行选项生成，jsonschema.exceptions.ValidationError异常，错误类型为notice-9。
                    2.判断推理规则列表是否存在数值约束；如果不存在，说明该知识不能应用此算法进行选项生成，错误类型为notice-11。
                corrupt:
                    1.当抛出jsonschema.exceptions.SchemaError异常
            运行日志记录：
                成功生成选项时，将生成选项信息写入运行日志
        """
        # 存储生成选项结果，初始列表为空。
        self.knowid = knowid
        generate_result = []

        # 如果inference为空，长度为0，直接返回结果。
        if len(inference) == 0:
            self.log_manager.generate_error_log(time(), knowid, "att_value_judge", "notice", 9,
                                                "推理列表为空")
            return generate_result
        # 保证推理前件和后件都有cond 否则直接返回
        try:
            # 推理前件
            antecedent_constraint = inference['antecedent']['cond']
            # 推理后件
            consequence_constraint = inference['consequence']['cond']
        except jsonschema.exceptions.SchemaError as e:
            self.log_manager.generate_error_log(time(), knowid, "att_value_judge", "corrupt", 1, str(e))
            return generate_result


        whether_validate = 0
        try:  # 验证推理前件
            validate(schema=self.cond_validation_schema, instance=antecedent_constraint)
        except jsonschema.exceptions.SchemaError as e:
            # 不符合约束schema是触发corrupt，输出到日志中
            self.log_manager.generate_error_log(time(), knowid, "att_value_judge", "corrupt", 1, str(e))
            whether_validate = 1
        except jsonschema.exceptions.ValidationError as e:
            # jsonschema.exceptions.ValidationError异常，属于notice情况
            self.log_manager.generate_error_log(time(), knowid, "att_value_judge", "notice", 9, str(e))
            whether_validate = 1

        try:  # 验证推理后件
            validate(schema=self.cond_validation_schema, instance=consequence_constraint)
        except jsonschema.exceptions.SchemaError as e:
            # 不符合约束schema是触发corrupt，输出到日志中
            self.log_manager.generate_error_log(time(), knowid, "att_value_judge", "corrupt", 1, str(e))
            whether_validate = 1
        except jsonschema.exceptions.ValidationError as e:
            # 推理列表为空的情况走的jsonschema.exceptions.ValidationError异常，属于notice情况
            self.log_manager.generate_error_log(time(), knowid, "att_value_judge", "notice", 9, str(e))
            whether_validate = 1
        if whether_validate != 0:  # 此时约束不满足条件，返回空列表。
            return generate_result
        '''
        如果推理后件均不含数值约束，直接返回空集合
        '''
        if ("verb" in consequence_constraint["constraint"] or "entity" in consequence_constraint["constraint"]):
            self.log_manager.generate_error_log(time(), knowid, "att_value_judge", "notice", 11,
                                                "推理后件中不含数值约束")
            return generate_result
        #初始化列表 存储转化后的约束
        consequence_confuse_string_list=[]
        # 如果是数值约束 而且 数值约束的值不为零的情况下才进行处理
        if("compare" in consequence_constraint["constraint"] and  consequence_constraint["constraint"]["index"] != 0):
            # 获取数值变化后的字符串
            consequence_confuse_string_list=self._confuse_value_constraint(consequence_constraint)



        # 如果转换后的字符串列表为空，表明可能是数值约束的数值为0或者是存在约束，不进行操作
        #如果转换后的字符串列表为空，表明可能是数值约束的数值为0或者是存在约束，不进行操作
        '''
        事实上，如果修改推理前件，很难判断整个题目的真值，因此只修改推理后件。
        '''
        if(len(consequence_confuse_string_list)!=0):
            value_list = self._judge_value(consequence_constraint)
            if "verb" in antecedent_constraint['constraint'] or "entity" in antecedent_constraint['constraint']:
                for i in range(4):
                    res_string="如果" +self._existence_to_string(antecedent_constraint)+"，"+consequence_confuse_string_list[i]+"，是合理的。"
                    generate_result.append(make_JSON(knowid + "28" + str(len(generate_result) + 1).zfill(2),res_string,value_list[i],6,knowid))
            else:
                for i in range(4):
                    res_string="如果" + self._number_to_string(antecedent_constraint)+ "，" +  consequence_confuse_string_list[i] + "，是合理的。"
                    generate_result.append(make_JSON(knowid + "28" + str(len(generate_result) + 1).zfill(2), res_string, value_list[i], 6,knowid))

        # 算法执行到最后，如果没有发现问题，就写入运行日志
        self.log_manager.generate_run_log(time(), knowid, "att_value_judge", len(generate_result))
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

    def _confuse_value_constraint(self,cond):
        '''
        函数参数：
            cond:表示前件/后件约束
        返回值：
            confuse_string:字符串列表
        '''
        confuse_string=[]
        #进行数值改变，倍数分别是1.2，1.1，0.9，0.8。倍数大于一和小于一具有不同的真值
        confuse_string.append(cond["entity"]+"等于"+str(Decimal(str(cond["constraint"]["index"]*Decimal("1.2"))))+cond["constraint"]["unit"])
        confuse_string.append(cond["entity"]+"等于"+str(Decimal(str(cond["constraint"]["index"]*Decimal("1.1"))))+cond["constraint"]["unit"])
        confuse_string.append(cond["entity"]+"等于"+str(Decimal(str(cond["constraint"]["index"]*Decimal("0.9"))))+cond["constraint"]["unit"])
        confuse_string.append(cond["entity"]+"等于"+str(Decimal(str(cond["constraint"]["index"]*Decimal("0.8"))))+cond["constraint"]["unit"])
        return confuse_string

    def _judge_value(self,cond):
        '''
        函数参数：
            cond:表示前件/后件约束
        返回值:
            judge_value 选项真值列表
        '''
        judge_bool=[]
        '''
        具体的真值需要参考confuse_value_constraint，通过约束进行判断
        '''
        if((cond["constraint"]["compare"]=="large" and cond["bool"]==True)
                or (cond["constraint"]["compare"]=="below" and cond ["bool"]==False)
                or (cond["constraint"]["compare"] == "belowequal" and cond["bool"] == False)
                or (cond["constraint"]["compare"]=="largeequal" and cond["bool"]==True)
        ):
            judge_bool.append(True)
            judge_bool.append(True)
            judge_bool.append(False)
            judge_bool.append(False)
            return judge_bool
        elif ((cond["constraint"]["compare"] == "large" and cond["bool"] == False)
                or (cond["constraint"]["compare"] == "below" and cond["bool"] == True)
                or (cond["constraint"]["compare"] == "belowequal" and cond["bool"] == True)
                or (cond["constraint"]["compare"] == "largeequal" and cond["bool"] == False)
        ):
            judge_bool.append(False)
            judge_bool.append(False)
            judge_bool.append(True)
            judge_bool.append(True)
            return judge_bool
        #以上两种情况枚举了8种类型，大于，不大于，小于，不下于，不大于等于，不小于等于，小于等于，大于等于
        #剩下之后两种情况，等于和不等于，显然经过数值更改之后，选项的真值都是false
        else:
            judge_bool.append(False)
            judge_bool.append(False)
            judge_bool.append(False)
            judge_bool.append(False)
            return judge_bool