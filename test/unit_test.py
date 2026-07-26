import sys
import os
import unittest
import json
from jsonschema import validate,ValidationError,SchemaError
import glob
import time
import importlib

#这里的根目录是 coal_objective_create/
base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(base_dir)

# 日志管理
from src.log_manager import LogManager
#桩程序导入，方便更改
import src.stack as stk
#配置文件导入，方便更改
import config.config_choice as config

# 导入所有待测试组件
# 核查组件
from src.rely_KG_check import check_KG_consistency
from src.rely_ES_check import check_entity_consistency
from src.rely_IG_check import check_inference_consistency

# 准确性待测试组件
from src.acc_transform_knowledgeRepresent import AccTransformKnowledgeRepresent
from src.acc_entity_replace import AccEntityReplace
from src.acc_KG_confuse import AccKGConfuse

# 鲁棒性待测试组件
from src.rob_disturb_entityAssociated import RobDisturbEntityAssociated
from src.rob_homophone_disturb import RobHomophoneDisturb
from src.rob_stopwords_interference import RobStopwordsInterference
#from src.rob_synonym_algorithm import RobSynonymAlgorithm

# 构建一致性待测试组件
from src.cons_reload_parallelrelation import ConsReloadParallelRelation

# 敏感性待测试组件
from src.lim_valueconstrain_transform import LimValueConstraintTransform
from src.lim_unit_transform import LimUnitTransform
from src.lim_LLMgenerate_mask import LimLLMGenerateMask
from src.lim_reload_textdescription import LimReloadTextDescription

# 推理可靠性待测试组件
from src.inf_single_inference import InfSingleInference
from src.inf_inference_chain import InfInferenceChain
from src.inf_inference_trap import InfInferenceTrap

# 题目生成待测试组件
from src.objective_question_generation import ObjectiveQuestionGeneration
from src.construct_question import ConstructQuestion



