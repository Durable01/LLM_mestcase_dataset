import json
import os
from pickle import GLOBAL

'''
3-10使用，OUTER_DEPENDENCIES_WARNING获取对应三元组失败
OUTER_DEPENDENCIES_NOTICE 直接返回空集
'''
OUTER_DEPENDENCIES_NOTICE= False
OUTER_DEPENDENCIES_WARNING = False


'''
3-9使用 调用内部依赖3-2发生错误
'''
GET_ENTITES_ERROR=False

'''
调用cnsyn库发生错误
'''
GET_cnsyn_CORRUPT=False
'''

获取相似实体时发生错误
'''
GET_SIMILAR_ENTITIES_ERROR=False

'''
3-4使用，CHECK_KG_CONSISTENCY_number=1用于标识第几次调用桩程序发生错误，
CHECK_KG_CONSISTENCY_ERROR标识这一次是否发生错误
'''
CHECK_KG_CONSISTENCY_number=1
CHECK_KG_CONSISTENCY_ERROR1=False
CHECK_KG_CONSISTENCY_ERROR2=False


# 全局变量区。这一区域初始是有正常的默认值的，测试用例会调整该区域的全局变量值以实现测试的目的。

# 用于tempstk_inference_consistency函数的返回值，对应3.17的内部依赖、3.3的桩程序。
TEMPSTK_INFERENCE_CONSISTENCY_RETURN = True

# 用于tempstk_inference_consistency函数是否抛出异常，对应3.17的内部依赖、3.3的桩程序。
TEMPSTK_INFERENCE_CONSISTENCY_ERROR = False

# 用于get_n_step_consequence的n参数，对应3.18的桩程序。
GET_N_STEP_CONSEQUENCE_N_2 = [
            {
                "cond": {
                    "entity": "placeholder_entity",  # [脱敏] 原始数据涉及商业机密
                    "bool": True,
                    "constraint": {
                        "compare": "belowequal",
                        "index": 1,
                        "unit": "placeholder_unit",  # [脱敏] 原始数据涉及商业机密
                    },
                },
            },
        ]

# 用于get_n_step_consequence的n参数，对应3.18的桩程序。
GET_N_STEP_CONSEQUENCE_N_3 = [
            {
                "cond": {
                    "entity": "placeholder_entity",  # [脱敏] 原始数据涉及商业机密
                    "bool": False,
                    "constraint": {
                        "compare": "large",
                        "index": 1,
                        "unit": "placeholder_unit",  # [脱敏] 原始数据涉及商业机密
                    },
                },
            },
        ]

# 用于get_n_step_consequence是否抛出异常，对应3.18的桩程序。
GET_N_STEP_CONSEQUENCE_ERROR = False

# 用于get_parallel_head是否抛出异常，对应3.25-3.27的桩程序。
GET_PARALLEL_HEAD_ERROR = False

def has_entity_true(entity: str, pos: str) -> bool:
    "桩程序"
    "手动模拟实体库是否存在实体"
    if GET_ENTITES_ERROR:
        raise Exception()
    return True

def has_entity_false(entity: str, pos: str) -> bool:
    "桩程序"
    "手动模拟实体库是否不存在实体"
    if GET_ENTITES_ERROR:
        raise Exception()
    return False

def inference_consistency(antecedent, consequent):
    """
    3.3推理图谱一致性核查桩程序
    参数：
        antecedent：推理前件
        consequent：后件
    返回值：
        bool值：True表示存在，False不存在。
    """
    # 手动改True/False来模拟两情况
    return False

def tempstk_inference_consistency(antecedent, consequent):
    """
    3.3的临时桩程序
    这里仅临时对3.3测试程序配套写一个桩程序(temp stack)：
    如果前件的entity含"仪器仪表"且后件的entity含"绝缘电阻"则返回 True，否则 False。
    """
    
    global TEMPSTK_INFERENCE_CONSISTENCY_RETURN
    global TEMPSTK_INFERENCE_CONSISTENCY_ERROR
    
    if TEMPSTK_INFERENCE_CONSISTENCY_ERROR == True:
        raise ValueError("Testcase give you an error! Bad luck ToT")

    return TEMPSTK_INFERENCE_CONSISTENCY_RETURN

def get_similar_entity(entity, cosine_lower, cosine_upper):
    '''
    3.5测试桩程序
    返回与给定实体在KG中相似度在(cosine_lower, cosine_upper)范围内的实体列表
    '''
    if GET_SIMILAR_ENTITIES_ERROR==True:
        raise Exception()
    raw_list = ["相似实体1", "相似实体2", "相似实体3"]
    result = []
    for item in raw_list:
        json_str = json.dumps(item, ensure_ascii=False)
        result.append(json.loads(json_str))
    return result

