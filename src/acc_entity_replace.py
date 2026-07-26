'''
3.4 实体集知识内容替换-覆盖知识准确性

版本迭代情况：
[脱敏] 版本迭代记录
[脱敏] 版本迭代记录
[脱敏] 版本迭代记录
[脱敏] 版本迭代记录

库依赖情况：无

本组件存在外部依赖和内部依赖。
外部依赖：实体库-给定语义相似度范围的实体获取
内部依赖：调用3.3的接口，以及组件3.21、3.23

配置变量使用情况：无
'''
import sys
import os
base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(base_dir)

import random
import time

from src.make_json import make_JSON
from src.log_manager import LogManager

# 桩程序，模拟内部依赖、外部依赖。
from src.stack import get_similar_entity
from src.rely_KG_check import check_KG_consistency

class AccEntityReplace:
    '''
    实体集知识内容替换-覆盖知识准确性

    该类负责随机选取一个实体词汇，调用外部依赖获取语义相似实体列表，
    然后对可能影响三元组关系的替换，调用内部依赖进行一致性校验，
    最后保留校验为False的选项并生成JSON。

    属性：
        log_manager：LogManager实例用于记录错误、运行日志。
    
    '''
    def __init__(self, log_manager):
        '''
        初始化log_manager。

        参数：
            log_manager：日志管理类
        
        返回值：无
        '''
        self.log_manager = log_manager

    def generate_choice(self, knowid, knowstr, knowcata, knowentity, entityrelation):
        ''' 
        生成选项的主函数。

        函数参数：
            knowid：知识唯一标识，一个字符串。
            knowstr：知识描述内容，一个字符串。
            knowcata：知识所在目录唯一标识，一个字符串。
            knowentity：知识的实体集，JSON数组格式，数组中的每个元素包括"entity", "wordtype", "position"。
            entityrelation：知识的三元组，用以判断是否修改了三元组，以及修改三元组时调用内部依赖。
        
        返回值：
            generate_result：生成的选项JSON列表。

        基本思想：
        1. 随机选择结构化知识中的一个实体词汇。
        2. 使用知识实体建模过程模块中的内容，对被选择词汇，在实体库中寻找语义相似度在(0.5， 0.8)范围内的若干个词汇。
        3. 以2中的每个词汇逐个替换原始结构化知识中的实体词汇，每次替换均可以得到新的选项内容（"text"）。
        4. 如果3中的选项存在三元组关系，且实体替换了三元组关系中的词汇，则需要将3中的选项陈述进行基于知识图谱的一致性核查，输入为替换了实体后的三元组关系。
            保留核查结果为False的选项内容，其选项真值（"value"）为假。
        5. 处理知识唯一标识（"knowid"）、知识目录（"knowcata"）属性，构建选项唯一标识（"id"）、选项关联知识（"cataid"）、选项关联指标（"evaluation"）。
        
        异常处理：
            提示(notice)情况：
                1. 输入实体集为空。
            警告(warning)情况：
                1. 外部依赖get_similar_entity异常。
            错误(error)情况：
                1. 内部依赖check_KG_consistency异常。
    
        运行日志记录：
            组件能正常运行完成时，记录一次运行日志，包含knowid、生成选项数量。
        '''

        # 存储生成的选项列表。
        generate_result = []

        # 验证输入实体集
        if self._validate_knowentity(knowid, knowentity) == False:
            return generate_result
        
        # 随机选择一个实体。
        selected_entity = self._select_random_entity(knowentity)

        # 调用外部依赖获取相似实体列表。
        try:
            similar_entity_list = self._get_similar_entities(selected_entity["entity"], knowid)
        except Exception as e:
            self.log_manager.generate_error_log(time.time(), knowid, "acc_entity_replace", "warning", 2, str(e))
            return generate_result

        # 收集相关的三元组。
        related_relations = self._get_related_relations(selected_entity["entity"], entityrelation)
        
        # 处理每个相似实体。
        generate_index = 0 # 存储当前已生成的选项数量，用于创建选项唯一id。
        for similar_entity in similar_entity_list:

            # 得到是否通过一致性验证，False才能进行下一步替换。
            # error错误类型一旦发生直接
            check_result = True
            try:
                check_result = self._check_triple_consistency(related_relations, similar_entity, knowid)
            except Exception as e:
                self.log_manager.generate_error_log(time.time(), knowid, "acc_entity_replace", "error", 3, str(e))
                break
            if check_result == True:
                continue

            # 替换实体。
            target_string = self._replace_entities(knowstr, selected_entity["entity"], similar_entity, knowentity)
            
            # 构建选项。
            generate_result.append(make_JSON(knowid + "04" + str(generate_index).zfill(2), target_string, False, 1, knowcata))
            generate_index += 1

        # 生成运行日志。
        if generate_index > 0:
            self.log_manager.generate_run_log(time.time(), knowid, "acc_entity_replace", generate_index)

        return generate_result

    def _validate_knowentity(self, knowid, knowentity):
        '''
        验证输入实体集是否为空。

        参数：
            knowid：知识唯一标识，一个字符串。
            knowentity：知识的实体集，JSON数组格式，数组中的每个元素包括"entity", "wordtype", "position"。

        返回值：
            一个布尔值，True表示输入实体集不为空，False表示输入实体集为空。
        '''
        # 虽然这种现象很罕见，但如果knowentity为空，直接返回空列表。
        if len(knowentity) == 0:
            self.log_manager.generate_error_log(time.time(), knowid, "acc_entity_replace", "notice", 1, "The knowentity is empty.")
            return False
        return True

    def _select_random_entity(self, knowentity):
        '''
        随机选择一个实体。

        参数：
            knowentity：知识的实体集。

        返回值：    
            selected_entity：随机选择的实体。
        '''
        # 随机选择一个实体。
        rand_index = random.randint(0, len(knowentity) - 1)
        # 为了方便验证结果的正确性，这里加入插桩代码，用以控制rand_index的值。
        # rand_index = 0
        selected_entity = knowentity[rand_index]
        return selected_entity

    def _get_similar_entities(self, selected_entity_string, knowid):
        '''
        对被选择的词汇，调用外部依赖。
        根据外部依赖，其需要三个函数参数：原始实体的字符串，相似度下限（0.5），相似度上限（0.8）；
        返回值是一个列表字符串。

        参数：
            selected_entity_string：被选择的实体字符串。
            knowid：知识唯一标识，一个字符串。

        返回值：
            similar_entity_list：相似实体列表。
        '''
        try:
            similar_entity_list = get_similar_entity(selected_entity_string, 0.5, 0.8)
            return similar_entity_list
        except Exception as e:
            raise ValueError(str(e))
        
    def _get_related_relations(self, selected_entity_string, entityrelation):
        '''
        对entityrelation进行验证，判断其是否与frontentity、relation、endentity三者之一相同。
        如果存在相同，把整个三元组都记录下来,添加到列表same_list_relation中；
        为了节约比较时间，额外准备一个same_list_index整数列表存储其具体与三元组中的哪个元素相同。

        参数：
            selected_entity_string：被选择的实体字符串。
            entityrelation：知识的三元组关系集。

        返回值：
            same_list_relation：与被选择实体相同的三元组列表。
        '''
        same_list_relation = []
        for relation in entityrelation: # 我们没有验证知识三元组关系是否为空，因为如果为空，这个for函数根本不会被执行。
            # 相比之前版本这里简化为append一个元组，元组第一个元素是relation，第二个元素是0、1、2，分别代表frontentity、relation、endentity。
            if relation["frontentity"] == selected_entity_string:
                same_list_relation.append((relation, 0))
            if relation["relation"] == selected_entity_string:
                same_list_relation.append((relation, 1)) 
            if relation["endentity"] == selected_entity_string:
                same_list_relation.append((relation, 2))
        return same_list_relation

    def _check_triple_consistency(self, same_list_relations, similar_entity, knowid):
        '''
        检查相似实体是否存在于知识三元组中。

        参数：
            same_list_relations：与被选择实体相同的三元组列表。
            similar_entity：相似实体。
            knowid：知识唯一标识，一个字符串。

        返回值：
            一个布尔值，True表示相似实体存在于知识的三元组中，False表示相似实体不存在于知识的三元组中。
        '''
        # 本算法只保留核查结果为False的选项。由于最后验证时只有0和非0，因此使用相同实体列表的长度即可。
        # 如果没有相同实体的三元组，那么一致性核查是不需要做的，可以直接进行选项生成。
        if len(same_list_relations) == 0:
            return False
        
        for same_list_relation, same_list_index in same_list_relations:
            try:
                # 使用KG_element存储三元组。
                KG_element = [same_list_relation["frontentity"], same_list_relation["relation"], same_list_relation["endentity"]]
                KG_element[same_list_index] = similar_entity

                if check_KG_consistency(KG_element[0], KG_element[1], KG_element[2]) == False:
                    return False # 只要有一个没被查到，就说明一致性核查不通过，选项陈述为假，可以进行选项生成。

            except Exception as e:
                raise ValueError()
                
                return True # 异常时跳过当前实体。
            
        return True # 如果所有相同实体的三元组都被查到，那么一致性核查通过，选项陈述为真，不进行选项生成。

    def _replace_entities(self, knowstr, selected_entity_string, similar_entity, knowentity):
        '''
        将被选择的实体替换为相似实体，并确保替换后结果必定为假。

        参数：
            knowstr：知识的字符串。
            selected_entity_string：被选择的实体字符串。
            similar_entity：相似实体。
            knowentity：知识的实体集。

        返回值：   
            target_string：替换后的字符串。
        '''
        # 为了保证替换后结果必定为假，我们遍历实体库里的全部实体，替换掉其中存在的所有相同实体。
        same_entity_list = []
        same_entity_len = len(selected_entity_string)
        # 遍历knowentity找到所有与被选实体相同的实体位置。
        for entity in knowentity:
            if entity["entity"] == selected_entity_string:
                same_entity_list.append(entity["position"])

        #（做了性能改进）
        # 确保位置有序。
        same_entity_list.sort()

        temp_part = []  # 存储分割后的字符串。
        last_index = 0  # 记录上一次相同实体的位置。

        for position in same_entity_list:
            # 添加当前位置前的原始字符串。
            temp_part.append(knowstr[last_index:position])
            # 添加替换实体。
            temp_part.append(similar_entity)
            # 更新最后索引位置。
            last_index = position + same_entity_len

        # 添加knowstr中最后剩余的字符串。
        temp_part.append(knowstr[last_index:])
        # 拼接最终字符串。
        target_string = "".join(temp_part)

        return target_string
