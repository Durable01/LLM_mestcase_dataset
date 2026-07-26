import os
import sys
import subprocess
import webbrowser
import tkinter.messagebox as messagebox
from itertools import chain
import datetime

# [脱敏] 根目录说明
base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(base_dir)
from mutation_test.references.work_db import WorkDB, use_db
from mutation_test.references.work_item import TestOutcome

from src.call_LLM import call_LLM

class MutTest:
    @staticmethod
    def init(config_path:str,work_db_path:str,verbosity:str = None):
        '''初始化变异体数据库,这个过程会生成变异体，并将其写入变异体数据库
        '''
        MutTest.delete_file_if_exists(work_db_path)
        if bool(verbosity) :
            subprocess.run(['cosmic-ray',"--verbosity",verbosity, 'init', config_path, work_db_path])
        else:
            subprocess.run(['cosmic-ray', 'init', config_path, work_db_path])
        pass
    @staticmethod
    def exec(config_path:str,work_db_path:str,verbosity:str = None):
        '''运行变异体测试，这个过程会读取变异体数据库，并执行变异体测试
        '''
        #环境变量设置
        os.environ['MUTATION_TEST'] = '1'
        env = dict(os.environ)
        if bool(verbosity) :
            subprocess.run(['cosmic-ray',"--verbosity",verbosity, 'exec', config_path, work_db_path],
            env=env
            )
        else:
            subprocess.run(['cosmic-ray', 'exec', config_path, work_db_path],
            env=env)
        pass

    @staticmethod
    def report(work_db_path:str,include_incompleted:bool = False):
        '''读取指定路径的变异体数据库内容，并以报告的形式输出到控制台
        '''
        if bool(include_incompleted) :
            subprocess.run(['cr-report','--show-pending', work_db_path])
        else:
            subprocess.run(['cr-report', work_db_path])
        pass

    @staticmethod
    def report_html(work_db_path:str,html_path:str,isOnlySurvived:bool = True,include_incompleted:bool = False,browser_warning:bool = True,open_browser:bool = True):
        '''读取指定路径的变异体数据库内容，并以HTML的形式输出到指定路径
        '''

        with open(html_path, "w",encoding="utf-8") as f:
            if bool(isOnlySurvived) and bool(include_incompleted) :
                subprocess.run(['cr-html', '--skip-success', '--not-only-completed', work_db_path],
                stdout=f,text=True)
            elif bool(isOnlySurvived) :
                subprocess.run(['cr-html', '--skip-success', '--only-completed', work_db_path],
                stdout=f,text=True)
            elif bool(include_incompleted) :
                subprocess.run(['cr-html', '--include-success', '--not-only-completed', work_db_path],
                stdout=f,text=True)
            else:
                subprocess.run(['cr-html', '--include-success', '--only-completed', work_db_path],
                stdout=f,text=True)
            pass
        if open_browser:
            if browser_warning:
                messagebox.showwarning("警告", "建议使用Chrome浏览器打开HTML报告(此消息可设置参数browser_warning=False来关闭)")
            webbrowser.open(os.path.abspath(html_path))
    
    @staticmethod
    def delete_file_if_exists(file_path):
        """
        如果文件存在则删除，不存在也不报错
        """
        if os.path.exists(file_path) and os.path.isfile(file_path):
            try:
                os.remove(file_path)
                print(f"file {file_path} deleted")
                return True
            except Exception as e:
                print(f"delete file {file_path} failed: {e}")
                return False
        else:
            print(f"file {file_path} not exists or not a file")
            return False
    @staticmethod
    def survivals_sub_report(work_db_path,survival_dir:str, skip_success:bool = False):
        #确保生存目录存在
        os.makedirs(survival_dir, exist_ok=True)
        """生成变异体存活txt文件，并保存到指定目录"""
        with use_db(work_db_path, WorkDB.Mode.open) as db:

            all_items = db.completed_work_items

            #生成全部变异体列表
            all_items = db.completed_work_items
            #对每个存活的变异体生成变异内容txt文件
            for index, (work_item, result) in enumerate(all_items, start=1):
                if result is not None:
                    if not result.is_killed:
                        for mutation in work_item.mutations:
                            survival_path = os.path.join(survival_dir, f"{work_item.job_id}.txt")
                            if result.diff:
                                with open(survival_path, "w", encoding="utf-8") as f:
                                    f.write(f"Survival Job ID: {work_item.job_id}\n")
                                    f.write(f"worker outcome: {result.worker_outcome}\n")
                                    f.write(f"test outcome: {result.test_outcome}\n")
                                    f.write(f"Operator: {mutation.operator_name}\n")
                                    f.write(f"Occurrence: {mutation.occurrence}\n")
                                    f.write(f"Module Path: {mutation.module_path} Start Pos: {mutation.start_pos} End Pos: {mutation.end_pos}\n")
                                    f.write(f"Diff: {result.diff}\n")
    
    @staticmethod
    def LLM_survival_analysis(work_db_path:str,analysis_dir:str):
        """利用大语言模型对变异体存活txt文件进行分析"""
        #确保分析结果存放目录存在，这个目录用来存放大语言模型分析结果的txt文件
        os.makedirs(analysis_dir, exist_ok=True)
        #模板提示词
        base_prompt = "下面是在变异测试过程中存活的一段代码的变异体,其中变异部分已确认测试覆盖,观察此存活变异体信息,并给出分析结果和建议"
        #读取变异体存活txt文件
        with use_db(work_db_path, WorkDB.Mode.open) as db:
            #生成全部变异体列表
            all_items = db.completed_work_items
            #对每个存活的变异体生成变异内容txt文件
            for index, (work_item, result) in enumerate(all_items, start=1):
                if result is not None:
                    if not result.is_killed:
                        for mutation in work_item.mutations:
                            analysis_path = os.path.join(analysis_dir, f"{work_item.job_id}.txt")
                            os.makedirs(os.path.dirname(analysis_path), exist_ok=True)
                            if result.diff:
                                LLM_prompt = base_prompt + f"\n\n变异体存活改动内容: {result.diff}"
                                print(f"[{datetime.datetime.now().strftime("%d/%m/%Y %H:%M:%S")}]正在分析变异体: {work_item.job_id}\n")
                                LLM_answer = call_LLM(LLM_prompt)
                                print(f"变异体{work_item.job_id}分析完毕\n")
                                with open(analysis_path, "w", encoding="utf-8") as f:
                                    f.write(f"===================Survival Mutation Info:===========================\n")
                                    f.write(f"Survival Job ID: {work_item.job_id}\n")
                                    f.write(f"worker outcome: {result.worker_outcome}\n")
                                    f.write(f"test outcome: {result.test_outcome}\n")
                                    f.write(f"Operator: {mutation.operator_name}\n")
                                    f.write(f"Occurrence: {mutation.occurrence}\n")
                                    f.write(f"Module Path: {mutation.module_path} Start Pos: {mutation.start_pos} End Pos: {mutation.end_pos}\n")
                                    f.write(f"Diff: {result.diff}\n")
                                    f.write("===================LLM Analysis Result:===========================\n")
                                    f.write(LLM_answer)


