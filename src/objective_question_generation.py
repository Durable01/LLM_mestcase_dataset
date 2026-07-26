'''
题目3.1 领域选项管理

版本迭代情况：
[脱敏] 版本迭代记录
[脱敏] 版本迭代记录

库依赖情况：
jsonschema==4.24.0
numpy==1.26.4
pandas==2.3.0

本组件没有外部依赖。
内部依赖：调用题目3.2 结构化题目组织与输出组件。

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
import copy
import config.config_choice
import random
from queue import Queue
import numpy as np
import pandas as pd
import time
from src.construct_question import ConstructQuestion
from src.log_manager import LogManager
from config.config_choice import CHOICE_JSON_FILENAME
from config.config_choice import CATALOG_FILENAME
from config.config_choice import CHOICE_SCHEMA
from config.config_choice import CHOICE_NUMBER
from config.config_choice import UNCERTAIN_MULTIPLE_RATIO

class ObjectiveQuestionGeneration:
    '''
    领域选项管理类。
    
    本类变量：
        true_queue_list: 存储正确选项队列的列表。
        false_queue_list: 存储错误选项队列的列表。两个列表按序一一对应。
        true_count_list: 统计正确选项队列的选项个数。本类以数量判定题目生成触发时机。
        false_count_list: 统计错误选项队列的选项个数。
        cata_table: 领域目录表（Domain catalog table)，numpy格式数组：
            第一列为领域目录字符串；
            第二列为目录唯一标识的起始位置；
            第三列为目录唯一标识的终点位置。
            起终位置均为字符串格式，直接比较字符串字典序即可判断；python可以直接比较字符串，即str1 > str2。
        choice_schema: 选项验证的内容。
        choice_fileptr: 一个json文件的指针。
        cons_question: ConstructQuestion类的实例。
    '''

    def __init__(self, log_manager):
        ''' 构造函数
        
        函数参数：
            log_manager：日志管理类

        构造函数没有返回值。
        
        异常处理：
            1. 目录文件读入失败，此时抛出异常，日志类型为崩溃
            2. 选项JSON文件读入失败，此时抛出异常，日志类型为崩溃
        
        构造函数没有运行日志。
        '''
        # 日志是最先开始构造的
        self.log_manager = log_manager
        # 四个列表初始化
        self.true_queue_list = []
        self.true_count_list = []
        self.false_queue_list = []
        self.false_count_list = []
        # 目录文件读入
        try:
            pd_cata = pd.read_csv(CATALOG_FILENAME, encoding = "UTF-8")
        except Exception as e: # 这一部分后续要做日志处理，类型为崩溃
            log_manager.generate_error_log(time.time(), "", "objective_question_generation", "corrupt", 4, str(e))
            raise e
        self.cata_table = np.array(pd_cata)
        # 对目录文件的每一行，都读一遍。
        for i in range(0, len(self.cata_table)):
            self.true_queue_list.append(Queue(maxsize = 200))
            self.true_count_list.append(0)
            self.false_queue_list.append(Queue(maxsize = 200))
            self.false_count_list.append(0)
        # 选项schema
        string_schema = CHOICE_SCHEMA
        self.choice_schema = json.loads(string_schema)
        # 准备好JSON文件指针
        try:
            self.choice_fileptr = open(CHOICE_JSON_FILENAME, "r", encoding = "UTF-8")
        except Exception as e: # 这一部分后续要做日志处理，类型为崩溃
            log_manager.generate_error_log(time.time(), "", "objective_question_generation", "corrupt", 4, str(e))
            raise e
        # 实例
        self.cons_question = ConstructQuestion(log_manager)
        
    
    def _read_one_choice(self):
        '''
        只读入一个JSON，返回一个JSON对象；该函数是为了后续可能改变JSON文件类型单独抽象出来的。
        
        本函数没有参数。

        返回值：
            JSON_choice，一个选项对应的JSON对象。
        '''

        choice_str = self.choice_fileptr.readline()
        if choice_str != "":
            right_position = choice_str.rfind("}") # 最后一个右大括号后面的内容可以全部剔除
            choice_str = choice_str[0: right_position + 1]
            JSON_choice = json.loads(choice_str)
            return JSON_choice
        else:
            return ""

    def _get_choice_number(self, ad):
        '''
        本题选项的个数；目前配置为4。
        
        函数参数：
            ad：当前要生成题目的队列编号。
        
        返回值：
            choice_number，本题选项的个数。
        '''
        choice_number = CHOICE_NUMBER
        return choice_number
    
    def _calculate_true_number(self, count, true_count, false_count):
        '''
        根据当前的情况，计算正确选项的数量。
        这一部分逻辑单独提出来，增强代码可维护性。

        函数参数：
            count: 选项个数。
            true_count: 当前队列剩余正确选项个数。
            false_count: 当前队列剩余错误选项个数。
        
        返回值：
            true_choice_num，代表正确选项的数量。
        '''
        true_choice_num = 0
        if true_count <= count / 2: # 在队列剩余至多一个正确选项的情况下，直接耗尽正确选项列表
            true_choice_num = true_count
        elif false_count <= count / 2: # 在队列剩余至多一个错误选项的情况下，直接耗尽错误选项列表
            true_choice_num = 4 - false_count
        else: # 如果情况不像上面两个那么极端，可以随机决定。
            ''' 整体思路如下：
            以0.6和0.4为界，将正确选项比率分为低、中、高三类，随机决定选项个数。
                    0-0.2       0.2-0.4     0.4-0.6     0.6-0.8     0.8-1
            低       1           1           1           1           0
            中       3           3           2           1           1
            高       4           4           3           3           1
            此时，三种情况的正确选项期望为0.8（比率0.2）、2（比率0.5）和3（比率0.75）。
            此种情况下，除非输入数值本身就特别极端，否则较为容易将选项比率收敛至中等水平，且能保证单选题的比例。
            '''
            true_ratio = true_count / (true_count + false_count)
            rand_result = random.random()
            if true_ratio < 0.4:
                if rand_result < 0.8:
                    true_choice_num = 1
                else:
                    true_choice_num = 0
            elif true_ratio < 0.6:
                if rand_result < 0.4:
                    true_choice_num = 3
                elif rand_result < 0.6:
                    true_choice_num = 2
                else:
                    true_choice_num = 1
            else:
                if rand_result < 0.4:
                    true_choice_num = 4
                elif rand_result < 0.8:
                    true_choice_num = 3
                else:
                    true_choice_num = 1
        return true_choice_num
        
    def _ready_generate_question(self, ad):
        '''
        根据当前两个列表的选项数量情况，组织题目的选项，并出队。
        如果成功生成（调用函数返回值为0），则题目成功生成，撰写日志；
        否则，报错错误信息。

        函数参数：
            ad，表示需要对哪个队列进行题目生成。

        本函数没有返回值。

        异常处理：
            1. 调用construct_question失败，异常类型为错误
        '''
        choice_num = self._get_choice_number(ad)
        # 循环条件是选项数量之和大于等于4。
        while self.true_count_list[ad] + self.false_count_list[ad] >= choice_num:
            true_count = self.true_count_list[ad]
            false_count = self.false_count_list[ad]
            # 首先确定这道题正确的选项有几个。
            true_choice_num = self._calculate_true_number(choice_num, true_count, false_count)

            # 确定题目类型，1为单选，2为多选，3为不定项。
            # true_choice_num为1是单选，其余为多选。
            # 以不定项比例确定选择题数量。
            question_type = 0
            rand_result = random.random()
            if rand_result < UNCERTAIN_MULTIPLE_RATIO:
                question_type = 3
            else:
                if true_choice_num == 1:
                    question_type = 1
                else:
                    question_type = 2
            
            # 下一步确定最终输入的选项列表，这里要打乱顺序。
            random_list = [] # 选项列表，以4个选项为例，[0，1，2，3]
            for i in range(0, choice_num): 
                random_list.append(i)
            random.shuffle(random_list) # 该函数打乱列表顺序
            
            # 准备选项列表，按序依次添加。
            choice_list = []
            for i in range(0, len(random_list)):
                if random_list[i] < true_choice_num: # 只有小于该数字，添加的才是正确选项
                    if self.true_queue_list[ad].empty():
                        # 需要追加错误日志处理，类型为崩溃；正常情况下队列不能为空
                        print("Corrupt")
                        return
                    choice_list.append(self.true_queue_list[ad].get())
                else:
                    if self.false_queue_list[ad].empty():
                        # 需要追加错误日志处理，类型为崩溃；正常情况下队列不能为空
                        print("Corrupt")
                        return
                    choice_list.append(self.false_queue_list[ad].get())
            
            # 相关管理变量也要调整
            self.true_count_list[ad] = self.true_count_list[ad] - true_choice_num
            self.false_count_list[ad] = self.false_count_list[ad] - (choice_num - true_choice_num)
            
            # 调用题目生成。
            return_value = self.cons_question.construct_question(question_type, choice_list, self.cata_table[ad][0])
            if return_value == 0:
                # 正常运行，追加日志处理
                continue
            else:
                # 根据情况追加错误日志处理，类型根据情况决定
                self.log_manager.generate_error_log(time.time(), "", "objective_question_generation", "error", 5, "调用construct_question失败")
                continue

    def _manage_one_JSON(self, JSON_choice):
        '''
        领域选项管理的核心函数，对一个JSON进行处理，并调用外部逻辑。

        函数参数：
            JSON_choice，一个选项对应的JSON对象。
                JSON主要元素有"id", "text", "value", "evaluation", "cataid"。

        本函数没有返回值。
        '''

        # 首先对JSON_choice进行schema验证
        try:
            validate(JSON_choice, self.choice_schema)
        except jsonschema.exceptions.ValidationError:
            self.log_manager.generate_error_log(time.time(), "", "objective_question_generation", "warning", 5, "选项不符合schema")
            return # 这一部分做日志处理，类型为警告
        except jsonschema.exceptions.SchemaError as e:
            self.log_manager.generate_error_log(time.time(), "", "objective_question_generation", "corrupt", 1, "schema语法错误")
            raise e # 这一部分做日志处理，类型为崩溃
        
        # 如果通过验证，接下来可以根据JSON的目录结构，确定要加入的队列了。
        choice_cata = JSON_choice["cataid"]
        ad = 0 # 循环变量，用以判断日志
        for ad in range(0, len(self.cata_table)):
            # 目录表范围左闭右开。
            if choice_cata >= str(self.cata_table[ad][1]) and choice_cata < str(self.cata_table[ad][2]):
                # 如果匹配到该范围，观察选项真值加入队列。
                if JSON_choice["value"] == True:
                    self.true_count_list[ad] = self.true_count_list[ad] + 1
                    self.true_queue_list[ad].put(JSON_choice)
                else:
                    self.false_count_list[ad] = self.false_count_list[ad] + 1
                    self.false_queue_list[ad].put(JSON_choice)
                # 队列最大长度为200，所以如果两个队列元素之和为200，就要启动选项生成了。
                if self.true_count_list[ad] + self.false_count_list[ad] >= 200:
                    self._ready_generate_question(ad)

        
        if ad == len(self.cata_table):
            self.log_manager.generate_error_log(time.time(), "", "objective_question_generation", "warning", 1, "选项对应目录不合法")
            # 如果ad等于len(self.cata_table)，说明该选项对应目录不合法，做日志处理，类型为警告。
            return
    
    def read_JSON_file(self):
        '''
        领域选项管理的核心函数，执行一次即可读取整个文件。

        本函数没有参数。

        本函数没有返回值。
        '''

        # 按照正常逻辑进行选项管理。
        JSON_choice = self._read_one_choice()
        while JSON_choice != "":
            self._manage_one_JSON(JSON_choice)
            JSON_choice = self._read_one_choice()

        # 全部文件读入后，把所有选项列表都执行一遍选项生成。
        for i in range(0, len(self.true_queue_list)):
            self._ready_generate_question(i)