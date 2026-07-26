import sys
import os
#这里的根目录是 coal_objective_create/
base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
test_dir = os.path.join(base_dir,"test")
sys.path.append(base_dir)
sys.path.append(test_dir)

import coverage
import unittest
from coverage_test.covtest_father import CovTestFather

# 使用绝对路径导入
import importlib.util
spec = importlib.util.spec_from_file_location("unittest_3_06", os.path.join(test_dir, "unittest_3_06.py"))
unittest_3_06 = importlib.util.module_from_spec(spec)
spec.loader.exec_module(unittest_3_06)
TestCase_03_06 = unittest_3_06.TestCase_03_06


class CovTest_3_06(CovTestFather):
    def create_cov(self,isBranch:bool)->coverage.Coverage:
        '''设置覆盖率测试器
        '''
        include = os.path.join(base_dir,"src","acc_transform_knowledgeRepresent.py")
        data_file = os.path.join(base_dir,"coverage_test","output","acc_transform_knowledgeRepresent",".coverage_3_06")
        
        # 确保输出目录存在
        output_dir = os.path.dirname(data_file)
        os.makedirs(output_dir, exist_ok=True)
        
        new_cov = coverage.Coverage(
            include=[include],
            data_file=data_file,
            branch=isBranch,
            omit=[]  # 明确指定omit参数
        )
        return new_cov

    def run_unittest(self,vision = 1, test_result_path = None):
        TestCase_03_06.exec(vision, test_result_path)
        pass


if __name__ == "__main__":
    covtest = CovTest_3_06(isBranch=True)
    covtest.run()
    covtest.report()
    covtest.html_report(os.path.join(base_dir,"coverage_test","output","acc_transform_knowledgeRepresent","coverage_3_06_html"))
    covtest.xml_report(os.path.join(base_dir,"coverage_test","output","acc_transform_knowledgeRepresent","coverage_3_06.xml"))
    covtest.json_report(os.path.join(base_dir,"coverage_test","output","acc_transform_knowledgeRepresent","coverage_3_06.json"))
