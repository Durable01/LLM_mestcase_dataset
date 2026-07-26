'''
3.17 单一推理关系的陈述内容生成-覆盖推理可靠性

为了保证相关参数可配置，本代码相关变量放到config文件夹中的config_choice_3_17文件中。


版本迭代:
[脱敏] 版本迭代记录
[脱敏] 版本迭代记录
[脱敏] 版本迭代记录
[脱敏] 版本迭代记录

库依赖情况:
openai==1.93.0
schema==0.7.7

本组件存在内部依赖:
内部依赖：调用3.3接口
大模型依赖：语言优化

配置变量使用情况:
API_KEY:调用deepseek时需要的内容。
REFINE_PROMPT:用以引导大模型实现润色任务。
COND_CONSTRAINT_SCHEMA:用以验证inference的前件和后件是否符合单一cond的schema约束规则。
'''
from time import time

import jsonschema
from jsonschema import validate
from openai import OpenAI
import json
import copy
import config.config_choice
from src.call_LLM import call_LLM
from src.log_manager import LogManager
from src.make_json import make_JSON

# 桩程序，模拟内部依赖。
from src.rely_IG_check import check_inference_consistency

class InfSingleInference:
    '''单一（single）推理关系（Inference）的陈述内容生成。该指标覆盖推理可靠性。

    属性：
        api_key，调用deepseek时需要的内容。
        refine_prompt，用以引导大模型实现润色任务。
        cond_validation_schema，用以验证inference的前件和后件是否符合单一cond的schema约束规则。
        log_manager,用于日志管理
    '''    

    def __init__(self,log_manager):
        ''' 类构造函数，从config文件中读取refine_prompt。
        '''
        self.log_manager = log_manager
        self.api_key = config.config_choice.API_KEY
        self.refine_prompt = config.config_choice.REFINE_PROMPT
        cond_validation_string = config.config_choice.COND_CONSTRAINT_SCHEMA
        self.cond_validation_schema = json.loads(cond_validation_string)

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

    def _make_string(self, front, back):
        ''' 字符串构造函数，采用“<front部分>时，<back>”的格式。
        
        函数参数：
            front：推理前件，一个JSON，符合cond schema。
            back：推理后件，一个JSON，符合cond schema。

        返回值：
            merge_string，一个组合后的字符串。

        '''

        # 存储返回结果，初始为初始衔接词
        merge_string = "如果"
        # 对推理前件分情况讨论
        if "verb" in front["constraint"] or "entity" in front["constraint"]: # verb字段只出现在存在约束中，此时调用存在约束转换函数
            merge_string = merge_string + self._existence_to_string(front)
        elif "compare" in front["constraint"]: #compare字段只出现在数值约束中，此时调用数值约束转换函数
            merge_string = merge_string + self._number_to_string(front)
        # 添加描述衔接词
        merge_string = merge_string + "，那么" # 添加分隔符
        # 对推理后件分情况讨论
        if "verb" in back["constraint"] or "entity" in back["constraint"]:
            merge_string = merge_string + self._existence_to_string(back)
        elif "compare" in back["constraint"]:
            merge_string = merge_string + self._number_to_string(back)
        # 添加描述结尾词，返回结果
        merge_string = merge_string + "。"
        return merge_string


    def generate_choice(self, knowid, knowstr, knowcata, inference):
        ''' 算法的核心部分，通过这里完成选项的生成任务。

        函数参数：
            knowid：知识唯一标识，一个字符串。
            knowstr：知识内容，一个字符串。
            knowcata：知识目录标识，一个字符串。
            inference：推理规则，它是符合inference schema的JSON格式。

        返回值：
            generate_result，一个列表，列表中的每个元素为一个满足选项schema的JSON。

        异常处理:
            notice:
                1.知识推理列表为空，或者知识不存在推理列表。
            warning:
                1.远程调用大模型时，尝试数次仍不能返回有效结果。
            error:
                1:使用内部依赖时出现异常。
            corrupt:
                1:jsonschema验证抛出jsonschema.exceptions.SchemaError异常。

        运行日志记录：
            成功生成选项时，将生成选项信息写入运行日志
        
        '''

        # 存储生成选项结果，初始列表为空。
        generate_result = []
        """如果inference为空,直接返回。"""
        if not inference:  # 同时覆盖 None、空字典 {} 等无效情况
            self.log_manager.generate_error_log(time(), knowid, "inf_single_inference", "notice", 9, "推理内容为空或无效")
            return generate_result
            
        # 获取前后件
        antecedent_constraint = inference['antecedent']
        consequence_constraint = inference['consequence']

        whether_validate = 0    
        try: # 验证推理前件
            antecedent_constraint_cond=antecedent_constraint['cond']
            validate(schema = self.cond_validation_schema, instance = antecedent_constraint_cond)
        except jsonschema.exceptions.ValidationError as e:
            self.log_manager.generate_error_log(time(),knowid,"inf_single_inference","notice",9,str(e))
            whether_validate = 1
        except jsonschema.exceptions.SchemaError as e:
            self.log_manager.generate_error_log(time(),knowid,"inf_single_inference","corrupt",1,str(e))
            whether_validate = 1

        try: # 验证推理后件
            consequence_constraint_cond=consequence_constraint['cond']
            validate(schema = self.cond_validation_schema, instance = consequence_constraint_cond)
        except jsonschema.exceptions.ValidationError as e:
            self.log_manager.generate_error_log(time(), knowid, "inf_single_inference", "notice", 9, str(e))
            whether_validate = 1
        except jsonschema.exceptions.SchemaError as e:
            self.log_manager.generate_error_log(time(), knowid, "inf_single_inference", "corrupt", 1, str(e))
            whether_validate = 1


        if whether_validate != 0: # 此时约束不满足条件，返回空列表。
            return generate_result
        
        '''
        构建逆命题、否命题、逆否命题的推理约束，前件与后件分开存储。
        '''

        # 逆命题，采用adverse前缀；用front和back表示前件和后件。
        adverse_front = copy.deepcopy(consequence_constraint)
        adverse_back = copy.deepcopy(antecedent_constraint)
        # 否命题，原命题的前件和后件全部取反。
        negative_front = copy.deepcopy(antecedent_constraint)
        negative_back = copy.deepcopy(consequence_constraint)
        # 取反需要修改bool值。
        negative_front['cond']["bool"] = not negative_front['cond']["bool"]
        negative_back['cond']["bool"] = not negative_back['cond']["bool"]
            
        # 逆否命题，采用adv_neg前缀，表示adverse_negative。
        adv_neg_front = copy.deepcopy(consequence_constraint)
        adv_neg_back = copy.deepcopy(antecedent_constraint)
        
        # 使用not运算符直接取反
        adv_neg_front['cond']["bool"] = not adv_neg_front['cond']["bool"]
        adv_neg_back['cond']["bool"] = not adv_neg_back['cond']["bool"]
        
        '''
        将逆命题、否命题和逆否命题变换为字符串，采用相同的前缀、后缀为string表示。
        '''

        adverse_string = "“"+self._make_string(adverse_front['cond'], adverse_back['cond'])+ "”\n" + self.refine_prompt
        negative_string = "“" + self._make_string(negative_front['cond'], negative_back['cond'])+ "”\n" + self.refine_prompt
        adv_neg_string = "“" + self._make_string(adv_neg_front['cond'], adv_neg_back['cond'])+ "”\n" + self.refine_prompt

        '''
        使用大语言模型对表达进行优化。
        '''
        try:
            #调用大模型对表达进行优化，处理大模型返回的字符串
            adverse_string = self._process_LLM_answer(call_LLM(adverse_string))
        except Exception as e:
            #如果大模型调用发生错误，写入日志
            self.log_manager.generate_error_log(time(), knowid, "inf_single_inference", "warning", 1, str(e))
            #返回原字符串
            adverse_string=self._make_string(adverse_front['cond'], adverse_back['cond'])
        try:
            negative_string =self._process_LLM_answer(call_LLM(negative_string))
        except Exception as e:
            # 如果大模型调用发生错误，写入日志
            self.log_manager.generate_error_log(time(), knowid, "inf_single_inference", "warning", 1, str(e))
            # 返回原字符串
            negative_string=self._make_string(negative_front['cond'], negative_back['cond'])
        try:
            adv_neg_string = self._process_LLM_answer(call_LLM(adv_neg_string))
        except Exception as e:
            # 如果大模型调用发生错误，写入日志
            self.log_manager.generate_error_log(time(), knowid, "inf_single_inference", "warning", 1, str(e))
            # 返回原字符串
            adv_neg_string=self._make_string(adv_neg_front['cond'], adv_neg_back['cond'])

        '''
        查询逆命题的真值，确定逆命题和否命题的真值。
        '''
        try:
            source_truth = True
            adverse_truth = check_inference_consistency(adverse_front, adverse_back)
        except Exception as e:
            self.log_manager.generate_error_log(time(), knowid, "inf_single_inference", "warning", 2, str(e))
            return generate_result


        '''
        构建JSON，包括id，text，value，evaluation，cataid。
        其中id为knowid+17（本算法编号为17），按顺序为逆命题、否命题、逆否命题生成01、02、03；
        text为对应字符串，adverse_string、negative_string、adv_neg_string。
        value为对应真值，adv_neg使用source_truth，其余两个使用adverse_truth。
        evaluation为推理可靠性，整数为5。
        cataid使用knowcata。
        '''
        #调用内部以来的make_json函数
        generate_result.append(make_JSON(knowid + "1701", adverse_string, adverse_truth, 5, knowcata))
        generate_result.append(make_JSON(knowid + "1702", negative_string, adverse_truth, 5, knowcata))
        generate_result.append(make_JSON(knowid + "1703", adv_neg_string, source_truth, 5, knowcata))
        #如果运行到最后没有问题，就写入运行日志
        self.log_manager.generate_run_log(time(), knowid, "inf_single_inference", len(generate_result))
        #返回结果
        return generate_result

    def _process_LLM_answer(self,LLM_answer):
        #处理大模型返回的字符串为可用的结果
        if LLM_answer != "":
            pos_start = LLM_answer.find("陈述：")
            LLM_answer = LLM_answer[pos_start + 3:]
            pos_end = LLM_answer.find("\n")
            LLM_answer = LLM_answer[0: pos_end]
            return LLM_answer
        else:
            return""
