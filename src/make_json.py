"""
3.21 JSON格式组织

版本迭代情况：
[脱敏] 版本迭代记录

库依赖情况：
无

本组件无外部依赖、内部依赖、文档依赖。

配置变量使用情况：
无
"""

import json

def make_JSON(id, text, value, evaluation, cataid):
    """ 生成符合格式要求的JSON对象并返回

    参数：
        id：选项的唯一标识，格式为原知识id+两位数组件编号（04~19）+两位数本次生成题目编号（00~99）组成的字符串。
        text：选项内容，一个字符串。
        value: 选项真值，True或者False。
        evaluation: 评价指标，一个整数，按顺序为知识准确性1，语义鲁棒性2，一致性3，条件敏感性4，推理可靠性5。
        cataid:  选项对应的知识目录，一个字符串。

    返回值：
        json_object：一个JSON格式对象。

    异常处理：
        无

    运行日志记录：
        该组件无需输出日志信息。
    """

    # 1. 为该选项创建一个空字典。
    option_dict = {}

    # 2. 将各个字段内容添加到字典中。
    option_dict['id'] = id
    option_dict['text'] = text
    option_dict['value'] = value
    option_dict['evaluation'] = evaluation
    option_dict['cataid'] = cataid

    # 3. 利用json.dumps函数和json.loads函数，将字典转换为JSON对象格式。
    json_string = json.dumps(option_dict, ensure_ascii=False, indent=4)
    json_object = json.loads(json_string)

    # 4. 返回该JSON对象。
    return json_object