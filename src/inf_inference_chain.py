"""
3.18 推理链关系的陈述内容生成-覆盖推理可靠性

版本迭代：
[脱敏] 版本迭代记录
[脱敏] 版本迭代记录
[脱敏] 版本迭代记录

库依赖情况:
schema==0.7.7

本组件存在外部依赖：
外部依赖：调用推理图谱的给定约束若干步推理目标获取
大模型依赖：语言优化

为了保证相关参数可配置，本代码相关变量放到config文件夹中的config_choice文件中。
配置变量适用情况：
REFINE_PROMPT:用以引导大模型实现润色任务。
COND_CONSTRAINT_SCHEMA:验证推理前件部分JSON的schema。
CONSEQUENCE_SCHEMA ：用于验证推理后件JSON的schema
"""

from time import time
import jsonschema
from jsonschema import validate
import json
import config.config_choice
from src.call_LLM import call_LLM
from src.make_json import make_JSON

# 桩程序，模拟外部依赖。
from src.stack import get_n_step_consequence

class InfInferenceChain:
    '''推理链关系的陈述内容生成-覆盖推理可靠性

    类变量：
    refine_prompt：由大语言模型完成精炼的输入提示信息。
    cond_validation_schema：验证推理cond部分JSON的schema。
    consequence_validation_string：验证推理后件JSON的schema。
    log_manager：记录日志信息的对象
    '''

    def __init__(self,log_manager):
        ''' 类构造函数。本类的相关变量与3.17非常相似，对相关类变量从配置文件中赋值即可。
        '''
        self.refine_prompt = config.config_choice.REFINE_PROMPT
        cond_validation_string = config.config_choice.COND_CONSTRAINT_SCHEMA

        self.cond_validation_schema = json.loads(cond_validation_string)
        '''
        推理后件的验证schema需要独立再写一个；实际上就是在cond外面套一个cond的描述。
        '''
        consequence_validation_string = config.config_choice.CONSEQUENCE_SCHEMA
        self.consequence_schema = json.loads(consequence_validation_string)
        #传入日志管理器对象
        self.log_manager = log_manager

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
        """将数值约束转换为字符串。

        函数参数：
            cond：约束，一个JSON。

        返回值：
            merge_string，一个组合后的字符串。
        """

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
        """ 字符串构造函数，采用“<front部分>时，<back>”的格式。
        
        函数参数：
            front：推理前件，一个JSON，符合cond schema。
            back：推理后件，一个JSON，符合cond schema。

        返回值：
            merge_string，一个组合后的字符串。

        """

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
        """算法的核心部分，通过该步完成选项的构建。

        函数参数：
            knowid：知识唯一标识，一个字符串。
            knowstr：知识内容，一个字符串。
            knowcata：知识目录标识，一个字符串。
            inference：推理规则，它是符合inference schema的JSON格式。

        返回值：
            generate_result，一个列表，列表中的每个元素为一个满足选项schema的JSON。

        基本思想：
        1. 判断推理列表是否为空；如果为空，说明该知识不能应用此算法进行选项生成（这种现象会很常见）。
        2. 寻找推理列表的前件，使用知识实体建模过程中的内容，获取推理跳数为n的推理后件。
        3. 以知识内容的推理前件和2中得到的推理后件，构建选项内容。
        4. 选项真值（"value"）为真。
        5. 处理知识唯一标识（"knowid"）、知识目录（"knowcata"）属性，构建选项唯一标识（"id"）、选项关联知识（"cataid"）、选项关联指标（"evaluation"）。

        异常处理:
            notice:
                1.知识推理列表为空，或者知识不存在推理列表。
                2.jsonschema验证抛出jsonschema.exceptions.ValidationError异常。
            warning:
                1.远程调用大模型时，尝试数次仍不能返回有效结果。
                2.使用外部依赖时出现异常
            corrupt:
                1:jsonschema验证抛出jsonschema.exceptions.SchemaError异常。

             运行日志记录：
                 成功生成选项时，将生成选项信息写入运行日志
        """

        # 存储生成选项结果，初始列表为空。
        generate_result = []

        '''
        判断推理列表是否为空、前件是否符合schema。我们只对推理前件寻找合适的实体，因此推理后件我们不去进行验证。
        '''
        if len(inference) == 0:
            self.log_manager.generate_error_log(time(),knowid,"inf_inference_chain","notice",9,"推理列表为空")
            return generate_result # 如果推理列表为空，直接结束。
        whether_validate = 0 # 判断推理前件的cond是否符合schema。
        antecedent_source = inference["antecedent"]["cond"]
        
        try:
            validate(antecedent_source, self.cond_validation_schema)
        except jsonschema.exceptions.ValidationError as e:
            self.log_manager.generate_error_log(time(),knowid,"inf_inference_chain","notice",9,"json验证："+str(e))
            whether_validate = 1
        except jsonschema.exceptions.SchemaError as e:
            self.log_manager.generate_error_log(time(),knowid,"inf_inference_chain","corrupt",1,"json验证："+str(e))
            whether_validate = 1

        if whether_validate != 0:
            return generate_result
        
        '''
        调用外部依赖接口，分别获取推理前件2步、3步范围的JSON。
        接口统一为["antecedent"]、["consequence"]内部的内容。
        考虑到该算法复杂度随n多项式级提升，且3步以上的推理在知识中应当并不常见，因此只采用推理步数为2和3的情况。
        如果外部依赖发生错误，此处写入日志，exception类型为 warning，算法继续执行，跳过此对应步数的推理后件
        '''
        consequence_2_step_list = []
        consequence_3_step_list = []

        try:
            consequence_2_step_list = get_n_step_consequence(inference["antecedent"], 2)
        except Exception as e:
            self.log_manager.generate_error_log(time(), knowid, "inf_inference_chain", "warning", 2,"外部依赖调用："+str(e))


        try:
            consequence_3_step_list = get_n_step_consequence(inference["antecedent"], 3)
        except Exception as e:
            self.log_manager.generate_error_log(time(), knowid, "inf_inference_chain", "warning", 2,"外部依赖调用："+str(e))
        '''
        将返回结果组织成原始字符串，存储在string_description_list列表中。
        '''

        string_description_list = []
        if consequence_2_step_list:
            for consequence in consequence_2_step_list:
                try: # 验证该consequence是否符合schema，否则直接跳过。
                    validate(consequence, self.consequence_schema)
                except jsonschema.exceptions.ValidationError as e:
                    self.log_manager.generate_error_log(time(),knowid,"inf_inference_chain","notice",9,"json验证："+str(e))
                    continue
                except jsonschema.exceptions.SchemaError as e:
                    self.log_manager.generate_error_log(time(),knowid,"inf_inference_chain","corrupt",1,"json验证："+str(e))
                    continue
                string_description_list.append(self._make_string(antecedent_source, consequence["cond"]))

        if consequence_3_step_list:
            for consequence in consequence_3_step_list:
                try: # 验证该consequence是否符合schema，否则直接跳过。
                     validate(consequence, self.consequence_schema)
                except jsonschema.exceptions.ValidationError as e:
                    self.log_manager.generate_error_log(time(),knowid,"inf_inference_chain","notice",9,"json验证："+str(e))
                    continue
                except jsonschema.exceptions.SchemaError as e:
                    self.log_manager.generate_error_log(time(),knowid,"inf_inference_chain","corrupt",1,"json验证："+str(e))
                    continue
                string_description_list.append(self._make_string(antecedent_source, consequence["cond"]))


        '''
        利用大语言模型进行表达上的润色工作。
        '''
        string_refined_list = []
        for string in string_description_list:
            give_prompt = "“" + string + "”\n" + self.refine_prompt
            try:
                result_string = self._process_LLM_answer(call_LLM(give_prompt))
                string_refined_list.append(result_string)
            except Exception as e:
                #如果大模型调用发生错误，写入日志
                self.log_manager.generate_error_log(time(), knowid, "inf_inference_chain", "warning", 1, "大模型调用："+str(e))
                string_refined_list.append(string)


        '''
        组织成JSON。
        '''
        for i in range(0, len(string_refined_list)):
            generate_result.append(make_JSON(knowid + "18" + str(i).zfill(2), string_refined_list[i], True, 5, knowcata))

        #如果运行到最后没有问题，就写入运行日志
        self.log_manager.generate_run_log(time(), knowid, "inf_inference_chain", len(generate_result))

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