import sys
import os
import unittest
import json
from jsonschema import validate, ValidationError, SchemaError
import glob
import time
import importlib

# 这里的根目录是 coal_objective_create/
base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(base_dir)

# 日志管理
from src.log_manager import LogManager
# 桩程序导入，方便更改
import src.stack as stk
# 配置文件导入，方便更改
import config.config_choice as config

# 导入被测组件
from src.rob_disturb_entityAssociated import RobDisturbEntityAssociated

class TestCase_03_10(unittest.TestCase):

    @staticmethod
    def exec(vision = 1, test_result_path = None):
        '''执行测试'''
        suite = TestCase_03_10.build_suite()
        if test_result_path:
            with open(test_result_path, 'w', encoding='utf-8') as f:
                runner = unittest.TextTestRunner(stream=f, verbosity=vision)
                result = runner.run(suite)
                if os.environ.get("MUTATION_TEST"):
                    sys.exit(0 if result.wasSuccessful() else 1)
        else:
            runner = unittest.TextTestRunner(stream=sys.stderr, verbosity=vision)
            result = runner.run(suite)
            if os.environ.get("MUTATION_TEST"):
                sys.exit(0 if result.wasSuccessful() else 1)

    @staticmethod
    def build_suite():
        '''构建测试套件'''
        # 目录
        input_dir = os.path.join(base_dir, "test", "input", "rob_disturb_entityAssociated")
        expect_dir = os.path.join(base_dir, "test", "expect", "rob_disturb_entityAssociated")
        output_dir = os.path.join(base_dir, "test", "output", "rob_disturb_entityAssociated")

        input_paths = sorted(glob.glob(os.path.join(input_dir, "*.txt")))
        expect_choice_paths = sorted(glob.glob(os.path.join(expect_dir, "*choice.txt")))
        expect_error_paths = sorted(glob.glob(os.path.join(expect_dir, "*error.txt")))
        expect_run_paths = sorted(glob.glob(os.path.join(expect_dir, "*run.txt")))

        suite = unittest.TestSuite()
        for input_path, expect_choice_path, expect_error_path, expect_run_path in zip(
                input_paths, expect_choice_paths, expect_error_paths, expect_run_paths):
            suite.addTest(TestCase_03_10('test_main', input_path, expect_choice_path, expect_error_path,
                                        expect_run_path, output_dir))
        return suite

    def __init__(self, methodName, input_path, expect_choice_path, expect_error_path, expect_run_path, output_dir):
        super().__init__(methodName)
        self.input_path = input_path
        self.expect_choice_path = expect_choice_path
        self.expect_error_path = expect_error_path
        self.expect_run_path = expect_run_path
        self.output_dir = output_dir

    def setUp(self):
        '''初始化测试用例'''
        self.input_label = os.path.splitext(os.path.basename(self.input_path))[0]
        print(f"[{time.asctime()}]测试用例{self.input_label}已启动...")
        with open(self.input_path, "r", encoding="UTF-8") as f1, \
                open(self.expect_choice_path, "r", encoding="UTF-8") as f2, \
                open(self.expect_error_path, "r", encoding="UTF-8") as f3, \
                open(self.expect_run_path, "r", encoding="UTF-8") as f4:
            try:
                self.input_data = json.load(f1)
                self.expect_choice = None if self.is_file_empty(f2) else json.load(f2)
                self.expect_error = None if self.is_file_empty(f3) else json.load(f3)
                self.expect_run = None if self.is_file_empty(f4) else json.load(f4)
            except json.JSONDecodeError as e:
                self.skipTest(f"{self.input_label}\njson：测试用例格式不符合规范" + str(e))

        self.error_log_path = os.path.join(base_dir, 'log', 'error_log.txt')
        self.run_log_path = os.path.join(base_dir, 'log', 'run_log.txt')
        # 清空日志文件上次残留内容
        with open(self.error_log_path, 'w') as f1, open(self.run_log_path, 'w') as f2:
            pass

        # 设置配置
        self.config_set()

    def test_main(self):
        '''单元测试->目标组件3.10：实体关联内容的干扰-覆盖语义鲁棒性'''
        start_time = time.time()
        result_choices = self.get_choices()
        end_time = time.time()
        generate_time = end_time - start_time
        print(f"生成用时：{generate_time}")

        # 读取生成日志
        with open(self.error_log_path, "r", encoding="UTF-8") as f1, open(self.run_log_path, "r", encoding="UTF-8") as f2:
            error_log = f1.readlines()
            run_log = f2.readlines()

        # 如果不是变异测试则保存结果
        if not os.environ.get("MUTATION_TEST"):
            self.result_save(result_choices, error_log, run_log, generate_time)

        # 对输出与预期存在性是否一致进行先验证
        if not self.is_sameExist(result_choices, self.expect_choice) or not self.is_sameExist(error_log, self.expect_error) or not self.is_sameExist(run_log, self.expect_run):
            self.fail(f"输出与预期存在性不符:  输出|预期\n         \
            选项生成:{bool(result_choices)}|{bool(self.expect_choice)}:\n         \
            异常日志:{bool(error_log)}|{bool(self.expect_error)}:\n         \
            运行日志:{bool(run_log)}|{bool(self.expect_run)}")

        # 选项生成验证
        if result_choices:
            try:
                for choice in result_choices:
                    validate(instance=choice, schema=self.expect_choice)
            except ValidationError as e:
                self.fail("choice:选项生成结果不符合预期")
            except SchemaError as e:
                self.skipTest(f"{self.input_label}\nchoice schema:测试用例预期选项有误")

        # 异常日志验证
        if error_log:
            for line in error_log:
                try:
                    validate(instance=json.loads(line), schema=self.expect_error)
                except ValidationError:
                    self.fail("error_log:异常日志生成结果不符合预期")
                except SchemaError:
                    self.skipTest(f"{self.input_label}\nerror schema:测试用例预期异常日志有误")

        # 运行日志验证
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
        '''
        组件桩程序和相关配置参数所需要的变量的设置区域。
        根据输入用例可注入桩开关，方便模拟外部依赖不同场景。
        '''
        importlib.reload(stk)
        importlib.reload(config)

        # 控制外部依赖桩的行为
        if "OUTER_DEPENDENCIES_NOTICE" in self.input_data:
            stk.OUTER_DEPENDENCIES_NOTICE = self.input_data["OUTER_DEPENDENCIES_NOTICE"]
        if "OUTER_DEPENDENCIES_WARNING" in self.input_data:
            stk.OUTER_DEPENDENCIES_WARNING = self.input_data["OUTER_DEPENDENCIES_WARNING"]

    def get_choices(self):
        '''组件调用generate_choice所需参数设置'''
        try:
            input_knowid = self.input_data["knowid"]
            input_knowstr = self.input_data["knowstr"]
            input_knowcata = self.input_data["knowcata"]
            input_knowtree = self.input_data["knowtree"]
            input_isdebug = self.input_data["isdebug"]
        except Exception as e:
            self.skipTest("input_data: 输入样例必要字段缺失:" + str(e))

        # 生成内容
        self.generator = RobDisturbEntityAssociated(LogManager(_isdebug=input_isdebug))
        result_choices = self.generator.generate_choice(input_knowid, input_knowstr, input_knowcata, input_knowtree)
        return result_choices

    def result_save(self, result_choices, error_log, run_log, generate_time):
        '''保存生成内容'''
        os.makedirs(self.output_dir, exist_ok=True)
        output_choice_path = os.path.join(self.output_dir, self.input_label + "choice.txt")
        output_error_path = os.path.join(self.output_dir, self.input_label + "error.txt")
        output_run_path = os.path.join(self.output_dir, self.input_label + "run.txt")
        with open(output_choice_path, "w", encoding="UTF-8") as f:
            f.write("[\n")
            for i in range(len(result_choices)):
                f.write(json.dumps(result_choices[i], ensure_ascii=False, indent=4))
                if i < len(result_choices) - 1:
                    f.write(",\n")
            f.write("\n]")
            f.write(f"\n生成用时: {generate_time}")
        with open(output_error_path, "w", encoding="UTF-8") as f:
            for line in error_log:
                f.write(line)
        with open(output_run_path, "w", encoding="UTF-8") as f:
            for line in run_log:
                f.write(line)

    def is_sameExist(self, i, j):
        # 检验存在性一致
        return bool(i) == bool(j)

    def is_file_empty(self, f):
        return os.fstat(f.fileno()).st_size == 0

    def __str__(self):
        return f"{self.__class__.__name__}.{self._testMethodName} (file_path={self.input_path})"

if __name__ == "__main__":
    result_path = os.path.join(base_dir, "test", "output", "unittest_3_10.txt")
    TestCase_03_10.exec(2, result_path)