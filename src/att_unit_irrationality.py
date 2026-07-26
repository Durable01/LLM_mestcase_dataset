'''
3.30 数值约束的单位极端性检查——覆盖意图语义准确性

版本迭代情况：
[脱敏] 版本迭代记录

库依赖情况：
jsonschema==4.24.0
pandas==2.3.0

本组件存在文档依赖、内部依赖。
文档依赖：不合理单位值表
内部依赖：调用3.21,3.23接口

配置变量使用情况：
UNIT_IRRATIONALITY_TABLE_PATH：不合理单位值表路径
CONSTRAINT_SCHEMA:推理前件 推理后件的schema

'''

import json
import copy
import jsonschema
import random
import pandas as pd
from time import time
from jsonschema import validate
import config.config_choice as cfg_choice
from src.make_json import make_JSON

class AttUnitIrrationality:
    '''对数值约束的单位值进行极端性不合理替换，得到内容为假的选项内容。
    
        属性：
        schema: 从配置文件中加载的JSON schema，用于验证推理结构。
        log_manager: 日志管理类
        path: 不合理单位值表路径
        unit_irrationality_table：从csv文件加载的不合理单位值表
    '''
    def __init__(self, log_manager):
        '''
        类初始化函数
        
        参数：
            log_manager: 日志管理类

        返回值：
        无
        
        异常处理：
        读取文档失败，属于corrupt情况
        '''
        self.schema = json.loads(cfg_choice.CONSTRAINT_SCHEMA)
        self.log_manager = log_manager
        self.path = cfg_choice.UNIT_IRRATIONALITY_TABLE_PATH
        self.unit_irrationality_table = None

        # 初始化时加载不合理单位值表
        try:
            self.unit_irrationality_table = pd.read_csv(self.path)
        except Exception as e:
            # 读取失败时记录corrupt异常，保持unit_irrationality_table为空DataFrame
            self.log_manager.generate_error_log(time(), "system", "att_unit_irrationality", "corrupt", 2, f"加载不合理单位值表失败: {str(e)}")


    def _make_string(self, front, back):
        """
        推理内容形式组织

        参数：
            front：推理前件
            back：推理后件

        返回值：
            result_str：一个符合格式要求的推理内容字符串
        """

        result_str = f"如果{self._cond_to_string(front)}，那么{self._cond_to_string(back)}。"
        return result_str

    def _cond_to_string(self, cond):
        """
        约束条件内容转换为字符串

        参数：
            cond：约束条件。

        返回值：
            cond_str：一个约束条件内容转换后的字符串
        """
        parts = [cond["entity"]]
        if not cond["bool"]:
            parts.append("没有")
        
        constraint = cond["constraint"]
        if "verb" in constraint:
            parts.append(constraint.get("verb", ""))
            parts.append("、".join(constraint["entity"]))
        elif "compare" in constraint:
            compare_map = {
                "large": "大于", "equal": "等于", "below": "小于",
                "largeequal": "大于等于", "notequal": "不等于", "belowequal": "小于等于"
            }
            parts.extend([
                compare_map.get(constraint["compare"], ""),
                f"{constraint['index']}{constraint['unit']}"
            ])
        cond_str = "".join(parts)
        return cond_str

    def validate_inference(self, inference, knowid):
        '''
        验证推理规则是否符合schema，且不为空
        参数：
            inference：推理规则
        返回值：
            validate_index：是否验证通过(True表示验证通过，False表示验证不通过)
        异常处理：
            notice:
                1.知识推理列表为空，或者知识不存在推理列表
                2.jsonschema.exceptions.ValidationError异常
            corrupt:
                1.jsonschema.exceptions.SchemaError异常
        '''
        #用于表示验证是否通过的布尔值
        validate_right = True
        validate_wrong = False
        #验证inference是否合法，前件后件是否存在（notice）
        if not inference or not isinstance(inference, dict):
            self.log_manager.generate_error_log(time(), knowid, "att_unit_irrationality", "notice", 9, "推理内容为空或格式错误")
            return validate_wrong

        if "antecedent" not in inference or "consequence" not in inference:
            self.log_manager.generate_error_log(time(), knowid, "att_unit_irrationality", "notice", 9, "推理内容缺少前件或后件")
            return validate_wrong
                
        # 验证推理前件（corrupt和notice）
        try:
            validate(instance=inference["antecedent"]["cond"], schema=self.schema)
        except jsonschema.exceptions.SchemaError as e:
            # jsonschema.exceptions.SchemaError异常，属于corrupt情况
            self.log_manager.generate_error_log(time(), knowid, "att_unit_irrationality", "corrupt", 1, str(e))
            return validate_wrong
        except jsonschema.exceptions.ValidationError as e:
            # jsonschema.exceptions.ValidationError异常，属于notice情况
            self.log_manager.generate_error_log(time(), knowid, "att_unit_irrationality", "notice", 9, str(e))
            return validate_wrong

        # 验证推理后件（corrupt和notice）
        try:
            validate(instance=inference["consequence"]["cond"], schema=self.schema)
        except jsonschema.exceptions.SchemaError as e:
            # jsonschema.exceptions.SchemaError异常，属于corrupt情况
            self.log_manager.generate_error_log(time(), knowid, "att_unit_irrationality", "corrupt", 1, str(e))
            return validate_wrong
        except jsonschema.exceptions.ValidationError as e:
            # jsonschema.exceptions.ValidationError异常，属于notice情况
            self.log_manager.generate_error_log(time(), knowid, "att_unit_irrationality", "notice", 9, str(e))
            return validate_wrong

        return validate_right

    def _get_replace_value(self, unit):
        '''
        在不合理单位值表中查找单位对应的不合理范围，并生成一个不合理值
        参数：
            unit：单位
        返回值：
            不合理值
        异常处理：
            无
        '''
        if (self.unit_irrationality_table.empty) or (unit not in self.unit_irrationality_table["unit"].values):
            return None
        replace_unit_compare = self.unit_irrationality_table[self.unit_irrationality_table["unit"] == unit]["compare"].values[0]
        replace_unit_index = float(self.unit_irrationality_table[self.unit_irrationality_table["unit"] == unit]["index"].values[0])

        #用于边界不包含情况使用(保留两位小数情况，故设置为0.01)
        epsilon = 0.01
        result = None
        #根据compare类型生成不合理值
        if replace_unit_compare == "belowequal":
            result = random.uniform(replace_unit_index - 10,replace_unit_index)
        elif replace_unit_compare == "below":
            result = random.uniform(replace_unit_index - 10,replace_unit_index - epsilon)
        elif replace_unit_compare == "largeequal":
            result = random.uniform(replace_unit_index,replace_unit_index + 10)
        elif replace_unit_compare == "large":
            result = random.uniform(replace_unit_index + epsilon,replace_unit_index + 10)
        elif replace_unit_compare == "equal":
            result = replace_unit_index
        elif replace_unit_compare == "notequal":
            result = random.uniform(replace_unit_index - 10,replace_unit_index - epsilon)#这里向下取值，也可以用其他方法
        #对生成的随机数保留两位小数
        result = float(f"{result:.2f}")
        #如果生成的结果实际对应是整数（如5.00），则取整输出
        if abs(result - round(result)) < (10e-5):
            result = round(result)
        return result


    def generate_choice(self, knowid,knowstr, knowcata, inference):
        '''
        选项生成函数

        参数：
            knowid：知识唯一标识
            knowcata：知识目录标识
            inference：推理规则

        返回值：
            generate_result：一个列表，列表中的每个元素为一个满足选项schema的JSON
        
        异常处理：
            notice：
                1.知识列表没有数值约束
                2.数值约束中的单位在不合理单位值表中无法查到
                (应文档要求，type分别是 (11,17)
        运行日志记录：
            成功生成选项时，将生成选项信息写入运行日志
        '''
        generate_result = []
        #验证推理规则是否符合schema，且不为空
        if not self.validate_inference(inference, knowid):
            return generate_result

        #验证推理前件和后件是否存在数值约束
        has_antecedent_constraint = "compare" in inference["antecedent"]["cond"]["constraint"]
        has_consequence_constraint = "compare" in inference["consequence"]["cond"]["constraint"]
        # 知识推理列表没有数值约束，属于notice情况
        if not has_antecedent_constraint and not has_consequence_constraint:
            self.log_manager.generate_error_log(time(), knowid, "att_unit_irrationality", "notice", 11, "知识推理列表没有数值约束。")
            return generate_result

        #对数值约束中的单位在不合理单位值表中进行查找,存在的情况下获取替换值
        ante_replace_value = None
        cons_replace_value = None
        if has_antecedent_constraint:
            ante_unit = inference["antecedent"]["cond"]["constraint"]["unit"]
            ante_replace_value = self._get_replace_value(ante_unit)

        if has_consequence_constraint:
            cons_unit = inference["consequence"]["cond"]["constraint"]["unit"]
            cons_replace_value = self._get_replace_value(cons_unit)

        
        if not ante_replace_value and not cons_replace_value:
            self.log_manager.generate_error_log(time(), knowid, "att_unit_irrationality", "notice", 17, "前后件的单位在不合理单位表中均无法查到")
            return generate_result
        if not ante_replace_value and has_antecedent_constraint:
            self.log_manager.generate_error_log(time(), knowid, "att_unit_irrationality", "notice", 17, "前件的单位" + ante_unit + "在不合理单位表找不到")
        if not cons_replace_value and has_consequence_constraint:
            self.log_manager.generate_error_log(time(), knowid, "att_unit_irrationality", "notice", 17, "后件的单位" + cons_unit + "在不合理单位表找不到")

        #替换数值约束中的单位值
        option_text_list = []
        if ante_replace_value:
            new_ante = copy.deepcopy(inference["antecedent"]["cond"])
            new_ante["constraint"]["index"] = ante_replace_value
            new_ante["constraint"]["compare"] = "equal"
            option_text = self._make_string(new_ante, inference["consequence"]["cond"])
            option_text_list.append(option_text)
        if cons_replace_value:
            new_cons = copy.deepcopy(inference["consequence"]["cond"])
            new_cons["constraint"]["index"] = cons_replace_value
            new_cons["constraint"]["compare"] = "equal"
            option_text = self._make_string(inference["antecedent"]["cond"], new_cons)
            option_text_list.append(option_text)
        '''
        组织成JSON。
        '''
        for i in range(0, len(option_text_list)):
            generate_result.append(make_JSON(knowid + "30" + str(i).zfill(2), option_text_list[i], False, 13, knowcata))

        #如果运行到最后没有问题，就写入运行日志
        self.log_manager.generate_run_log(time(), knowid, "att_unit_irrationality", len(generate_result))

        return generate_result



