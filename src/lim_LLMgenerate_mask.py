'''
3.16 条件掩码的大模型辅助生成-覆盖条件敏感性
有大模型依赖，无其他依赖

版本迭代情况：
[脱敏] 版本迭代记录
[脱敏] 版本迭代记录
[脱敏] 版本迭代记录
[脱敏] 版本迭代记录
[脱敏] 版本迭代记录

库依赖情况：
openai==1.93.0
schema==0.7.7
本组件存在大模型依赖：需要调用3.22的大模型调用组件

配置变量使用情况：
CONSTRAINT_SCHEMA：约束的schema
LLM_PROMPT：大模型的提示词
API_KEY：大模型调用的api-key
'''

import json
from time import time
import random

import jsonschema
from jsonschema import validate
from config import config_choice
from src.call_LLM import call_LLM
from src.make_json import make_JSON


class LimLLMGenerateMask:
    '''
    条件掩码的大模型辅助生成-覆盖条件敏感性

    先将所选掩码替换为一个占位用的标记[MASK]（只替换第一个匹配位置），
    将被掩码的句子和掩码一起发给LLM。
    只对随机选的一个掩码调用LLM，避免对每个掩码都调用。
    要求LLM返回完整的一条陈述，以"陈述："开头。

    属性：
        cond_validation_schema：用于校验schema
        api_key：大模型调用的api_key
        llm_prompt：大模型提示词
        log_manager：日志管理
        knowid：知识唯一标识，一个字符串
    '''
    def __init__(self, log_manager):
        cond_validation_string = config_choice.CONSTRAINT_SCHEMA
        self.cond_validation_schema = json.loads(cond_validation_string)
        self.api_key = config_choice.API_KEY
        self.llm_prompt = config_choice.LLM_PROMPT
        self.log_manager = log_manager

        self.knowid = ""

    def generate_choice(self, knowid, knowstr, knowcata, inference):
        ''' 
        算法的核心部分，通过这里完成选项的生成任务。

        参数：
            knowid：知识唯一标识，一个字符串
            knowstr：知识内容，一个字符串
            knowcata：知识目录标识，一个字符串
            inference：推理规则，一个JSON

        返回值：
            generate_result，一个列表，列表中的每个元素为一个满足选项schema的JSON

        异常处理：
            提示(notice)情况:
                1.知识推理列表为空，或者知识不存在推理列表
            错误(error)情况:
                1.远程调用大模型时，尝试数次仍不能返回有效结果
            崩溃(corrupt)情况:
                1.jsonschema验证抛出jsonschema.exceptions.SchemaError异常

        运行日志记录：
            成功生成选项时，将生成选项信息写入运行日志
        '''
        # 存储生成选项结果，初始列表为空
        self.knowid = knowid
        generate_result = []

        if len(inference) == 0:
            self.log_manager.generate_error_log(time(),knowid,"lim_LLMgenerate_mask","notice",9,"推理列表为空")
            return generate_result # 如果推理列表为空，直接结束。

        # 推理前件
        antecedent_constraint = inference['antecedent']['cond']
        # 推理后件
        consequence_constraint = inference['consequence']['cond']

        whether_validate = 0 # 验证失败的标志

        try:  # 验证推理前件
            validate(schema=self.cond_validation_schema, instance=antecedent_constraint)
        except jsonschema.exceptions.SchemaError as e:
            # 不符合约束schema：corrupt
            self.log_manager.generate_error_log(time(), knowid, "lim_LLMgenerate_mask", "corrupt", 1, str(e))
            whether_validate = 1
        except jsonschema.exceptions.ValidationError as e:
            # jsonschema.exceptions.ValidationError异常：notice
            self.log_manager.generate_error_log(time(), knowid, "lim_LLMgenerate_mask", "notice", 9, str(e))
            whether_validate = 1

        try:  # 验证推理后件
            validate(schema=self.cond_validation_schema, instance=consequence_constraint)
        except jsonschema.exceptions.SchemaError as e:
            # 不符合约束schema：corrupt
            self.log_manager.generate_error_log(time(), knowid, "lim_LLMgenerate_mask", "corrupt", 1, str(e))
            whether_validate = 1
        except jsonschema.exceptions.ValidationError as e:
            # jsonschema.exceptions.ValidationError异常：notice
            self.log_manager.generate_error_log(time(), knowid, "lim_LLMgenerate_mask", "notice", 9, str(e))
            whether_validate = 1

        if whether_validate != 0: # 此时约束不满足条件，返回空列表。
            return generate_result

        # 收集全部掩码（包括index/unit/entity），但后续只随机选一个进行掩码与LLM调用
        cond_list = self._collect_masks(antecedent_constraint, consequence_constraint)

        # 随机选一个掩码项；测试发现存在问题，已更改为大于0时才进行处理，否则不处理
        if len(cond_list) > 0:
            chosen_mask = random.choice(cond_list)
        else:
            return generate_result

        # 构造被掩码的句子
        masked_sentence = self._build_masked_sentence(knowstr, chosen_mask)

        # 构造prompt
        prompt = self._build_prompt(masked_sentence, chosen_mask, self.llm_prompt)

        try:
            # 调用LLM
            llm_answer = self._LLM_generate(prompt)
        # 调用大模型的时候发生了错误或者出现了异常，直接返回空集合
        except Exception as e:
            self.log_manager.generate_error_log(time(), self.knowid, "lim_LLMgenerate_mask", "error", 1, "调用大模型尝试数次仍不能返回有效结果，返回空串")
            return generate_result

        # 生成选项JSON
        generate_result.append(make_JSON(knowid, llm_answer, False, 4, knowcata))

        # 如果运行到最后没有问题，就写入run_log
        self.log_manager.generate_run_log(time(), knowid, "lim_LLMgenerate_mask", len(generate_result))

        return generate_result

    def _collect_masks(self, antecedent_constraint, consequence_constraint):
        """
        从前件和后件约束中收集可掩码的项。

        参数：
            antecedent_constraint: 推理前件约束
            consequence_constraint: 推理后件约束

        返回值：
            cond_list: 候选掩码列表
        """
        cond_list=[]

        # 前件数值约束收集掩码
        if "compare" in antecedent_constraint["constraint"]:
            # index和unit都可以作为掩码
            cond_list.append(antecedent_constraint["constraint"]["index"])
            cond_list.append(antecedent_constraint["constraint"]["unit"])
        else:
            # 存在约束收集掩码
            for entity in antecedent_constraint["constraint"]["entity"]:
                cond_list.append(entity)

        # 后件数值约束收集掩码
        if "compare" in consequence_constraint["constraint"]:
            cond_list.append(consequence_constraint["constraint"]["index"])
            cond_list.append(consequence_constraint["constraint"]["unit"])
        else:
            # 存在约束收集掩码
            for entity in consequence_constraint["constraint"]["entity"]:
                cond_list.append(entity)
        
        return cond_list

    def _build_masked_sentence(self, knowstr, chosen_mask):
        """
        将knowstr中第一个出现的掩码项替换为占位标记[MASK]，并返回新的字符串。
        
        参数：
            knowstr: 知识内容
            chosen_mask: 待掩码的项

        返回值：
            masked_sentence: 替换后的句子
        """
        # 将掩码转为字符串
        chosen_mask = str(chosen_mask)

        # 找到第一个出现的掩码项
        pos = knowstr.find(chosen_mask)
        # 前半+[MASK]+后半
        masked_sentence = knowstr[:pos] + "[MASK]" + knowstr[pos + len(chosen_mask):]
        return masked_sentence
    
    def _build_prompt(self, masked_sentence, chosen_mask, base_prompt):
        """
        构造发送给LLM的prompt（被掩码的句子+掩码原词+输出要求）。
        要求LLM返回完整句子，以“陈述：”开头，独立一行。

        参数：
            masked_sentence: 被掩码的句子
            chosen_mask: 被掩码的项
            base_prompt: 提示词（要求）

        返回值：
            prompt: 构造好的prompt
        """
        chosen_mask = str(chosen_mask)
        # prompt：被掩码句子+被掩码原始词+要求
        prompt = masked_sentence + "\n" + chosen_mask + "\n" + base_prompt
        return prompt

    def _LLM_generate(self, llm_prompt):
        '''
        参数: 
            llm_prompt: 提示词
        
        返回值: 
            处理过后的llm_answer
        '''
        LLM_answer = ""
        # 调用大模型接口
        LLM_answer = call_LLM(llm_prompt)

        # 处理大模型返回的结果
        text = LLM_answer.strip()
        # 找“陈述：”前缀
        prefix = "陈述："
        pos = text.find(prefix)
        if pos != -1:
            parsed = text[pos + len(prefix):].strip()
            # 只取第一行
            parsed_line = parsed.splitlines()[0].strip()
            if parsed_line:
                # 返回完整句子
                return parsed_line

        # 如果都返回不了有效结果，返回空串
        return ""
