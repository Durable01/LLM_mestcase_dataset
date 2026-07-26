"""
3.29 数值约束的模糊语义干扰——覆盖意图语义准确性

版本迭代情况：
[脱敏] 版本迭代记录

库依赖情况
openai==1.92.0
jsonschema==0.7.7

本组件存在大模型依赖(使用组件3.23实现)
本组件存在内部依赖：3.21组件make_json,3.23组件log_manager

配置变量使用情况:
API_KEY:调用deepseek的密钥
ATTFUZZY_PROMPT:大模型提示词
CONSTRAINT_SCHEMA:约束schema字符串
"""
import json
import jsonschema
import jsonschema.exceptions
from jsonschema import validate
import copy
from time import time
from config import config_choice
from src.make_json import make_JSON
from src.call_LLM import call_LLM

class AttFuzzyInference:
    def __init__(self, log_manager):
        self.log_manager = log_manager
        cond_validation_string = config_choice.CONSTRAINT_SCHEMA
        self.cond_validation_schema = json.loads(cond_validation_string)
        self.componentid = "att_fuzzy_inference"
        
    def generate_choice(self, knowid, knowstr, knowcata, inference):
        """
        基本功能：
            基于给定的knowid，knowstr,knowcata,inference，生成数值约束的模糊语义干扰选项

        函数参数：
            knowid：知识唯一标识，一个字符串。
            knowstr：知识内容，一个字符串。
            knowcata：知识目录标识，一个字符串。
            inference：推理规则，它是符合inference schema的JSON格式。
        
        返回值:
            generate_result，一个列表，列表中的每个元素为一个满足选项schema的JSON。
        
        异常处理：notice、warning和corrupt
            notice:
                1.知识推理列表为空
                2.知识列表没有数值约束
            warning:
                1.大模型调用异常
            corrupt:
                1.jsonschema验证抛出jsonschema.exceptions.SchemaError异常。

        运行日志记录：
            成功生成选项时，将生成选项信息写入运行日志
        """
        # 存储生成选项结果，初始列表为空
        generate_result = []

        # 如果inference为空，长度为0，直接返回结果
        if len(inference) == 0:
            self.log_manager.generate_error_log(time(), knowid, "att_fuzzy_inference", "notice", 9, "推理列表为空")
            return generate_result
        
        # 保证推理前件和后件都有cond 否则直接返回
        try:
            # 推理前件
            antecedent_constraint = inference['antecedent']['cond']
            # 推理后件
            consequence_constraint = inference['consequence']['cond']
        except jsonschema.exceptions.SchemaError as e:
            self.log_manager.generate_error_log(time(), knowid, "att_fuzzy_inference", "corrupt", 1, str(e))
            return generate_result

        whether_validate = 0
        try:  # 验证推理前件
            validate(schema=self.cond_validation_schema, instance=antecedent_constraint)
        except jsonschema.exceptions.SchemaError as e:
            self.log_manager.generate_error_log(time(), knowid, "att_fuzzy_inference", "corrupt", 1, str(e))
            whether_validate = 1
        except jsonschema.exceptions.ValidationError as e:
            self.log_manager.generate_error_log(time(), knowid, "att_fuzzy_inference", "notice", 9, str(e))
            whether_validate = 1

        try:  # 验证推理后件
            validate(schema=self.cond_validation_schema, instance=consequence_constraint)
        except jsonschema.exceptions.SchemaError as e:
            self.log_manager.generate_error_log(time(), knowid, "att_fuzzy_inference", "corrupt", 1, str(e))
            whether_validate = 1
        except jsonschema.exceptions.ValidationError as e:
            self.log_manager.generate_error_log(time(), knowid, "att_fuzzy_inference", "notice", 9, str(e))
            whether_validate = 1
        if whether_validate != 0:
            return generate_result

        # 如果推理前件和推理后件均不含数值约束，直接返回空集合
        if ("verb" in antecedent_constraint["constraint"] or "entity" in antecedent_constraint["constraint"]) and ("verb" in consequence_constraint["constraint"] or "entity" in consequence_constraint["constraint"]):
            self.log_manager.generate_error_log(time(), knowid, "att_fuzzy_inference", "notice", 11, "推理列表中不含数值约束")
            return generate_result

        antecedent_constraint_exist = False
        consequence_constraint_exist = False

        if ("compare" in antecedent_constraint["constraint"]):
            antecedent_constraint_exist = True
        if ("compare" in consequence_constraint["constraint"]):
            consequence_constraint_exist = True

        cnt = 0
        # 前件和后件都有数值约束
        if antecedent_constraint_exist and consequence_constraint_exist:
            # 处理前件约束
            both_options = self._generate_both_fuzzy_options(antecedent_constraint, consequence_constraint)
            for option in both_options:
                generate_result.append(make_JSON(knowid + "29" + str(cnt).zfill(2), option, False, 13, knowcata))
                cnt += 1
        # 前件有数值约束，后件没有
        elif antecedent_constraint_exist and not consequence_constraint_exist:
            ante_options = self._generate_single_fuzzy_options(antecedent_constraint, consequence_constraint, "antecedent")
            for option in ante_options:
                generate_result.append(make_JSON(knowid + "29" + str(cnt).zfill(2), option, False, 13, knowcata))
                cnt += 1

        # 后件有数值约束，前件没有
        elif not antecedent_constraint_exist and consequence_constraint_exist:
            cons_options = self._generate_single_fuzzy_options(antecedent_constraint, consequence_constraint, "consequence")
            for option in cons_options:
                generate_result.append(make_JSON(knowid + "29" + str(cnt).zfill(2), option, False, 13, knowcata))
                cnt += 1
        prompt = config_choice.ATT_FUZZY_PROMPT
        
        for i in range(len(generate_result)):
            original_knowstr = generate_result[i]['text']
            LLM_input = original_knowstr + "\n" + prompt
            try:
                LLM_output = call_LLM(LLM_input)
                # 去掉陈述： 前缀
                LLM_output = LLM_output.replace("陈述：", "").strip()
            except Exception as e:
                self.log_manager.generate_error_log(time(), knowid, self.componentid, "warning", 1, str(e))
                continue
            generate_result[i]['text'] = LLM_output.strip()
            
        # 运行到最后没有问题，输出到运行日志
        if len(generate_result) > 0:
            self.log_manager.generate_run_log(time(), knowid, self.componentid, len(generate_result))

        return generate_result

    def _generate_single_fuzzy_options(self, antecedent_constraint, consequence_constraint, constraint_position):
        """
        生成模糊语义选项

        参数：
            antecedent_constraint: 推理前件
            consequence_constraint: 推理后件
            constraint_position: 约束位置("antecedent"或"consequence")

        返回值：
            选项列表
        """
        options = []
        
        if constraint_position == "antecedent":
            target_constraint = antecedent_constraint
            other_constraint = consequence_constraint
        else:
            target_constraint = consequence_constraint
            other_constraint = antecedent_constraint
            
        compare_type = target_constraint["constraint"]["compare"]
        
        # 根据约束类型生成模糊语义选项
        if compare_type in ["large", "largeequal"]:
            # 生成2个模糊语义选项：越小越好、尽可能小
            fuzzy_expressions = ["越小越好", "尽可能小"]
            for expression in fuzzy_expressions:
                fuzzy_option = self._create_fuzzy_option(antecedent_constraint, consequence_constraint,constraint_position, expression)
                options.append(fuzzy_option)
                
        elif compare_type in ["below", "belowequal"]:
            # 生成2个模糊语义选项：越大越好、尽可能大
            fuzzy_expressions = ["越大越好", "尽可能大"]
            for expression in fuzzy_expressions:
                fuzzy_option = self._create_fuzzy_option(antecedent_constraint, consequence_constraint, constraint_position,expression)
                options.append(fuzzy_option)
                
        elif compare_type == "equal":
            # 生成4个模糊语义选项
            fuzzy_expressions = ["越小越好", "尽可能小", "越大越好", "尽可能大"]
            for expression in fuzzy_expressions:
                fuzzy_option = self._create_fuzzy_option(antecedent_constraint, consequence_constraint, constraint_position,expression)
                options.append(fuzzy_option)
                
        # notequal类型不生成额外选项
        
        return options

    def _create_fuzzy_option(self, antecedent_constraint, consequence_constraint, constraint_position, fuzzy_expression):
        """
        创建模糊语义选项

        参数：
            antecedent_constraint: 推理前件
            consequence_constraint: 推理后件
            constraint_position: 约束位置
            fuzzy_expression: 模糊表达

        返回值：
            模糊语义选项字符串
        """
        if constraint_position == "antecedent":
            # 修改前件
            fuzzy_antecedent = copy.deepcopy(antecedent_constraint)
            fuzzy_antecedent["constraint"] = {"fuzzy_expression": fuzzy_expression}
            return self._make_string(fuzzy_antecedent, consequence_constraint)
        else:
            # 修改后件
            fuzzy_consequence = copy.deepcopy(consequence_constraint)
            fuzzy_consequence["constraint"] = {"fuzzy_expression": fuzzy_expression}
            return self._make_string(antecedent_constraint, fuzzy_consequence)

    def _generate_both_fuzzy_options(self, antecedent_constraint, consequence_constraint): 
        """
        生成前件和后件均为模糊语义的选项

        参数：
            antecedent_constraint: 推理前件
            consequence_constraint: 推理后件
        """
        options=[]

        ante_compare_type = antecedent_constraint["constraint"]["compare"]
        cons_compare_type = consequence_constraint["constraint"]["compare"]
        ante_fuzzy_expressions = self._get_fuzzy_expressions(ante_compare_type)
        cons_fuzzy_expressions = self._get_fuzzy_expressions(cons_compare_type)
        for ante_expression in ante_fuzzy_expressions:
            for cons_expression in cons_fuzzy_expressions:
                fuzzy_antecedent = copy.deepcopy(antecedent_constraint)
                fuzzy_antecedent["constraint"] = {"fuzzy_expression": ante_expression}
                fuzzy_consequence = copy.deepcopy(consequence_constraint)
                fuzzy_consequence["constraint"] = {"fuzzy_expression": cons_expression}
                option_string = self._make_string(fuzzy_antecedent, fuzzy_consequence)
                options.append(option_string)
        return options

    def _get_fuzzy_expressions(self, compare_type):
        """
        根据比较类型获取对应的模糊表达式
        
        参数：
            compare_type: 比较类型
            
        返回值：
            模糊表达式列表
        """
        if compare_type in ["large", "largeequal"]:
            return ["越小越好", "尽可能小"]
        elif compare_type in ["below", "belowequal"]:
            return ["越大越好", "尽可能大"]
        elif compare_type == "equal":
            return ["越小越好", "尽可能小", "越大越好", "尽可能大"]
        else:  # notequal等其他类型
            return []

    def _number_to_string(self, cond):
        """ 将数值约束转换为字符串。"""
        merge_string = ""
        merge_string = merge_string + cond["entity"]
        if cond["bool"] == False:
            merge_string = merge_string + "没有"
        
        cond_constraint = cond["constraint"]
        
        # 检查是否为模糊语义约束
        if "fuzzy_expression" in cond_constraint:
            merge_string = merge_string + cond_constraint["fuzzy_expression"]
        else:
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
        """ 将存在约束转换为字符串。"""
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
        """ 字符串构造函数，采用"如果<front部分>，那么<back>"的格式。"""
        merge_string = "如果"
        
        # 对推理前件分情况讨论
        if "verb" in front["constraint"] or "entity" in front["constraint"]:
            merge_string = merge_string + self._existence_to_string(front)
        elif "fuzzy_expression" in front["constraint"] or "compare" in front["constraint"]:
            merge_string = merge_string + self._number_to_string(front)
        
        merge_string = merge_string + "，那么"
        
        # 对推理后件分情况讨论
        if "verb" in back["constraint"] or "entity" in back["constraint"]:
            merge_string = merge_string + self._existence_to_string(back)
        elif "fuzzy_expression" in back["constraint"] or "compare" in back["constraint"]:
            merge_string = merge_string + self._number_to_string(back)
        
        merge_string = merge_string + "。"
        return merge_string