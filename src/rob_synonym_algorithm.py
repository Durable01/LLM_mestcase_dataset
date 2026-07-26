"""
3.9近义词替换算法核心实现
实现基于近义词替换的知识语义鲁棒性测试算法

版本迭代情况
[脱敏] 版本迭代记录
[脱敏] 版本迭代记录
[脱敏] 版本迭代记录
[脱敏] 版本迭代记录

库依赖情况：
scikit_learn==1.2.2
joblib==1.5.1
whoosh==2.7.4
numpy==1.26.4

本组件存在内部依赖和外部依赖：
内部依赖：3.2组件rely_ES_check，3.21组件make_json,3.23组件log_manager。
外部依赖：1.2.0版本cnsyn库

配置变量使用情况：
无
"""
import random
import time
import cnsyn
from src.make_json import make_JSON
from src.rely_ES_check import check_entity_consistency


class RobSynonymAlgorithm:
    """近义词替换算法核心类"""
    
    def __init__(self, log_manager):
        """
        初始化近义词替换算法
        需要传递log_manager参数用于日志管理
        """
        self.log_manager = log_manager
        self.componentid = "rob_synonym_algorithm"
    
    def generate_choice(self,knowid,knowstr,knowcata,knowentity):
        """
        基本功能：
            基于给定的knowid，knowstr,knowcata,knowentity，随机选择knowentity中的实体，生成其实体的近义词选项

        函数参数：
            knowid：知识唯一标识，一个字符串。
            knowstr：知识描述内容，一个字符串。
            knowcata：知识所在目录唯一标识，一个字符串。
            knowentity：知识的实体集，JSON数组格式，数组中的每个元素包括"entity", "wordtype", "position"。
            
        返回值：
            options：返回的选项JSON列表

        异常处理：
            notice：随机指定的实体，其近义词不存在。
            error:使用内部依赖时出现异常。
            corrupt:cnsyn库抛出异常。
        
        运行日志记录：
            成功生成选项时，将生成选项时间、知识唯一标识、类名称（组件标识）、选项生成个数写入运行日志
            
        实现基本思想：
        1. 在知识实体中随机选择一个实体
        2. 利用中文同义词查询工具，对被选择实体查找近义词
        3. 对每个近义词，在与实体词性相同的实体库中查找是否存在实体；只保留结果为False的近义词
        4. 对过滤后的近义词生成选项内容，其选项真值（"value"）为真
        5. 处理知识唯一标识等属性，构建完整选项
        """
        #选项列表
        options=[]

        #如果实体集为空，直接返回空列表
        if len(knowentity)==0:
            return options
            
        #步骤一：随机选择一个实体
        rand_index = random.randint(0, len(knowentity) - 1)
        selected_entity = knowentity[rand_index]

        #步骤二：利用cnsyn库，查找近义词
        selected_entity_string = selected_entity["entity"]
        synonyms = []
        try:
            synonyms = cnsyn.search(selected_entity_string)
            if synonyms:
                synonyms = synonyms[:5]  # 限制返回5个近义词
            else:
                synonyms = []
        except Exception as e:
            # cnsyn库异常，记录corrupt日志
            self.log_manager.generate_error_log(time.time(),knowid,self.componentid,"corrupt",3, str(e))
            return options

        #步骤三：在实体库中查找是否存在实体
        """
            此步骤需要调用内部依赖，组件3.2
            只保留返回值为False的近义词
        """
        filtered_synonyms = []
        pos_code = selected_entity["wordtype"]
        for synonym in synonyms:
            try:
                # 调用entity_consistency_check组件检查实体是否存在
                if not check_entity_consistency(synonym, [pos_code]):
                    filtered_synonyms.append(synonym)
            except Exception as e:
                # 使用内部依赖时出现异常，记录error日志并抛出异常
                self.log_manager.generate_error_log(time.time(),knowid,self.componentid,"error",3,f"调用实体一致性检查组件异常: {str(e)}")
                return options
        #判断是否有近义词
        """
        虽然cnsyn库可能正常运行，但如果没有近义词返回，也属于需要进行异常与错误的输出
        不放在过滤这一步之前是因为，如果近义词为空，这个循环不会运行，所以直接在过滤后统一检查是否有近义词，减少代码量
        """
        if not filtered_synonyms :
            self.log_manager.generate_error_log(time.time(),knowid,self.componentid,"notice",5,"没有近义词")
            return options
        #步骤四、五：生成选项
        """
        过滤后选项真值为真
        鲁棒性为2
        """
        for synonym in filtered_synonyms:
            # 根据实体位置信息替换文本
            entity_text = selected_entity["entity"]
            start_pos = selected_entity["position"]
            end_pos = start_pos + len(entity_text)
            
            # 替换文本中的实体
            new_text = knowstr[:start_pos] + synonym + knowstr[end_pos:]
            
            # 构建选项
            option=make_JSON(knowid,new_text,True,2,knowcata)

            #添加到选项列表
            options.append(option)   

         #若运行到最后没有问题，则记录在运行日志中
        self.log_manager.generate_run_log(time.time(), knowid, self.componentid, len(options))

        return options   

