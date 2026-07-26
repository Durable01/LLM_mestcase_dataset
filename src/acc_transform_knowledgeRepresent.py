'''
3.6 知识表达方式转换-覆盖知识准确性

版本迭代情况:
[脱敏] 版本迭代记录
[脱敏] 版本迭代记录
[脱敏] 版本迭代记录
[脱敏] 版本迭代记录

库依赖情况:
openai==1.93.0

本组件存在大模型依赖(使用组件3.23实现)
本组件存在内部依赖：3.21组件make_json,3.23组件log_manager

配置变量使用情况:
API_KEY:调用deepseek的密钥
TRANSFORM_PROMPT:大模型提示词
'''

from time import time
import config.config_choice
from src.call_LLM import call_LLM
from src.make_json import make_JSON


class AccTransformKnowledgeRepresent:
    '''
    知识表述方式转换-覆盖知识准确性

    api-key:调用大模型密钥
    log_manager；日志管理
    '''

    def __init__(self,log_manager):
        self.api_key = config.config_choice.API_KEY # deepseek的调用密钥
        self.log_manager = log_manager

    def _LLM_generate(self, string):
        ''' 当前要求下，大语言模型的生成内容中可能有不止一条陈述，因此本函数需要返回列表。

        利用LLM进行句式转换陈述生成，需要在知识string后添加prompt指令，提供给大模型；
        返回值中每行以"陈述："开头，每行独立一条，因此可以用换行符\n，split整个返回字符串，每条逐个匹配。
        调用LLM的api仍然需要异常处理的逻辑，这一部分单独作为另一个函数。

        函数参数：
            string：被处理的初始信息，在输入提示信息的前半部分。
        返回值：
            string_match_list，一个字符串组成的列表，列表中的每个字符串表示一个LLM生成的陈述。
        '''
        prompt=config.config_choice.TRANSFORM_PROMPT
        LLM_output_string=""
        LLM_input_string = "“" + string + "”\n" + prompt
        try:
            #大模型发生错误
            LLM_output_string =call_LLM(LLM_input_string)
        except Exception as e:
            self.log_manager.generate_error_log(time(), self.knowid, "acc_transform_knowledgeRepresent", "error", 1, str(e))
            return []

        # 检查LLM返回值是否为空
        if not LLM_output_string:
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
            if match_pos != -1:
                string_match_list.append(output[match_pos + 3:])
        # 全部处理完成，返回列表。        
        return string_match_list

    def generate_choice(self, knowid, knowstr, knowcata):
        ''' 算法的核心部分，通过这里完成选项的生成任务。
        基本功能：
            基于给定的knowid、knowstr、knowcata，通过调用大模型改变句式，以此改变知识内容的表述方式，得到选项陈述
        函数参数：
            knowid：知识唯一标识，一个字符串。
            knowstr：知识内容，一个字符串。
            knowcata：知识目录标识，一个字符串。

        返回值：
            generate_result，一个列表，列表中的每个元素为一个满足选项schema的JSON。
        
        异常处理：
            error：远程调用大模型时，尝试数次仍不能返回有效结果

        运行日志记录：
            成功生成选项时，将生成选项时间、知识唯一标识、类名称（组件标识）、选项生成个数写入运行日志
        '''

        # 存储生成选项结果，初始列表为空。
        self.knowid = knowid
        generate_result = []
        
        '''
        应用大模型进行选项生成，结果存在LLM_result_list里。
        '''        
        
        LLM_return_list = self._LLM_generate(knowstr)

        if len(LLM_return_list) == 0:
            return generate_result
        '''
        将相关指标组合为JSON。
        '''
        for i in range(0, len(LLM_return_list)):
            generate_result.append(make_JSON(knowid + "06" + str(i).zfill(2), LLM_return_list[i], True, 1, knowcata))

            # 运行到最后没有问题，输出到运行日志
        self.log_manager.generate_run_log(time(), knowid, "acc_transform_knowledgeRepresent", len(generate_result))
        return generate_result
