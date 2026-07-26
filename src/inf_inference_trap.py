"""
3.19 逻辑推理陷阱的陈述内容生成-覆盖推理可靠性

版本迭代情况：
[脱敏] 版本迭代记录
[脱敏] 版本迭代记录
[脱敏] 版本迭代记录

库依赖情况：
jsonschema==4.24.0

本组件存在文档依赖和内部依赖。
大模型依赖：推理陷阱模式的生成
内部依赖：调用3.21,3.22,3.23接口

配置变量使用情况：
CONSTRAINT_SCHEMA:推理前件 推理后件的schema
API_KEY：大模型调用密钥
TRAP_REVERSE_PROMPT：生成倒果为因选项的prompt
TRAP_BLACK_WHITE_PROMPT：生成非此即彼选项的prompt
TRAP_RECYCLE_PROMPT：生成循环论证选项的prompt
"""


import json
import jsonschema
import config.config_choice
from time import time
from jsonschema import validate
from src.make_json import make_JSON
from src.call_LLM import call_LLM

class InfInferenceTrap:
    """逻辑推理陷阱的陈述内容生成-覆盖推理可靠性

    属性：
        log_manager:日志管理类
        schema:从配置文件中加载的JSON schema，用于验证推理结构
        api_key:大模型密钥
        trap_prompt_list:prompt列表
    """

    def __init__(self, log_manager):
        """ 类初始化函数

        参数：
            log_manager:日志管理类

        返回值：
            无
        """
        self.log_manager = log_manager
        self.schema = json.loads(config.config_choice.CONSTRAINT_SCHEMA)
        self.api_key = config.config_choice.API_KEY # deepseek的调用密钥
        """
        根据不同类别的推理陷阱类型，分别设计prompt。
        需要注意的是，后续为了便于实现，prompt采用列表的形式，对列表中的每个元素做完全相同的处理。
        但在初始化过程中，元素需要从配置文件中逐个手动添加到列表中，以便于在本代码中查看能够支持的推理陷阱类型。
        """
        self.trap_prompt_list = []
        self.trap_prompt_list.append(config.config_choice.TRAP_REVERSE_PROMPT) # 倒果为因
        self.trap_prompt_list.append(config.config_choice.TRAP_BLACK_WHITE_PROMPT) # 非此即彼
        self.trap_prompt_list.append(config.config_choice.TRAP_RECYCLE_PROMPT) # 循环论证
    
    def _LLM_generate(self, prompt, string):
        """ 由于这一次，大语言模型的生成内容中可能有不止一条陈述，因此本函数需要返回列表。

        利用LLM进行推理陷阱生成，需要在知识string后添加prompt指令，提供给大模型；
        返回值中每行以“陈述：”开头，每行独立一条，因此可以用换行符\n，split整个返回字符串，每条逐个匹配。
        调用LLM的api仍然需要异常处理的逻辑，这一部分单独作为另一个函数。

        参数：
            prompt：引导LLM进行生成的引导语言，在输入提示信息中的后半部分。
            string：被处理的初始信息，在输入提示信息的前半部分。
        
        返回值：
            string_match_list，一个字符串组成的列表，列表中的每个字符串表示一个LLM生成的陈述。
        """

        LLM_input_string = "“" + string + "”\n" + prompt
        LLM_output_string = call_LLM(LLM_input_string)

        # 以换行符分开整个字符串，得到每个行的字符串列表
        output_list = LLM_output_string.split("\n")
        # 函数返回的列表
        string_match_list = []
        for output in output_list:
            """
            对LLM返回的字符串按行遍历，匹配“陈述:”。
            如果匹配到，从匹配到的位置（即“陈”这个字的位置）后面3个位置，直到本行末尾，就是生成的陈述。
            """
            # 如果output长度小于4，进行匹配没有意义。
            if len(output) < 4:
                continue
            match_pos = output.find("陈述：")
            if match_pos != -1:
                string_match_list.append(output[match_pos + 3:])
        # 全部处理完成，返回列表。        
        return string_match_list

    def generate_choice(self, knowid, knowstr, knowcata, inference):
        """ 实现选项生成任务的主函数，返回值为JSON对象的列表。

        参数：
            knowid: 知识的唯一标识，字符串形式。
            knowstr：知识内容，以字符串形式表示。
            knowcata: 知识所在目录的唯一标识，字符串形式。
            inference：知识对应的推理关系。需要说明的是，本方法不需要对inference进行变换，只需要验证它是否有实际元素即可。

        返回值：
            generate_result，一个列表，列表中的每个元素为一个满足选项schema的JSON。

        异常处理：
            抛出jsonschema.exceptions.ValidationError异常，属于notice
            推理列表为空，属于notice
            远程调用大模型时，尝试数次仍不能返回有效结果，属于warning
            抛出jsonschema.exceptions.SchemaError异常，属于corrupt

        运行日志记录：
            成功生成选项时，将生成选项信息写入运行日志。
        """

        # 存储生成选项结果，初始列表为空。
        generate_result = []
        validate_failed = False

        # 判断推理列表是否为空。本算法不对inference进行JSON层次的修改，只要inference存在，那么就可以继续进行。
        if len(inference) == 0:
            # 推理列表为空，属于notice情况
            self.log_manager.generate_error_log(time(), knowid, "inf_inference_trap", "notice", 9, "知识推理列表为空。")
            return generate_result

        # 验证推理前件
        try:
            validate(instance=inference["antecedent"]["cond"], schema=self.schema)
        except jsonschema.exceptions.SchemaError as e:
            # jsonschema.exceptions.SchemaError异常，属于corrupt情况
            self.log_manager.generate_error_log(time(), knowid, "inf_inference_trap", "corrupt", 1, str(e))
            validate_failed = True
        except jsonschema.exceptions.ValidationError as e:
            # jsonschema.exceptions.ValidationError异常，属于notice情况
            self.log_manager.generate_error_log(time(), knowid, "inf_inference_trap", "notice", 9, str(e))
            validate_failed = True

        if validate_failed:
            return generate_result

        # 验证推理后件
        try:
            validate(instance=inference["consequence"]["cond"], schema=self.schema)
        except jsonschema.exceptions.SchemaError as e:
            # jsonschema.exceptions.SchemaError异常，属于corrupt情况
            self.log_manager.generate_error_log(time(), knowid, "inf_inference_trap", "corrupt", 1, str(e))
            validate_failed = True
        except jsonschema.exceptions.ValidationError as e:
            # jsonschema.exceptions.ValidationError异常，属于notice情况
            self.log_manager.generate_error_log(time(), knowid, "inf_inference_trap", "notice", 9, str(e))
            validate_failed = True

        if validate_failed:
            return generate_result

        # 逐条应用大模型进行选项生成，结果存在string_result_list里。
        string_result_list = []
        for prompt in self.trap_prompt_list:
            # 对每个prompt，存储返回的所有生成列表，在LLM_return_list里。
            try:
                LLM_return_list = self._LLM_generate(prompt, knowstr)
            except Exception as e:
                # 远程调用大模型时，尝试数次仍不能返回有效结果，属于warning情况
                self.log_manager.generate_error_log(time(), knowid, "inf_inference_trap", "warning", 1, str(e))
                return generate_result
            for string in LLM_return_list:
                string_result_list.append(string)

        # 将相关指标组合为JSON。
        for i in range(0, len(string_result_list)):
            generate_result.append(make_JSON(knowid + "19" + str(i).zfill(2), string_result_list[i], False, 5, knowcata))

        # 成功生成选项时，将生成选项信息写入运行日志。
        self.log_manager.generate_run_log(time(), knowid, "inf_inference_trap", len(generate_result))
        return generate_result