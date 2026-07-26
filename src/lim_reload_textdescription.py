'''
3.13 文字描述的条件更改-覆盖条件敏感性

版本迭代情况：
[脱敏] 版本迭代记录
[脱敏] 版本迭代记录
[脱敏] 版本迭代记录

库依赖情况：
jsonschema==4.24.0

本组件存在大模型依赖。
外部依赖：无
内部依赖：3.22 大模型调用组件
文档依赖：无

配置变量使用情况：
API_KEY：大模型调用的API Key
REFINE_PROMPT_REVERSE：前件取反的提示词
CONSTRAINT_SCHEMA：对推理内容约束的JSON Schema字符串
'''
import sys
import os
base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(os.path.join(base_dir, 'src'))

import json
import time
import copy
from jsonschema import validate, ValidationError, SchemaError
from config import config_choice
from log_manager import LogManager
from make_json import make_JSON
from src.call_LLM import call_LLM

class LimReloadTextDescription:
    """ 
    基于文字描述的条件更改，覆盖条件敏感性指标
    
    本组件通过两种方式修改知识内容中的条件约束：
    1.直接删除推理前件
    2.对推理前件取反
    其中第二种方式会调用大模型进行表达优化
    
    属性：
        log_manager：日志管理对象，用于记录运行日志和错误日志
        component_id：组件标识符，取值为类名
        api_key：大模型调用的API Key
        refine_prompt_reverse：前件取反的提示词
        cond_validation_schema：约束schema，用于验证推理规则
    """

    def __init__(self, log_manager):
        """ 
        初始化组件
        
        从config文件中获取api_key和提示词
        由于这里涉及两种方式，一种是删除推理前件，一种是对前件取反，推理前件删除不需要大模型润色
        
        参数：
            log_manager: LogManager对象，用于记录日志
        
        异常处理：
            schema解析失败：corrupt
        """
        self.log_manager = log_manager
        self.api_key = config_choice.API_KEY

        # 前件取反的提示词
        self.refine_prompt_reverse = config_choice.REFINE_PROMPT_REVERSE

        # 对schema进行校验
        cond_validation_string = config_choice.CONSTRAINT_SCHEMA
        try:
            self.cond_validation_schema = json.loads(cond_validation_string)
        except Exception as e:
            # schema解析失败：corrupt
            self.log_manager.generate_error_log(time.time(), "UNKNOWN", "lim_reload_textdescription", "corrupt", 1, str(e))

    def generate_choice(self, knowid, knowstr, knowcata, inference):
        """
        算法的核心部分，生成条件更改后的选项内容
        
        参数：
            knowid：字符串，知识唯一标识
            knowcata：字符串，知识目录标识
            inference：字典，符合inference schema的JSON格式的推理规则
        
        返回值：
            generate_result：列表，包含满足选项schema的JSON对象
        
        异常处理：
            提示(notice)情况：
                1.知识推理列表为空，或知识不存在推理列表。
                2.知识推理列表的前件无存在约束。
            警告(warning)情况：
                1.远程调用大模型时，尝试数次仍不能返回有效结果。
            崩溃(corrupt)情况：
                1.jsonschema验证抛出jsonschema.exceptions.SchemaError异常。
        
        运行日志记录：
            成功生成选项时，将生成选项信息写入运行日志
        """
        # 存储生成选项结果，初始列表为空。
        generate_result = []

        # 检查推理列表
        if not inference or 'antecedent' not in inference or 'consequence' not in inference:
            # 推理列表为空/不存在：notice
            self.log_manager.generate_error_log(time.time(), knowid, "lim_reload_textdescription", "notice", 9, "inference empty or missing fields")
            self.log_manager.generate_run_log(time.time(), knowid, "lim_reload_textdescription", 0)
            return generate_result

        # 推理前件约束
        antecedent_constraint = inference['antecedent']['cond']
        # 推理后件约束
        consequence_constraint = inference['consequence']['cond']

        # schema验证
        try:
            # 验证推理前件
            validate(instance=antecedent_constraint, schema=self.cond_validation_schema)
            # 验证推理后件
            validate(instance=consequence_constraint, schema=self.cond_validation_schema)
        except ValidationError as ve:
            # 约束不满足：notice
            self.log_manager.generate_error_log(time.time(), knowid, "lim_reload_textdescription", "notice", 10, str(ve))
            self.log_manager.generate_run_log(time.time(), knowid, "lim_reload_textdescription", 0)
            return generate_result  # 约束不满足条件，返回空列表
        except SchemaError as se:
            # schema错误：corrupt
            self.log_manager.generate_error_log(time.time(), knowid, "lim_reload_textdescription", "corrupt", 1, str(se))
            return generate_result  # 返回空列表

        # 检查前件是否存在约束
        if "verb" not in antecedent_constraint["constraint"] and "entity" not in antecedent_constraint["constraint"]:
            # 前件无存在约束：notice
            self.log_manager.generate_error_log(time.time(), knowid, "lim_reload_textdescription", "notice", 10, "antecedent has no existence constraint")
            self.log_manager.generate_run_log(time.time(), knowid, "lim_reload_textdescription", 0)
            return generate_result

        # 对原推理前件取反
        adverse_front = copy.deepcopy(antecedent_constraint)
        if adverse_front["bool"] == True:
            adverse_front["bool"] = False
        else:
            adverse_front["bool"] = True

        # 删除前件
        delete_front_string = self._make_string_delete(consequence_constraint)
        # 前件取反
        adverse_string = self._make_string_reverse(adverse_front, consequence_constraint)

        # 使用大模型对否定词进行润色
        try:
            refined_string = self._LLM_refine(adverse_string, knowid)
        except Exception as e:
            # LLM尝试数次仍不能返回有效结果：warning
            self.log_manager.generate_error_log(time.time(), knowid, "lim_reload_textdescription", "warning", 1, str(e))
            refined_string = adverse_string  # 使用原始字符串

        # 生成删除前件选项
        generate_result.append(make_JSON(knowid + "1301", delete_front_string, False, 4, knowcata))
        # 生成前件取反选项
        generate_result.append(make_JSON(knowid + "1302", refined_string, False, 4, knowcata))

        # 运行日志
        self.log_manager.generate_run_log(time.time(), knowid, "lim_reload_textdescription", len(generate_result))

        # 返回结果
        return generate_result

    def _make_string_delete(self, back):
        """ 
        构造删除前件的字符串
        
        参数：
            back：推理后件的约束条件
        
        返回值：
            字符串，删除前件后的陈述内容
        """
        merge_string = ""
        # 对推理后件分情况讨论，有存在约束和数值约束
        if "verb" in back["constraint"] or "entity" in back["constraint"]:
            merge_string = self._existence_to_string(back)
        elif "compare" in back["constraint"]:
            merge_string = self._number_to_string(back)
        # 添加描述结尾词，返回结果
        merge_string =  merge_string + "。"
            
        return merge_string

    def _make_string_reverse(self, front, back):
        """ 
         构造前件取反的字符串
        
        参数：
            front：字典，取反后的推理前件约束
            back：字典，推理后件的约束条件
        
        返回值：
            字符串，前件取反后的条件陈述
        """
        # 构造前件
        if "verb" in front["constraint"] or "entity" in front["constraint"]:
            front_string = self._existence_to_string(front)
        elif "compare" in front["constraint"]:
            front_string = self._number_to_string(front)
        
        # 构造后件
        if "verb" in back["constraint"] or "entity" in back["constraint"]:
            back_string = self._existence_to_string(back)
        elif "compare" in back["constraint"]:
            back_string = self._number_to_string(back)
        
        return f"如果{front_string}，那么{back_string}。"

    def _number_to_string(self, cond):
        """ 
        将数值约束转换为自然语言字符串
        
        参数：
            cond：字典，数值约束条件
        
        返回值：
            字符串，自然语言描述的数值约束
        """
        merge_string = cond["entity"]
        if "bool" in cond and cond["bool"] == False:
            merge_string += "没有"
        
        cond_constraint = cond["constraint"]
        # 比较符
        compare_map = {
            "large": "大于",
            "equal": "等于",
            "below": "小于",
            "largeequal": "大于等于",
            "notequal": "不等于",
            "belowequal": "小于等于"
        }
        
        merge_string += compare_map[cond_constraint["compare"]]
        merge_string += str(cond_constraint["index"]) + cond_constraint["unit"]
        return merge_string

    def _existence_to_string(self, cond):
        """ 
        将存在约束转换为自然语言字符串
        
        参数：
            cond：字典，存在约束条件
        
        返回值：
            字符串，自然语言描述的存在约束
        """
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

    def _LLM_refine(self, source_string, knowid):
        """ 
        利用大语言模型润色字符串
        
        参数：
            source_string：字符串，需要润色的原始字符串
            knowid：字符串，知识唯一标识
        
        返回值：
            字符串，润色后的结果
        
        异常处理：
            警告(warning)情况：
                1.大模型调用失败
        """
        # 下面的return仅用于测试
        # return source_string

        try:
            # 构建提示词
            give_prompt = f"“{source_string}”\n{self.refine_prompt_reverse}"
            
            # 调用大模型组件
            LLM_answer = call_LLM(give_prompt)
            
            # 处理大模型返回结果
            if LLM_answer:
                # 提取"陈述："后面的内容
                pos_start = LLM_answer.find("陈述：")
                if pos_start != -1:
                    LLM_answer = LLM_answer[pos_start + 3:]
                
                # 去除可能的换行符
                LLM_answer = LLM_answer.strip()
                
                # 如果以句号结尾，保留句号；否则添加句号
                if not LLM_answer.endswith('。'):
                    LLM_answer += '。'
                
                return LLM_answer
            # 如果大模型没有返回有效结果，直接返回原始字符串，仍然根据初始陈述进行选项组织
            return source_string
        
        except Exception as e:
            self.log_manager.generate_error_log(time.time(), knowid, "lim_reload_textdescription", "warning", 1, str(e))
            # 大模型调用失败，返回原始字符串
            return source_string 
