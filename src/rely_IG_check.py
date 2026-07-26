'''
3.3 基于推理图谱的一致性核查

版本迭代情况：
[脱敏] 版本迭代记录
[脱敏] 版本迭代记录
[脱敏] 版本迭代记录

库依赖情况：无

本组件存在外部依赖：推理图谱：推理关系存在性检索
无文档依赖

配置变量使用情况：无
'''
import sys
import os
base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(base_dir)

from src.stack import tempstk_inference_consistency

def check_inference_consistency(antecedent, consequent):
    """ 
    检查推理前件和后件关系是否存在于推理图谱中
    
    参数：
        antecedent：字符串，推理前件
        consequent：字符串，推理后件
    
    返回值：
        bool：True表示推理图谱中存在该推理关系，False表示不存在或发生错误
    
    异常处理：
        不捕获异常，直接由调用组件处理
    
    运行日志记录：
        由调用组件实现
    """
    
    # 调用外部依赖
    exist_flag = tempstk_inference_consistency(antecedent, consequent)
    return exist_flag










