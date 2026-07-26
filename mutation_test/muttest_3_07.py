import os
import sys

# [脱敏] 根目录说明
base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(base_dir)

from mutation_test.out_filter import OutFilter
from mutation_test.muttest import MutTest

if __name__ == "__main__":
    
    #记得写好配置文件
    config_path = os.path.join(base_dir,"mutation_test","mut_config","3_07.toml")
    work_db_path = os.path.join(base_dir,"mutation_test","mut_db","3_07.sqlite")
    coverage_json_path = os.path.join(base_dir,"coverage_test","output","rob_stopwords_interference","coverage_3_07.json")
    html_path = os.path.join(base_dir,"mutation_test","output","rob_stopwords_interference","3_07.html")
    survival_dir = os.path.join(base_dir,"mutation_test","output","rob_stopwords_interference","survivals")
    analysis_dir = os.path.join(base_dir,"mutation_test","output","rob_stopwords_interference","LLM_analysis")
    
    # 设置编码环境变量，避免中文输出导致的编码问题
    os.environ['PYTHONIOENCODING'] = 'utf-8'
    
    # 确保输出目录存在，这个放在外部主要是cosmic-ray的函数不便修改
    os.makedirs(os.path.dirname(html_path), exist_ok=True)

    '''变异测试部分'''
    #初始化变异体数据库
    MutTest.init(config_path=config_path,work_db_path=work_db_path,verbosity="INFO")
    #过滤掉未覆盖行的变异体
    OutFilter.uncovered_filter(work_db_path=work_db_path,coverage_json_path=coverage_json_path)
    #执行变异体测试
    MutTest.exec(config_path=config_path,work_db_path=work_db_path,verbosity="INFO")


    '''变异测试结果报告分析部分'''
    #控制台输出变异体测试报告
    MutTest.report(work_db_path=work_db_path,include_incompleted=True)
    #生成变异体测试报告HTML
    MutTest.report_html(work_db_path=work_db_path,html_path=html_path,isOnlySurvived=False,include_incompleted=False,browser_warning=False,open_browser=True)
    #分片生成变异体存活txt文件，无需html，借助数据库生成
    MutTest.survivals_sub_report(work_db_path=work_db_path,survival_dir=survival_dir, skip_success=False)
    #利用大语言模型对变异体存活txt文件进行分析
    # MutTest.LLM_survival_analysis(work_db_path=work_db_path,analysis_dir=analysis_dir)
