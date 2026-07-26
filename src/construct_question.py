'''
题目3.2 结构化题目组织与输出

版本迭代情况：
[脱敏] 版本迭代记录
[脱敏] 版本迭代记录

库依赖情况：
jsonschema==4.24.0
numpy==1.26.4
pandas==2.3.0

本组件没有内部依赖和外部依赖。

配置变量使用情况：
QUESTION_OUTPUT：题目输出文件的路径

本模块需要从外部文件中读入JSON并进行管理。
此外，本模块需要目录文档，对文档中的每个目录各创建一个正确选项队列、一个错误选项队列，并设计维护。
所有的JSON目前假定从一个.txt文件读入，每个JSON单独一行；为便于扩展移植，该逻辑单独一个函数。
'''

import jsonschema
from jsonschema import validate
from openai import OpenAI
import json
import time
import copy
import config.config_choice
import random
from queue import Queue
import numpy as np
import pandas as pd

from config.config_choice import QUESTION_OUTPUT

class ConstructQuestion:
    '''
    因为涉及到文件的读写，该类有文件指针变量，故改用类进行实现。

    全局变量：
        question_ptr：文件路径字符串。
        answer_letter_list：答案选项序号。
    '''
    def __init__(self, log_manager):
        ''' 初始化函数。为了避免文件缓冲区的问题，变量从文件指针改成文件名称，写入时临时打开。

        '''
        self.question_ptr = QUESTION_OUTPUT
        self.log_manager = log_manager
        # 文件初始化，清空一次
        temp_ptr = open(QUESTION_OUTPUT, "w+", encoding = "UTF-8")
        temp_ptr.close()
        self.answer_letter_list = ["A", "B", "C", "D", "E", "F", "G", "H", "I", "J", "K", "L", "M", "N", "O"]

    def calculate_cataid(self, cataid_list):
        ''' 计算公共最长前缀，从初始开始。

        函数参数
            cataid_list，一个字符串列表。
        
        返回值
            cataid_result，一个字符串。
        '''

        if len(cataid_list) == 0: # 列表没有元素，返回空字符串。
            return ""
        # 公共最长前缀取第一个元素的全部。
        cataid_result = cataid_list[0]
        for i in range(1, len(cataid_list)):
            same_pos = 0 # 记录公共前缀位置
            min_len = len(cataid_result)
            if min_len > len(cataid_list[i]): # 以两个字符串的较短者进行遍历，避免数组越界
                min_len = len(cataid_list[i])
            for j in range(0, min_len):
                if cataid_result[j] != cataid_list[i][j]: # 如果碰到不同，直接结束比较。
                    break
                else:
                    same_pos = same_pos + 1
            cataid_result = cataid_result[0: same_pos]
        return cataid_result
    
    def _write_to_file(self, id, text, choice, answer, questype, cataid):
        ''' 将题目以JSON格式写入文件中。

        函数参数：
            id：题目唯一标识。
            text：题目描述，“以下关于” + catalog + “的说法，” + “正确/错误” + “的是：”
            choice：直接把choice_list转成array的形式。
            answer：按照ABCD的顺序给答案。
            questype：就是question_type。
            cataid：取所有choice的cataid的最长公共前缀，从头开始。
        
        返回值：
            整数，表示函数是否正常运行，0表示成功返回。

        运行日志：
            每道题输出一条日志。
        '''

        questype_dict = {}
        questype_dict["id"] = id
        questype_dict["text"] = text
        questype_dict["choice"] = choice
        questype_dict["answer"] = answer
        questype_dict["questype"] = questype
        questype_dict["cataid"] = cataid
        JSON_string_choice = json.dumps(questype_dict, ensure_ascii=False, separators=(',', ':'))
        with open(self.question_ptr, "a+", encoding = "UTF-8") as f:
            f.write(JSON_string_choice + "\n")
        self.log_manager.generate_run_log(time.time(), id, "construct_question", "1")
        return 0
    
    def construct_question(self, question_type, choice_list, catalog):
        ''' 类主函数，用以将选项组织成题目。

        函数参数：
            question_type，一个整数，表示题目类型。
            choice_list，一个选项列表，按照顺序表示每个选项。
            catalog，表示目录字符串，用以构建题目。

        向文件输出的JSON格式：
            id：题目唯一标识。
            text：题目描述，“以下关于” + catalog + “的说法，” + “正确/错误” + “的是：”
            choice：直接把choice_list转成array的形式。
            answer：按照ABCD的顺序给答案。
            questype：就是question_type。
            cataid：取所有choice的cataid的最长公共前缀，从头开始。
        
        返回值：
            整数，表示函数是否正常运行，0表示成功返回。
        '''

        # 该题到底是算正确的选项还是算错误的选项？
        whether_false = 0 # 默认该题正确的选项为答案
        choice_number = 0
        true_choice_number = 0
        for choice in choice_list:
            choice_number = choice_number + 1
            if choice["value"] == True:
                true_choice_number = true_choice_number + 1
        # 只有两种情况，按照错误的选项算答案：
        # 1. choice_number比true_choice_number多1，而且question_type为1.
        # 2. true_choice_number为0.
        if true_choice_number == 0:
            whether_false = 1
        elif true_choice_number + 1 == choice_number and question_type == 1:
            whether_false = 1
        
        # 计算知识目录，也就是cataid字段，公共最长子串。
        choice_cataid_list = []
        for choice in choice_list:
            choice_cataid_list.append(choice["cataid"])
        question_cataid = self.calculate_cataid(choice_cataid_list)

        # 得到正确答案字符串。
        answer_string = ""
        for i in range(0, len(choice_list)):
            if whether_false == 0 and choice_list[i]["value"] == True:
                answer_string = answer_string + self.answer_letter_list[i]
            elif whether_false == 1 and choice_list[i]["value"] == False:
                answer_string = answer_string + self.answer_letter_list[i]
        
        # 得到选项JSON格式。
        choice_json_str = "["
        for i in range(0, len(choice_list)):
            choice_json_str = choice_json_str + json.dumps(choice_list[i], ensure_ascii=False, separators=(',', ':'))
            if i < len(choice_list) - 1:
                choice_json_str = choice_json_str + ","
            else:
                choice_json_str = choice_json_str + "]"
        choice_json = json.loads(choice_json_str)

        # 得到题目描述。
        text_string = "以下关于" + catalog + "的说法，"
        if whether_false == 1:
            text_string = text_string + "错误"
        else:
            text_string = text_string + "正确"
        text_string = text_string + "的是："

        # 得到题目唯一标识。
        question_id = ""
        for i in range(0, len(choice_list)):
            question_id = question_id + choice_list[i]["id"]
            if i < len(choice_list) - 1:
                question_id = question_id + "_"
        
        # 调用写入函数。
        whether_success = self._write_to_file(question_id, text_string, choice_json, answer_string, question_type, question_cataid)
        return whether_success
