"""
3.10 实体关联内容的干扰-覆盖语义鲁棒性

版本迭代情况：
[脱敏] 版本迭代记录
[脱敏] 版本迭代记录
[脱敏] 版本迭代记录
[脱敏] 版本迭代记录

库依赖情况：
无

本组件存在外部依赖和内部依赖
外部依赖：知识图谱:给定实体的三元组目标获取
内部依赖：组件3.21和3.23

配置变量使用情况：
无
"""

import random
from time import time

from src.make_json import make_JSON
# 桩程序,模拟外部依赖。
from src.stack import get_triples_by_frontentity

class RobDisturbEntityAssociated:
    """
        实体关联内容的干扰-覆盖语义鲁棒性

        类变量：
            log_manager：用于管理日志
    """

    def __init__(self,log_manager):
        """
        类初始化函数

        参数：
            log_manager：日志管理类

        返回值：
            无
        """
        self.log_manager = log_manager


    def _find_noun_nodelist(self,knowtree):
        """
        遍历语法树寻找名词属性的叶节点

        参数：
            knowtree：知识语法树

        返回值：
            noun_nodelist：名词属性子节点表
        """
        # 存储满足要求节点的子节点表
        noun_nodelist = []
        # 遍历函数
        def traverse(Node):
            if not Node.get("children") and (Node.get("nodetype") == "NN" or Node.get("nodetype") == "NNS"
                                             or Node.get("nodetype") == "NNP" or Node.get("nodetype") == "NNPS") :
                noun_nodelist.append(Node)
            elif "children" in Node:
                for child in Node["children"]:
                    traverse(child)

        traverse(knowtree)
        return noun_nodelist

    def _make_result_string(self, knowstr,selected_entitynode,associated_triples_list):
        """ 
        字符串构造函数
            
        当前设计的生成模式为，根据知识内容knowstr和三元组(A-B)(AxC)(...)，随机选取一个三元组如(AxC)
        ---> knowstr[0:A_end]+(xC)+knowstr[A_end+1:]
        p.s.：上面用A,B,C...表示实体,-,+,x...表示关系

        参数：
            knowstr：知识内容
            selected_entity：被选中的名词实体所在的节点,传入实体而不是位置方便后续对生成方式进行更改
            associated_triples_list：被过滤与knowstr重复内容后的实体内容关联三元组表

        返回值:
            merge_string：一个组合后的字符串。
        """
        merge_string = ""

        """ 注意：此处为测试用临时代码，知识实体建模过程模块中的部分组件功能完成后需要删改 """
        # 随机在列表中选择一个三元组关系
        rand_index = random.randint(0, len(associated_triples_list) - 1)
        # 为了方便验证结果的正确性，这里加入插桩代码，用以控制rand_index的值。
        # rand_index = 2
        merge_string = associated_triples_list[rand_index]["relation"] + associated_triples_list[rand_index]["endentity"]
        """ END测试用临时代码 """

        # 最后拼接到knowstr上
        end_position = selected_entitynode["end"]
        merge_string = knowstr[0:end_position] + "(" + merge_string + ")" + knowstr[end_position:]
        return merge_string

    def generate_choice(self, knowid, knowstr, knowcata, knowtree):
        """
        生成选项的主函数

        参数：
            knowid：知识唯一标识，一个字符串。
            knowstr：知识描述内容，一个字符串。
            knowcata：知识所在目录唯一标识，一个字符串。
            knowtree：知识语法树，JSON格式。
        
        返回值：
            generate_result：生成的选项JSON列表。

        基本思想：
            1.在知识语法树中找寻名词实体。
            2.对于名词实体，在知识图谱中找寻以它为起点的三元组关系。
            3.剔除掉在知识内容中出现的三元组关系（可以简单比较字符串）。
            4.对3中过滤后的三元组关系，组织生成选项内容，其选项真值（"value"）为真。
            这里可能需要设计若干种匹配模式，目前采用直接在后面使用括号的形式“（关系-实体2）”。
            5.处理知识唯一标识（"knowid"）、知识目录（"knowcata"）属性，构建选项唯一标识（"id"）、选项关联知识（"cataid"）、选项关联指标（"evaluation"）。
            选项唯一标识需要进一步进行设计；选项关联知识和知识目录相同，选项关联指标取语义鲁棒性的对应整数。

        异常处理:
            提示(notice)情况:
                1.随机指定的名词实体，没有对应的三元组关系
            警告(warning)情况:
                1.使用外部依赖时出现异常

        运行日志记录：
            成功生成选项时，将生成选项信息写入运行日志
        """
        # 存储生成的选项列表。虽然只有一个选项生成，但与其他组件保持一致
        generate_result = []        

        # 对当前知识的语法树查找名词实体的叶节点
        noun_nodelist = self._find_noun_nodelist(knowtree)

        # 存储根据实体内容找到的原始关联三元组表
        ori_associated_triples_list = []
        # 存储过滤后的关联三元组表
        filter_associated_triples_list = []

        # 外部依赖异常情况计数
        outer_dependency_error_count = 0

        # 遍历找到第一个在知识图谱有以其为起点的三元组关系且过滤后不为空的名词实体
        for i in range(len(noun_nodelist)):
            noun_nodestring = knowstr[noun_nodelist[i]["start"]:noun_nodelist[i]["end"]]    
            # 通过外部依赖get_triples_by_frontentity得到以所选实体内容为起点的原始关联三元组表
            # 如果外部依赖发生错误，此处写入日志，异常类型是warning，算法继续执行，跳过名词实体
            try :
                ori_associated_triples_list = get_triples_by_frontentity(noun_nodestring)
            except Exception as e:
                outer_dependency_error_count += 1
                self.log_manager.generate_error_log(time(), knowid, "rob_disturb_entityAssociated", "warning", 2, str(e))
                continue
            
            if len(ori_associated_triples_list) != 0:
                # 通过比较字符串对原始关联三元组表进行筛选，过滤掉与knowstr重复的关联三元组关系
                for j in range(0,len(ori_associated_triples_list)):
                    # 一个三元组对应的字符串
                    current_triple = ori_associated_triples_list[j]
                    current_triple_string = current_triple["frontentity"] + current_triple["relation"] + current_triple["endentity"] 
                    # 如果knowstr中不包含这个三元组，则将其添加到过滤后的关联三元组表中
                    if knowstr.find(current_triple_string) == -1: 
                        filter_associated_triples_list.append(ori_associated_triples_list[j])
                if len(filter_associated_triples_list) != 0:       
                    selected_entitynode = noun_nodelist[i]
                    break
        
        # 如果每次调用外部依赖都发生异常，则算法无法进行，直接返回空
        if outer_dependency_error_count == len(noun_nodelist):
            return generate_result

        # 如果遍历完所有名词实体后，没有找到在知识图谱有以其为起点的三元组关系的实体，或者过滤后为空，则直接返回，异常类型是notice
        if len(filter_associated_triples_list) == 0:
            self.log_manager.generate_error_log(time(), knowid, "rob_disturb_entityAssociated", "notice", 6, "随机指定的名词实体，没有对应的三元组关系")
            return generate_result

        # 执行选项生成
        result_string = self._make_result_string(knowstr, selected_entitynode, filter_associated_triples_list)
        generate_result.append(make_JSON(knowid + "1000", result_string, True, 2, knowcata))

        # 运行到最后没有问题，输入到run_log中
        self.log_manager.generate_run_log(time(), knowid, "rob_disturb_entityAssociated", len(generate_result))

        # 返回生成的选项结果
        return generate_result
