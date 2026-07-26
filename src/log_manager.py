'''
日志管理
本模块从外部读取参数组织成json并写入文件
目前所有的json写入到两个文件，错误日志error_log,运行日志run_log，每个json单独一行

版本迭代情况
[脱敏] 版本迭代记录

本组件不存在外部依赖，内部依赖，大模型依赖。

配置变量使用情况:
THRESHOLD_LOG:从列表写入文件的阈值

'''

import json
import os
from os import write
import config.config_choice

class LogManager:
    '''
    日志管理类
    变量：
    error_log_list:存储错误日志的列表
    run_log_list:存储运行日志的列表
    isdebug=_isdebug:是否开启debug模式
    error_log_pointer:错误日志文件指针
    run_log_pointer:运行日志文件指针
    threshold_output:给定的调用输出函数的阈值,从config中获取，默认是3
    '''
    def __init__(self, _isdebug):
        '''
        初始化日志列表
        需要注意的是 初始化需要传递_isdebug这个参数用于判断是否是debug模式，True标识处于debug状态
        '''
        self.error_log_list = []
        self.run_log_list = []
        self.isdebug = _isdebug

        #初始化文件指针
        error_log_path = config.config_choice.ERROR_LOG_PATH
        # [脱敏] 日志路径已改为从配置文件读取
        self.error_log_pointer = open(error_log_path, 'a', encoding="UTF-8")

        run_log_path = config.config_choice.RUN_LOG_PATH
        # [脱敏] 日志路径已改为从配置文件读取
        self.run_log_pointer = open(run_log_path, 'a', encoding="UTF-8")

        #从config文件中获取阈值
        self.threshold_output = config.config_choice.THRESHOLD_LOG

    def generate_error_log(self, timestamp, knowid, componentid, exception, type, information):
        '''
        本函数用于生成错误日志json字符串

        timestamp:时间戳，浮点数
        knowid:知识id
        componentid:组件的标识
        exception:异常类型,一共四种 notice warning error corrupt
        type:异常种类
        information:异常信息

        '''

        #当不是debug模式下且类型为notice时不需要输出日志
        if(exception == 'notice' and self.isdebug == False):
            return

        #重点处理information中的换行符保证json单独一行
        information = information.replace('\n', '')

        #构建字典
        error_log = {}
        error_log["timestamp"] = timestamp
        error_log["knowid"] = knowid
        error_log["componentid"] = componentid
        error_log["exception"] = exception
        error_log["type"] = type
        error_log["information"] = information

        #转换成字符串
        error_log_json = json.dumps(error_log, separators=(',', ':'), ensure_ascii=False)
        self.error_log_list.append(error_log_json)

        #判断是否超出阈值，超出则调用输出函数写入文件中
        if(len(self.error_log_list) >= self.threshold_output):
            self.write_error_file()
            #清空列表
            self.error_log_list.clear()

    def generate_run_log(self, timestamp, knowid, componentid, genamount):
        '''
        timestamp: 时间戳，浮点数
        knowid: 知识id
        componentid: 组件的标识
        genamount: 生成了多少个选型
        '''

        #构建字典
        run_log = {}
        run_log["timestamp"] = timestamp
        run_log["knowid"] = knowid
        run_log["componentid"] = componentid
        run_log["genamount"] = genamount

        #转换为字符串
        run_log_json = json.dumps(run_log, separators=(',', ':'), ensure_ascii=False)
        self.run_log_list.append(run_log_json)

        # 判断是否超出阈值，超出则调用输出函数写入文件中
        if(len(self.run_log_list) >= self.threshold_output):
            self.write_run_file()
            #清空列表
            self.run_log_list.clear()

    def write_error_file(self):
        '''
        写入错误日志文件
        本函数没有参数,为public函数
        '''
        for error_log in self.error_log_list:
            self.error_log_pointer.write(error_log)
            self.error_log_pointer.write('\n')
        self.error_log_pointer.flush()

    def write_run_file(self):
        '''
        写入运行日志文件
        本函数没有参数,为public函数
        '''

        for run_log in self.run_log_list:
            self.run_log_pointer.write(run_log)
            self.run_log_pointer.write('\n')
        self.run_log_pointer.flush()

    def __del__(self):
        '''
        析构函数：保证在日志管理组件将所有日志刷新到磁盘中，保证日志不会消失
        '''
        self.write_error_file()
        self.write_run_file()
        #关闭文件指针
        self.error_log_pointer.close()
        self.run_log_pointer.close()