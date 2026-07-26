'''
3.31 数值约束的语义极端性检查——覆盖意图语义准确性

版本迭代情况：
[脱敏] 版本迭代记录

库依赖情况：
jsonschema==4.21.0

本组件存在大模型依赖(使用组件3.23实现)。
内部依赖：调用3.21,3.23接口


配置变量使用情况:
API_KEY:调用deepseek的密钥
SEMANTIC_IRRATIONALITY_PROMPT:大模型提示词
CONSTRAINT_SCHEMA:推理前件 推理后件的schema

'''

import json
import jsonschema
import copy
from time import time
from jsonschema import validate
import config.config_choice as cfg_choice
from src.make_json import make_JSON
from src.call_LLM import call_LLM

class AttSemanticIrrationality:
    '''利用大模型对数值约束的语义进行更小范围的不合理替换，得到内容为假的选项内容。

    属性：
    semantic_irrationality_prompt: 大模型提示词
    schema: 从配置文件中加载的JSON schema，用于验证推理结构。
    log_manager: 日志管理类
    '''
    def __init__(self, log_manager):
        '''
        类初始化函数

        参数：
            log_manager: 日志管理类

        返回值：
            无

        异常处理：
            无
        '''
        self.semantic_irrationality_prompt = cfg_choice.SEMANTIC_IRRATIONALITY_PROMPT
        self.schema = json.loads(cfg_choice.CONSTRAINT_SCHEMA)
        self.log_manager = log_manager

    def validate_inference(self, inference, knowid):
        '''
        验证推理规则是否符合schema，且不为空
        参数：
            inference：推理规则
        返回值：
            validate_index：是否验证通过(True表示验证通过，False表示验证不通过)
        异常处理：
            notice:
                1.知识推理列表为空，或者知识不存在推理列表
                2.jsonschema.exceptions.ValidationError异常
            corrupt:
                1.jsonschema.exceptions.SchemaError异常
        '''
        #用于表示验证是否通过的布尔值
        validate_right = True
        validate_wrong = False
        #验证inference是否合法，前件后件是否存在（notice）
        if not inference or not isinstance(inference, dict):
            self.log_manager.generate_error_log(time(), knowid, "att_semantic_irrationality", "notice", 9, "推理内容为空或格式错误")
            return validate_wrong

        if "antecedent" not in inference or "consequence" not in inference:
            self.log_manager.generate_error_log(time(), knowid, "att_semantic_irrationality", "notice", 9, "推理内容缺少前件或后件")
            return validate_wrong
                
        # 验证推理前件（corrupt和notice）
        try:
            validate(instance=inference["antecedent"]["cond"], schema=self.schema)
        except jsonschema.exceptions.SchemaError as e:
            # jsonschema.exceptions.SchemaError异常，属于corrupt情况
            self.log_manager.generate_error_log(time(), knowid, "att_semantic_irrationality", "corrupt", 1, str(e))
            return validate_wrong
        except jsonschema.exceptions.ValidationError as e:
            # jsonschema.exceptions.ValidationError异常，属于notice情况
            self.log_manager.generate_error_log(time(), knowid, "att_semantic_irrationality", "notice", 9, str(e))
            return validate_wrong

        # 验证推理后件（corrupt和notice）
        try:
            validate(instance=inference["consequence"]["cond"], schema=self.schema)
        except jsonschema.exceptions.SchemaError as e:
            # jsonschema.exceptions.SchemaError异常，属于corrupt情况
            self.log_manager.generate_error_log(time(), knowid, "att_semantic_irrationality", "corrupt", 1, str(e))
            return validate_wrong
        except jsonschema.exceptions.ValidationError as e:
            # jsonschema.exceptions.ValidationError异常，属于notice情况
            self.log_manager.generate_error_log(time(), knowid, "att_semantic_irrationality", "notice", 9, str(e))
            return validate_wrong

        return validate_right


    def _LLM_generate(self, knowid, knowstr, constraint):
        '''
        利用大模型进行选项生成
        参数：
            knowid：知识唯一标识
            knowstr：知识内容
            constraint：约束
        返回值：
            string_match_list，一个字符串组成的列表，列表中的每个字符串表示一个LLM生成的陈述
        异常处理：
            error:
                1.大模型调用失败
        '''
        cons_value = constraint["index"]
        #深拷贝比较关系，避免转换为中文过程中修改原值
        cons_compare = copy.deepcopy(constraint["compare"])
        cons_unit = constraint["unit"]
        #将比较关系转换为中文
        compare_map = {
            "large": "大于", "equal": "等于", "below": "小于",
            "largeequal": "大于等于", "notequal": "不等于", "belowequal": "小于等于"
        }
        cons_compare = compare_map.get(cons_compare, cons_compare)  # 使用get方法，如果键不存在则返回原值
        #进行大模型调用
        LLM_prompt = "已知如下知识（该知识是正确的）：" + "\n" + knowstr
        LLM_prompt = LLM_prompt + "\n" + "原句包含了一个数值约束，其中数值为“" + str(cons_value) + "”，比较关系是“" + str(cons_compare) + "”，单位是“" + str(cons_unit) + "”。"
        LLM_prompt = LLM_prompt + '\n' + self.semantic_irrationality_prompt
        try:
            LLM_output_string = call_LLM(LLM_prompt)
        except Exception as e:
            self.log_manager.generate_error_log(time(), knowid, "att_semantic_irrationality", "error", 1, str(e))
            return []

        # 处理不同操作系统的换行符，统一转换为\n
        LLM_output_string = LLM_output_string.replace('\r\n', '\n').replace('\r', '\n')
        
        # 按行分割字符串
        output_list = LLM_output_string.split("\n")

        string_match_list = [] # 函数返回的列表
        for output in output_list:
            # 去除每行首尾的空白字符
            output = output.strip()
            ''' 
            对LLM返回的字符串按行遍历，匹配"陈述:"。
            如果匹配到，从匹配到的位置（即"陈"这个字的位置）后面3个位置，直到本行末尾，就是生成的陈述。
            '''
            if len(output) < 4: # 如果output长度小于4，进行匹配没有意义。
                continue
            match_pos = output.find("陈述：")
            if match_pos != -1 and match_pos == 0:
                string_match_list.append(output[match_pos + 3:])
        # 全部处理完成，返回列表。        
        return string_match_list


    def generate_choice(self, knowid,knowstr, knowcata, inference):
        '''
        选项生成函数
        
        参数：
            knowid：知识唯一标识
            knowcata：知识目录标识
            inference：推理规则

        返回值：
            generate_result：一个列表，列表中的每个元素为一个满足选项schema的JSON
        
        异常处理：
            notice：
                1.知识列表没有数值约束
        运行日志记录：
            成功生成选项时，将生成选项信息写入运行日志
        '''
        generate_result = []
        #验证推理规则是否符合schema，且不为空
        if not self.validate_inference(inference, knowid):
            return generate_result
        
        #验证推理前件和后件是否存在数值约束
        has_antecedent_constraint = "compare" in inference["antecedent"]["cond"]["constraint"]
        has_consequence_constraint = "compare" in inference["consequence"]["cond"]["constraint"]
        # 知识推理列表没有数值约束，属于notice情况
        if not has_antecedent_constraint and not has_consequence_constraint:
            self.log_manager.generate_error_log(time(), knowid, "att_semantic_irrationality", "notice", 11, "知识推理列表没有数值约束。")
            return generate_result

        #利用大模型进行选项生成
        LLM_return_list = []
        #对前件数值约束进行大模型生成
        if has_antecedent_constraint:
            LLM_return_list.extend(self._LLM_generate(knowid, knowstr, inference["antecedent"]["cond"]["constraint"]))

        #对后件数值约束进行大模型生成
        if has_consequence_constraint:
            LLM_return_list.extend(self._LLM_generate(knowid, knowstr, inference["consequence"]["cond"]["constraint"]))

        # 如果没有生成任何结果，直接返回
        if len(LLM_return_list) == 0:
            return generate_result
        # 将LLM生成的结果转换为JSON格式
        for i in range(len(LLM_return_list)):
            if len(LLM_return_list[i]) == 0:
                continue
            generate_result.append(make_JSON(knowid + "31" + str(i).zfill(2), LLM_return_list[i], False, 13, knowcata))
        self.log_manager.generate_run_log(time(), knowid, "att_semantic_irrationality", len(generate_result))
        return generate_result