def inference_consistency(cond_front, cond_back):
    '''测试桩程序。
    '''
    return False

def get_n_step_consequence(cond, n):
    '''测试桩程序。
    '''
    global GET_N_STEP_CONSEQUENCE_ERROR
    global GET_N_STEP_CONSEQUENCE_N_2
    global GET_N_STEP_CONSEQUENCE_N_3
    
    if GET_N_STEP_CONSEQUENCE_ERROR == True:
        raise ValueError("Testcase give you an error! Bad luck ToT")
    if n==2:
        dict_test = GET_N_STEP_CONSEQUENCE_N_2
    elif n==3:
        dict_test = GET_N_STEP_CONSEQUENCE_N_3
    list_test = []
    for dict_test in dict_test:
        json_str = json.dumps(dict_test, ensure_ascii=False, indent=4)
        list_test.append(json.loads(json_str))
    return list_test
    #return []

def get_similar_entity(entity, cosine_lower, cosine_upper):
    ''' 返回相似实体的桩程序。
    '''
    if GET_SIMILAR_ENTITIES_ERROR==True:
        raise Exception()
    similar_list = []
    similar_list.append("相似实体1")
    similar_list.append("相似实体2")
    return similar_list

stack_execute_time = 0

def check_relation(entity_front, relation, entity_back):
    ''' 返回知识图谱关系验证结果的桩程序。
    '''
    global stack_execute_time
    if stack_execute_time == 0:
        stack_execute_time = 1
        return True
    else:
        return False
    
stack_question_list = [0, 0, 0, 0]
def construct_question(question_type, choice_list, catalog):
    '''
    题目生成桩程序。
    '''
    global stack_question_list
    stack_question_list[question_type] = stack_question_list[question_type] + 1
    with open("test" + os.sep + "test_result_2.txt", "a+", encoding = "UTF-8") as f:
        f.write(str(question_type) + "\n")
        for i in range(0, len(choice_list)):
            f.write("\t")
            f.write(json.dumps(choice_list[i], ensure_ascii=False, separators=(',', ':')))
            f.write("\n")
        f.write(catalog + "\n")
    return 0

def get_triples_by_frontentity(frontentity_string):
    if OUTER_DEPENDENCIES_NOTICE==True:
        return []

    if OUTER_DEPENDENCIES_WARNING==True:
        raise Exception()
        return []
    '''
    根据front获取给定实体的三元组
    '''
    if frontentity_string == "placeholder_entity_a":  # [脱敏] 原始数据涉及商业机密
        return [
        {"frontentity": "placeholder_entity_a", "relation": "placeholder_rel_a", "endentity": "placeholder_entity_b"},  # [脱敏]
        ]
    
    elif frontentity_string == "placeholder_entity_c":  # [脱敏] 原始数据涉及商业机密
        return [
        {"frontentity": "placeholder_entity_c", "relation": "placeholder_rel_b", "endentity": "placeholder_desc_a"},  # [脱敏]
        {"frontentity": "placeholder_entity_c", "relation": "placeholder_rel_c", "endentity": "placeholder_desc_b"},  # [脱敏]
        {"frontentity": "placeholder_entity_c", "relation": "placeholder_rel_b", "endentity": "placeholder_desc_c"},  # [脱敏]
    ]
    else:
        return []
    
def test_stub_true():
    '''
    返回True的桩程序
    '''
    return True

def test_stub_false():
    '''
    返回False的桩程序
    '''
    return False

def KG_check(entriy_front,relation,entriy_after):
    '''
    由于知识实体建模过程的接口尚未接入，
    先以桩程序进行测试
    '''
    global CHECK_KG_CONSISTENCY_number
    if CHECK_KG_CONSISTENCY_number==1:
        CHECK_KG_CONSISTENCY_number = CHECK_KG_CONSISTENCY_number + 1
        if CHECK_KG_CONSISTENCY_ERROR2==True:
            raise Exception()
    else:
        CHECK_KG_CONSISTENCY_number = CHECK_KG_CONSISTENCY_number - 1
        if CHECK_KG_CONSISTENCY_ERROR1==True:
            raise Exception()

    return False

def get_parallel_head(knowstr, parallelrelation):
    '''
    对应3.24组件的桩程序。
    属性：
        需要结构化知识的知识内容、并置关系，即knowstr、parallelrelation。
    返回值：
        一个字符串，表示提取到的并置关系头。
    '''

    global GET_PARALLEL_HEAD_ERROR
    if GET_PARALLEL_HEAD_ERROR == True:
        raise ValueError("Testcase give you an error! Bad luck ToT")
    return_string = "桩程序给的并置关系头"
    return return_string