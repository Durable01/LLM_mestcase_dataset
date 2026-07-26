import sys
import os
import unittest
import json
from jsonschema import validate, ValidationError, SchemaError
import glob
import time
import importlib

#这里的根目录是 coal_objective_create/
base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(base_dir)

# 日志管理
from src.log_manager import LogManager
# 桩程序导入，方便更改
import src.stack as stk
#配置文件导入，方便更改
import config.config_choice as config
from src.att_fuzzy_inference import AttFuzzyInference

class TestCase_03_29(unittest.TestCase):

    @staticmethod
    def exec(vision=1, test_result_path=None):
        '''执行测试
        '''
        suite = TestCase_03_29.build_suite()
        if test_result_path:
            with open(test_result_path, 'w', encoding='utf-8') as f:
                runner = unittest.TextTestRunner(stream=f, verbosity=vision)
                result = runner.run(suite)
                sys.exit(0 if result.wasSuccessful() else 1)
        else:
            runner = unittest.TextTestRunner(stream=sys.stderr, verbosity=vision)
            result = runner.run(suite)
            sys.exit(0 if result.wasSuccessful() else 1)

    @staticmethod
    def build_suite():
        ''' 构建测试套件
        '''
        # 输入用例目录
        input_dir = os.path.join(base_dir, "test", "input", "att_fuzzy_inference")
        # 预期输出目录
        expect_dir = os.path.join(base_dir, "test", "expect", "att_fuzzy_inference")
        # 实际输出目录
        output_dir = os.path.join(base_dir, "test", "output", "att_fuzzy_inference")

        input_paths = sorted(glob.glob(os.path.join(input_dir, "*.txt")))
        #获取预期输出用例文件路径列表
        expect_choice_paths = sorted(glob.glob(os.path.join(expect_dir, "*choice.txt")))
        #获取预期异常日志文件路径列表
        expect_error_paths = sorted(glob.glob(os.path.join(expect_dir, "*error.txt")))
        #获取预期运行日志文件路径列表
        expect_run_paths = sorted(glob.glob(os.path.join(expect_dir, "*run.txt")))

        suite = unittest.TestSuite()
        for input_path, expect_choice_path, expect_error_path, expect_run_path in zip(input_paths, expect_choice_paths, expect_error_paths, expect_run_paths):
            suite.addTest(TestCase_03_29('test_main', input_path, expect_choice_path, expect_error_path, expect_run_path, output_dir))
        return suite

    def __init__(self, methodName, input_path, expect_choice_path, expect_error_path, expect_run_path, output_dir):
        super().__init__(methodName)
        self.input_path = input_path
        self.expect_choice_path = expect_choice_path
        self.expect_error_path = expect_error_path
        self.expect_run_path = expect_run_path
        self.output_dir = output_dir

    def setUp(self):
        '''初始化测试用例:
            1.读取测试用例文件
            2.清空原有日志
            3.设置配置
        '''
        #用于输出信息的测试文件名标签(不带后缀)
        self.input_label = os.path.splitext(os.path.basename(self.input_path))[0]
        #1.读取测试用例文件
        print(f"[{time.asctime()}]测试用例{self.input_label}已启动...")
        #读取加载json文件
        with open(self.input_path, "r", encoding="UTF-8") as f1, \
             open(self.expect_choice_path, "r", encoding="UTF-8") as f2, \
             open(self.expect_error_path, "r", encoding="UTF-8") as f3, \
             open(self.expect_run_path, "r", encoding="UTF-8") as f4:
            try:
                #f1默认应该有内容，空和不符合格式均不规范
                self.input_data = json.load(f1)
                #f2,3,4预期结果可能为空，也可能写法有误
                self.expect_choice = None if self.is_file_empty(f2) else json.load(f2)
                self.expect_error = None if self.is_file_empty(f3) else json.load(f3)
                self.expect_run = None if self.is_file_empty(f4) else json.load(f4)
            except json.JSONDecodeError as e:
                self.skipTest(f"{self.input_label}\njson：测试用例格式不符合规范 {e}")

        '''2.获取日志结果存放路径，并清空日志文件
        '''
        self.error_log_path = os.path.join(base_dir, 'log', 'error_log.txt')
        self.run_log_path = os.path.join(base_dir, 'log', 'run_log.txt')
        os.makedirs(os.path.dirname(self.error_log_path), exist_ok=True)
        with open(self.error_log_path, 'w') as f1, open(self.run_log_path, 'w') as f2:
            pass

        '''3.设置配置
        '''
        self.config_set()

    def test_main(self):
        '''单元测试->目标组件3.29
            1.生成内容并提取日志
            2.保存输出结果
            3.验证输出结果
        '''    

        '''1.开始生成内容和提取日志
        '''
        start_time = time.time()
        result_choices = self.get_choices()
        end_time = time.time()
        generate_time = end_time - start_time
        print(f"生成用时：{generate_time}")

        # 读取日志结果
        with open(self.error_log_path, "r", encoding="UTF-8") as f1, open(self.run_log_path, "r", encoding="UTF-8") as f2:
            error_log = f1.readlines()
            run_log = f2.readlines()

        '''2.保存各项生成内容，方便后续追踪查看
            这里通过环境变量MUTATION_TEST确定是否保存文件，方便后续变异测试
        '''
        if not os.environ.get("MUTATION_TEST"):
            self.result_save(result_choices, error_log, run_log, generate_time)

        '''3.开始测试，验证输出结果
        '''
        # 存在性检查（输出与期望同时存在或同时为空）
        if not self.is_sameExist(result_choices, self.expect_choice) or \
           not self.is_sameExist(error_log, self.expect_error) or \
           not self.is_sameExist(run_log, self.expect_run):
            self.fail(f"输出与预期存在性不符:  输出|预期\n         \
            选项生成:{bool(result_choices)}|{bool(self.expect_choice)}:\n         \
            异常日志:{bool(error_log)}|{bool(self.expect_error)}:\n         \
            运行日志:{bool(run_log)}|{bool(self.expect_run)}")

        '''确认存在性一致后
        '''
        #选项生成验证(如果存在性为空，则默认通过)
        if result_choices:
            try:
                for choice in result_choices:
                    validate(instance=choice, schema=self.expect_choice)
            except ValidationError as e:
                self.fail("choice:选项生成结果不符合预期")
            except SchemaError as e:
                self.skipTest(f"{self.input_label}\nchoice schema:测试用例预期选项有误")

        #异常日志验证(如果存在性为空，则默认通过)
        if error_log:
            for line in error_log:
                try:
                    validate(instance=json.loads(line), schema=self.expect_error)
                except ValidationError:
                    self.fail("error_log:异常日志生成结果不符合预期")
                except SchemaError:
                    self.skipTest(f"{self.input_label}\nerror schema:测试用例预期异常日志有误")

        #运行日志验证(如果存在性为空，则默认通过)
        if run_log:
            if len(run_log) > 1:
                self.fail(f"run_log:运行日志生成数量不符合预期,生成数量:{len(run_log)}")
            try:
                validate(instance=json.loads(run_log[0]), schema=self.expect_run)
            except ValidationError:
                self.fail("run_log:运行日志生成结果不符合预期")
            except SchemaError:
                self.skipTest(f"{self.input_label}\nrun schema:测试用例预期运行日志有误")

    def config_set(self):
        ''' 组件桩程序和相关配置参数所需要的变量的设置区域。
        '''
        importlib.reload(stk)
        importlib.reload(config)
        if "api_key" in self.input_data:
            config.API_KEY = self.input_data["api_key"]

    def get_choices(self):
        ''' 组件调用generate_choice所需要的参数的设置区域。
        '''
        try:
            input_knowid = self.input_data["knowid"]
            input_knowstr = self.input_data.get("knowstr", "")
            input_knowcata = self.input_data.get("knowcata", "")
            input_inference = self.input_data.get("inference", {})
            input_isdebug = self.input_data.get("isdebug", False)
        except Exception as e:
            self.skipTest("input_data: 输入样例必要字段缺失:" + str(e))
        #生成内容
        self.generator = AttFuzzyInference(LogManager(_isdebug=input_isdebug))
        result_choices = self.generator.generate_choice(input_knowid, input_knowstr, input_knowcata, input_inference)
        return result_choices

    def result_save(self, result_choices, error_log, run_log, generate_time):
        '''保存各项生成内容，方便后续追踪查看
        '''
        output_choice_path = os.path.join(self.output_dir, self.input_label + "choice.txt")
        output_error_path = os.path.join(self.output_dir, self.input_label + "error.txt")
        output_run_path = os.path.join(self.output_dir, self.input_label + "run.txt")
        #写入生成选项文件  
        with open(output_choice_path, "w", encoding="UTF-8") as f:
            f.write("[\n")
            for i in range(len(result_choices)):
                f.write(json.dumps(result_choices[i], ensure_ascii=False, indent=4))
                if i < len(result_choices) - 1:
                    f.write(",\n")
            f.write("\n]")
            f.write(f"\n生成用时: {generate_time}")

        #写入异常日志文件
        with open(output_error_path, "w", encoding="UTF-8") as f:
            for line in error_log:
                f.write(line)

        #写入运行日志文件
        with open(output_run_path, "w", encoding="UTF-8") as f:
            for line in run_log:
                f.write(line)

    def is_sameExist(self, i, j):
        '''检验存在性一致
        '''
        return bool(i) == bool(j)

    def is_file_empty(self, f):
        return os.fstat(f.fileno()).st_size == 0

    def __str__(self):
        return f"{self.__class__.__name__}.{self._testMethodName} (file_path={self.input_path})"

if __name__ == '__main__':
    result_path = os.path.join(base_dir, "test", "output", "unittest_3_29.txt")
    TestCase_03_29.exec(2, result_path)

