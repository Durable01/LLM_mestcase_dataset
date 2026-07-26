import sys
import os
import unittest
import coverage
from abc import ABC, abstractmethod
#这里的根目录是 coal_objective_create/
base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(base_dir)

class CovTestFather(ABC):
    '''
    覆盖率测试父类
    '''
    @abstractmethod
    def create_cov(self,isBranch:bool)->coverage.Coverage:
        '''
        实例化覆盖率测试器
        '''
        pass

    @abstractmethod
    def run_unittest(self):
        pass

    def __init__(self,isBranch = True):
        self.cov = self.create_cov(isBranch)

    def run(self):
        #启动覆盖率测试
        self.cov.start()
        self.run_unittest()
        #停止覆盖率测试
        self.cov.stop()
        #保存覆盖率测试结果至二进制文件
        self.cov.save()

    def report(self):
        #加载覆盖率测试结果
        self.cov.load()
        #控制台输出覆盖率测试报告
        self.cov.report()

    def html_report(self,report_directory:str):
        #加载覆盖率测试结果
        self.cov.load()
        os.makedirs(report_directory, exist_ok=True)
        #生成HTML覆盖率测试报告
        self.cov.html_report(directory=report_directory)

    def xml_report(self,report_path:str):
        #加载覆盖率测试结果
        self.cov.load()
        # 确保输出目录存在
        output_dir = os.path.dirname(report_path)
        os.makedirs(output_dir, exist_ok=True)
        #生成XML覆盖率测试报告
        self.cov.xml_report(outfile=report_path)

    def json_report(self,report_path:str):
        #加载覆盖率测试结果
        self.cov.load()
        # 确保输出目录存在
        output_dir = os.path.dirname(report_path)
        os.makedirs(output_dir, exist_ok=True)
        #生成JSON覆盖率测试报告
        self.cov.json_report(outfile=report_path)