class TestCase_objective_unittest(unittest.TestCase):

    def setUp(self):
        #各个测试方法共用的初始化
        super().setUp()

    def tearDown(self):
        #各个测试方法共用的后处理
        super().tearDown()

    @classmethod
    def exec_unittest(cls,index,vision = 1, test_result_path = None):
        '''外部调用的运行器，指定单元编号运行
        参数:index:运行单元测试的组件编号(如18),无法找到的情况下打印错误信息并退出
            vision:详细程度,1默认(简略)、2(详细)、0(最简)
            result_path:
                指定时输出的文件路径(写入为'w'模式)
                不指定时默认输入到控制台(sys.stderr)
        '''
        suite = unittest.TestSuite()
        try:
            suite.addTest(TestCase_objective_unittest("test_03_"+str(index))) #这里名称无效会报AttributeError
        except Exception as e:
            print(f"指定测试编号:{index}:无效") 
            return
        if test_result_path :
            with open(test_result_path,'w',encoding='utf-8') as f:
                runner = unittest.TextTestRunner(stream=f, verbosity = vision)
                result = runner.run(suite)
                sys.exit(0 if result.wasSuccessful() else 1)    
        else:
                runner = unittest.TextTestRunner(stream= sys.stderr,verbosity = vision)
                result = runner.run(suite)
                sys.exit(0 if result.wasSuccessful() else 1)

    @classmethod
    def exec_all(cls,vision = 1, test_result_path = None):
        '''外部调用的运行器，使所有组件测试运行
        参数:index:运行单元测试的组件编号(如18),无法找到的情况下打印错误信息并退出
            vision:详细程度,1默认(简略)、2(详细)、0(最简)
            result_path:
                指定时输出的文件路径(写入为'w'模式)
                不指定时默认输入到控制台(sys.stderr)
        '''
        suite = unittest.TestSuite()
        suite.addTest(unittest.TestLoader().loadTestsFromTestCase(TestCase_objective_unittest))
        if test_result_path :
            with open(test_result_path,'w',encoding='utf-8') as f:
                runner = unittest.TextTestRunner(stream=f, verbosity = vision)
                runner.run(suite)
        else:
                runner = unittest.TextTestRunner(stream= sys.stderr,verbosity = vision)
                runner.run(suite)

    def test_03_04(self):
        pass

    def test_03_05(self):
        '''
        单元测试->目标组件3.5：知识图谱相近概念混淆-覆盖知识准确性
        '''
        # 输入用例目录
        input_dir = os.path.join(base_dir, "test", "input", "acc_KG_confuse")
        
        # 预期输出用例目录
        expect_dir = os.path.join(base_dir, "test", "expect", "acc_KG_confuse")
        
        # 最后用来存放实际输出结果的目录
        output_dir = os.path.join(base_dir, "test", "output", "acc_KG_confuse")

        # 获取输入用例文件路径列表
        input_paths = sorted(glob.glob(os.path.join(input_dir, "*.txt")))
        
        # 获取预期输出用例文件路径列表
        expect_choice_paths = sorted(glob.glob(os.path.join(expect_dir, "*choice.txt")))
        
        # 获取预期异常日志文件路径列表
        expect_error_paths = sorted(glob.glob(os.path.join(expect_dir, "*error.txt")))
        
        # 获取预期运行日志文件路径列表
        expect_run_paths = sorted(glob.glob(os.path.join(expect_dir, "*run.txt")))


        #并行遍历各个相对应的文件
        for input_path,expect_choice_path,expect_error_path,expect_run_path in zip(input_paths,expect_choice_paths,expect_error_paths,expect_run_paths):
            #区分子测试
            with self.subTest(testcase = os.path.basename(input_path)):
                #用于输出信息的测试文件名标签(不带后缀)
                input_label = os.path.splitext(os.path.basename(input_path))[0]
                print(f"[{time.asctime()}]测试用例{input_label}已启动...")
                #读取加载json文件
                with open(input_path, "r", encoding="UTF-8") as f1, \
                    open(expect_choice_path, "r", encoding="UTF-8") as f2, \
                    open(expect_error_path, "r", encoding="UTF-8") as f3, \
                    open(expect_run_path, "r", encoding="UTF-8") as f4:
                    try:
                        #f1默认应该有内容，空和不符合格式均不规范
                        input_data = json.load(f1)
                        #f2,3,4预期结果可能为空，也可能写法有误
                        expect_choice = None if self.is_file_empty(f2) else json.load(f2)
                        expect_error = None if self.is_file_empty(f3) else json.load(f3)
                        expect_run = None if self.is_file_empty(f4) else json.load(f4)

                    except json.JSONDecodeError as e:
                        self.skipTest(f"{input_label}\njson：测试用例格式不符合规范"+str(e))

                '''获取日志结果存放路径
                '''
                error_log_path = os.path.join(base_dir, 'log', 'error_log.txt')
                run_log_path = os.path.join(base_dir, 'log', 'run_log.txt')
                #清空日志文件上次残留内容
                with open(error_log_path,'w') as f1,open(run_log_path,'w') as f2:
                    pass

                #配置重导入,确保初始化
                importlib.reload(stk)
                importlib.reload(config)

                # 控制抛异常
                if "GET_SIMILAR_ENTITIES_ERROR" in input_data:
                    stk.GET_SIMILAR_ENTITIES_ERROR = bool(input_data["GET_SIMILAR_ENTITIES_ERROR"])
                else:
                    stk.GET_SIMILAR_ENTITIES_ERROR = False # 测试用例没有此字段时默认不异常

                #提取必需字段
                try:
                    input_knowid = input_data["knowid"]
                    input_knowstr = input_data["knowstr"]
                    input_knowcata = input_data["knowcata"]
                    input_entityrelation = input_data["entityrelation"]
                    input_isdebug = input_data["isdebug"]
                except Exception as e:
                    self.skipTest("input_data:"+"输入样例必要字段缺失:"+str(e))

                '''开始生成内容
                '''
                start_time = time.time()
                self.generator = AccKGConfuse(LogManager(_isdebug=input_isdebug))
                result_choices = self.generator.generate_choice(input_knowid, input_knowstr, input_knowcata, input_entityrelation)
                end_time = time.time()
                generate_time = end_time - start_time
                print(f"生成用时：{generate_time}")

                #生成日志结果从文件读取
                with open(error_log_path, "r", encoding="UTF-8") as f1,open(run_log_path, "r", encoding="UTF-8") as f2:
                    error_log =  f1.readlines() #这里的读入只是文本，后续使用要loads()
                    run_log =  f2.readlines()

                '''保存各项生成内容，方便后续追踪查看
                    这里通过环境变量MUTATION_TEST确定是否保存文件(对单元测试无影响，只要不去专门搞系统全局变量就行)，方便后续变异测试
                '''
                if not os.environ.get("MUTATION_TEST"):
                    output_choice_path = os.path.join(output_dir,input_label+"choice.txt")
                    output_error_path = os.path.join(output_dir,input_label+"error.txt")
                    output_run_path = os.path.join(output_dir,input_label+"run.txt")
                    #写入生成选项文件          
                    with open(output_choice_path,"w", encoding="UTF-8") as f:
                            f.write("[\n")
                            for i in range(len(result_choices)):
                                f.write(json.dumps(result_choices[i], ensure_ascii=False, indent=4))
                                if i < len(result_choices) - 1:
                                    f.write(",\n")
                            f.write("\n]")
                            f.write(f"\n生成用时: {generate_time}")
                    #写入异常日志文件
                    with open(output_error_path,"w", encoding="UTF-8") as f:
                            for line in error_log:
                                f.write(line)
                    
                    #写入运行日志文件
                    with open(output_run_path,"w", encoding="UTF-8") as f:
                            for line in run_log:
                                f.write(line)

                '''开始测试，验证输出结果
                '''
                #对输出与预期存在性是否一致进行先验证 (确保后续 schema 和 检验内容 同时非空 或 同时空 )
                if not self.is_sameExist(result_choices,expect_choice) or not self.is_sameExist(error_log,expect_error) or not self.is_sameExist(run_log,expect_run) :
                    self.fail(f"输出与预期存在性不符:  输出|预期\n         \
                    选项生成:{bool(result_choices)}|{bool(expect_choice)}:\n         \
                    异常日志:{bool(error_log)}|{bool(expect_error)}:\n         \
                    运行日志:{bool(run_log)}|{bool(expect_run)}")

                '''确认存在性一致后
                '''
                #选项生成验证(如果存在性为空，则默认通过)
                if result_choices:
                    try:
                        for choice in result_choices:
                            validate(instance = choice,schema = expect_choice)
                    except ValidationError as e:
                        self.fail("choice:选项生成结果不符合预期")
                    except SchemaError as e:
                        self.skipTest(f"{input_label}\nchoice schema:测试用例预期选项有误")

                #异常日志验证(如果存在性为空，则默认通过)
                if error_log:
                    for line in error_log:
                        try:
                            validate(instance=json.loads(line),schema=expect_error) #之前只是把文本行读进来了，所以得转换
                        except ValidationError as e:
                            self.fail("error_log:异常日志生成结果不符合预期")
                        except SchemaError as e:
                            self.skipTest(f"{input_label}\nerror schema:测试用例预期异常日志有误")
                    
                #运行日志验证(如果存在性为空，则默认通过)
                if run_log:
                    if len(run_log) > 1:#这里做一个额外检验
                        self.fail(f"run_log:运行日志生成数量不符合预期,生成数量:{len(run_log)}")
                    try:
                        validate(instance=json.loads(run_log[0]),schema=expect_run)
                    except ValidationError as e:
                        self.fail("run_log:运行日志生成结果不符合预期")
                    except SchemaError as e:
                        self.skipTest(f"{input_label}\nrun schema:测试用例预期运行日志有误")
        
        pass

    def test_03_06(self):
        pass

    def test_03_07(self):
        pass

    def test_03_08(self):
        '''单元测试->目标组件3.8：字典检索的非敏感错别字干扰-覆盖语义鲁棒性
        '''
        # 定位输入用例目录
        input_dir = os.path.join(base_dir, "test", "input", "rob_homophone_disturb")

        # 定位预期输出用例目录
        expect_dir = os.path.join(base_dir, "test", "expect", "rob_homophone_disturb")

        # 最后用来存放实际输出结果的目录
        output_dir = os.path.join(base_dir, "test", "output", "rob_homophone_disturb")

        # 获取输入用例文件路径列表，这里排序使得各个下标对应
        input_paths = sorted(glob.glob(os.path.join(input_dir, "*.txt")))

        # 获取预期输出用例文件路径列表
        expect_choice_paths = sorted(glob.glob(os.path.join(expect_dir, "*choice.txt")))
        expect_error_paths = sorted(glob.glob(os.path.join(expect_dir, "*error.txt")))
        expect_run_paths = sorted(glob.glob(os.path.join(expect_dir, "*run.txt")))

        # 并行遍历各个相对应的文件
        for input_path, expect_choice_path, expect_error_path, expect_run_path in zip(
                input_paths, expect_choice_paths, expect_error_paths, expect_run_paths):
            with self.subTest(testcase=os.path.basename(input_path)):
                input_label = os.path.splitext(os.path.basename(input_path))[0]
                print(f"[{time.asctime()}]测试用例{input_label}已启动...")
                # 读取加载json文件
                with open(input_path, "r", encoding="UTF-8") as f1, \
                    open(expect_choice_path, "r", encoding="UTF-8") as f2, \
                    open(expect_error_path, "r", encoding="UTF-8") as f3, \
                    open(expect_run_path, "r", encoding="UTF-8") as f4:
                    try:
                        input_data = json.load(f1)
                        expect_choice = None if self.is_file_empty(f2) else json.load(f2)
                        expect_error = None if self.is_file_empty(f3) else json.load(f3)
                        expect_run = None if self.is_file_empty(f4) else json.load(f4)
                    except json.JSONDecodeError as e:
                        self.skipTest(f"{input_label}\njson：测试用例格式不符合规范" + str(e))

                # 获取日志结果存放路径并清空
                error_log_path = os.path.join(base_dir, 'log', 'error_log.txt')
                run_log_path = os.path.join(base_dir, 'log', 'run_log.txt')
                with open(error_log_path, 'w') as f1, open(run_log_path, 'w') as f2:
                    pass

                # 重新加载桩程序和配置
                importlib.reload(stk)
                importlib.reload(config)

                # 处理输入参数
                try:
                    input_knowid = input_data["knowid"]
                    input_knowstr = input_data["knowstr"]
                    input_knowcata = input_data["knowcata"]
                    input_knowtree = input_data["knowtree"]
                    input_isdebug = input_data["isdebug"]
                except Exception as e:
                    self.skipTest("input_data:" + "输入样例必要字段缺失:" + str(e))

                # 开始生成内容
                start_time = time.time()
                generator = RobHomophoneDisturb(LogManager(_isdebug=input_isdebug))
                result_choices = generator.generate_choice(input_knowid, input_knowstr, input_knowcata, input_knowtree)
                end_time = time.time()
                generate_time = end_time - start_time
                print(f"生成用时：{generate_time}")

                # 读取日志文件
                with open(error_log_path, "r", encoding="UTF-8") as f1, open(run_log_path, "r", encoding="UTF-8") as f2:
                    error_log = f1.readlines()
                    run_log = f2.readlines()

                # 保存输出
                if not os.environ.get("MUTATION_TEST"):
                    os.makedirs(output_dir, exist_ok=True)
                    output_choice_path = os.path.join(output_dir, input_label + "choice.txt")
                    output_error_path = os.path.join(output_dir, input_label + "error.txt")
                    output_run_path = os.path.join(output_dir, input_label + "run.txt")
                    # 写入生成选项文件
                    with open(output_choice_path, "w", encoding="UTF-8") as f:
                        f.write("[\n")
                        for i in range(len(result_choices)):
                            f.write(json.dumps(result_choices[i], ensure_ascii=False, indent=4))
                            if i < len(result_choices) - 1:
                                f.write(",\n")
                        f.write("\n]")
                        f.write(f"\n生成用时: {generate_time}")
                    # 写入异常日志文件
                    with open(output_error_path, "w", encoding="UTF-8") as f:
                        for line in error_log:
                            f.write(line)
                    # 写入运行日志文件
                    with open(output_run_path, "w", encoding="UTF-8") as f:
                        for line in run_log:
                            f.write(line)

                # 验证输出与预期存在性一致性
                if not self.is_sameExist(result_choices, expect_choice) or not self.is_sameExist(error_log, expect_error) or not self.is_sameExist(run_log, expect_run):
                    self.fail(f"输出与预期存在性不符:  输出|预期\n         \
                    选项生成:{bool(result_choices)}|{bool(expect_choice)}:\n         \
                    异常日志:{bool(error_log)}|{bool(expect_error)}:\n         \
                    运行日志:{bool(run_log)}|{bool(expect_run)}")

                # 若存在结果则进行schema验证
                if result_choices:
                    try:
                        for choice in result_choices:
                            validate(instance=choice, schema=expect_choice)
                    except ValidationError:
                        self.fail("choice:选项生成结果不符合预期")
                    except SchemaError:
                        self.skipTest(f"{input_label}\nchoice schema:测试用例预期选项有误")

                # 异常日志验证（若存在性为空则默认通过）
                if error_log:
                    for line in error_log:
                        try:
                            validate(instance=json.loads(line), schema=expect_error)
                        except ValidationError:
                            self.fail("error_log:异常日志生成结果不符合预期")
                        except SchemaError:
                            self.skipTest(f"{input_label}\nerror schema:测试用例预期异常日志有误")

                # 运行日志验证（若存在性为空则默认通过）
                if run_log:
                    if len(run_log) > 1:
                        self.fail(f"run_log:运行日志生成数量不符合预期,生成数量:{len(run_log)}")
                    try:
                        validate(instance=json.loads(run_log[0]), schema=expect_run)
                    except ValidationError:
                        self.fail("run_log:运行日志生成结果不符合预期")
                    except SchemaError:
                        self.skipTest(f"{input_label}\nrun schema:测试用例预期运行日志有误")


    def test_03_09(self):
        pass

    def test_03_10(self):
        # 目录
        input_dir = os.path.join(base_dir, "test", "input", "rob_disturb_entityAssociated")
        expect_dir = os.path.join(base_dir, "test", "expect", "rob_disturb_entityAssociated")
        output_dir = os.path.join(base_dir, "test", "output", "rob_disturb_entityAssociated")

        input_paths = sorted(glob.glob(os.path.join(input_dir, "*.txt")))
        expect_choice_paths = sorted(glob.glob(os.path.join(expect_dir, "*choice.txt")))
        expect_error_paths = sorted(glob.glob(os.path.join(expect_dir, "*error.txt")))
        expect_run_paths = sorted(glob.glob(os.path.join(expect_dir, "*run.txt")))

        for input_path, expect_choice_path, expect_error_path, expect_run_path in zip(input_paths, expect_choice_paths, expect_error_paths, expect_run_paths):
            with self.subTest(testcase=os.path.basename(input_path)):
                input_label = os.path.splitext(os.path.basename(input_path))[0]
                print(f"[{time.asctime()}]测试用例{input_label}已启动...")
                with open(input_path, "r", encoding="UTF-8") as f1, \
                     open(expect_choice_path, "r", encoding="UTF-8") as f2, \
                     open(expect_error_path, "r", encoding="UTF-8") as f3, \
                     open(expect_run_path, "r", encoding="UTF-8") as f4:
                    try:
                        input_data = json.load(f1)
                        expect_choice = None if self.is_file_empty(f2) else json.load(f2)
                        expect_error = None if self.is_file_empty(f3) else json.load(f3)
                        expect_run = None if self.is_file_empty(f4) else json.load(f4)
                    except json.JSONDecodeError as e:
                        self.skipTest(f"{input_label}\njson：测试用例格式不符合规范 {e}")

                # 清空日志
                error_log_path = os.path.join(base_dir, 'log', 'error_log.txt')
                run_log_path = os.path.join(base_dir, 'log', 'run_log.txt')
                with open(error_log_path, 'w') as f1, open(run_log_path, 'w') as f2:
                    pass

                # 重导入桩与配置
                importlib.reload(stk)
                importlib.reload(config)

                if "OUTER_DEPENDENCIES_NOTICE" in input_data:
                    stk.OUTER_DEPENDENCIES_NOTICE = input_data["OUTER_DEPENDENCIES_NOTICE"]
                if "OUTER_DEPENDENCIES_WARNING" in input_data:
                    stk.OUTER_DEPENDENCIES_WARNING = input_data["OUTER_DEPENDENCIES_WARNING"]

                try:
                    input_knowid = input_data["knowid"]
                    input_knowstr = input_data["knowstr"]
                    input_knowcata = input_data["knowcata"]
                    input_knowtree = input_data["knowtree"]
                    input_isdebug = input_data.get("isdebug", False)
                except Exception as e:
                    self.skipTest("input_data: 输入样例必要字段缺失: " + str(e))

                start_time = time.time()
                generator = RobDisturbEntityAssociated(LogManager(_isdebug=input_isdebug))
                result_choices = generator.generate_choice(input_knowid, input_knowstr, input_knowcata, input_knowtree)
                end_time = time.time()
                generate_time = end_time - start_time
                print(f"生成用时：{generate_time}")

                with open(error_log_path, "r", encoding="UTF-8") as f1, open(run_log_path, "r", encoding="UTF-8") as f2:
                    error_log = f1.readlines()
                    run_log = f2.readlines()

                if not os.environ.get("MUTATION_TEST"):
                    output_choice_path = os.path.join(output_dir, input_label + "choice.txt")
                    output_error_path = os.path.join(output_dir, input_label + "error.txt")
                    output_run_path = os.path.join(output_dir, input_label + "run.txt")
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

                if not self.is_sameExist(result_choices, expect_choice) or not self.is_sameExist(error_log, expect_error) or not self.is_sameExist(run_log, expect_run):
                    self.fail(f"输出与预期存在性不符:  输出|预期\n         \
                    选项生成:{bool(result_choices)}|{bool(expect_choice)}:\n         \
                    异常日志:{bool(error_log)}|{bool(expect_error)}:\n         \
                    运行日志:{bool(run_log)}|{bool(expect_run)}")

                if result_choices:
                    try:
                        for choice in result_choices:
                            validate(instance=choice, schema=expect_choice)
                    except ValidationError:
                        self.fail("choice:选项生成结果不符合预期")
                    except SchemaError:
                        self.skipTest(f"{input_label}\nchoice schema:测试用例预期选项有误")

                if error_log:
                    for line in error_log:
                        try:
                            validate(instance=json.loads(line), schema=expect_error)
                        except ValidationError:
                            self.fail("error_log:异常日志生成结果不符合预期")
                        except SchemaError:
                            self.skipTest(f"{input_label}\nerror schema:测试用例预期异常日志有误")

                if run_log:
                    if len(run_log) > 1:
                        self.fail(f"run_log:运行日志生成数量不符合预期,生成数量:{len(run_log)}")
                    try:
                        validate(instance=json.loads(run_log[0]), schema=expect_run)
                    except ValidationError:
                        self.fail("run_log:运行日志生成结果不符合预期")
                    except SchemaError:
                        self.skipTest(f"{input_label}\nrun schema:测试用例预期运行日志有误")

    def test_03_12(self):
        pass

    def test_03_13(self):
        pass

    def test_03_14(self):
        pass

    def test_03_15(self):
        pass

    def test_03_16(self):
        pass

    def test_03_17(self):
        pass

    def test_03_18(self):
        pass

    def test_03_19(self):
        pass

    def is_sameExist(self,i,j):
            #检验存在性一致
            return bool(i) == bool(j)

    def is_file_empty(self,f):
        #根据查资料这样写好像不会移动文件指针
        return os.fstat(f.fileno()).st_size == 0


if __name__ == "__main__":
    result_path = os.path.join(base_dir,"test","output","unittest_3_5.txt")
    TestCase_objective_unittest.exec_unittest("05",2,result_path)
