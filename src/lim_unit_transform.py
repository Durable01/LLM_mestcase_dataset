"""
3.15 单位换算的数值条件变动

版本迭代情况：
[脱敏] 版本迭代记录
[脱敏] 版本迭代记录
[脱敏] 版本迭代记录
[脱敏] 版本迭代记录
[脱敏] 版本迭代记录

库依赖情况：
jsonschema==4.24.0
pandas==2.3.0

本组件存在文档依赖和内部依赖。
文档依赖：单位换算表
内部依赖：调用3.21,3.23接口

配置变量使用情况：
UNIT_TABLE_PATH:文档依赖的单位表保存地址
CONSTRAINT_SCHEMA:推理前件 推理后件的schema
"""

import json
import copy
import jsonschema
import pandas as pd
from time import time
from jsonschema import validate
from config.config_choice import UNIT_TABLE_PATH
from config.config_choice import CONSTRAINT_SCHEMA
from src.make_json import make_JSON
from src.log_manager import LogManager

class LimUnitTransform:
    """ 对数值约束的数值、单位按照换算规则同时进行更改，得到内容为真的选项内容。

        属性：
            schema: 从配置文件中加载的JSON schema，用于验证推理结构。
            log_manager: 日志管理类
            path: 单位换算表路径
            unit_table：从csv文件加载的单位换算表
    """

    def __init__(self, log_manager):
        """
        类初始化函数

        参数：
            log_manager: 日志管理类

        返回值：
            无

        异常处理：
            读取文档失败，属于corrupt情况
        """
        self.schema = json.loads(CONSTRAINT_SCHEMA)
        self.log_manager = log_manager
        self.path = UNIT_TABLE_PATH
        self.unit_table = None

        # 初始化时加载单位换算表
        try:
            self.unit_table = pd.read_csv(self.path)
        except Exception as e:
            # 读取失败时记录corrupt异常，保持unit_table为空DataFrame
            self.log_manager.generate_error_log(time(), "system", "lim_unit_transform", "corrupt", 2, f"加载单位换算表失败: {str(e)}")

    def _get_unit_type(self, unit):
        """
        获取单位类型

        参数：
            unit：知识内容中的单位。

        返回值：
            unit_type：一个匹配到的单位类型字符串，如果没有匹配则返回None
        """
        if self.unit_table.empty:
            unit_type = None
        else:
            matches = self.unit_table[self.unit_table["unit"] == unit]
            unit_type = matches["type"].values[0] if not matches.empty else None
        return unit_type

    def _convert_unit(self, cond):
        """
        执行单位换算

        参数：
            cond：约束条件。

        返回值：
            converted_units：一个包含可转换单位和换算后对应值的字典，如果无法转换则返回None
        """
        if self.unit_table.empty:
            return None

        original_unit = cond["constraint"]["unit"]
        original_value = cond["constraint"]["index"]
        unit_type = self._get_unit_type(original_unit)
        
        if not unit_type:
            return None
            
        same_type_units = self.unit_table[self.unit_table["type"] == unit_type]
        if same_type_units.empty:
            return None
            
        base_ratio = self.unit_table[self.unit_table["unit"] == original_unit]["ratio"].values[0]

        converted_units = {}
        for _, row in same_type_units.iterrows():
            if row["unit"] != original_unit:
                converted_value = int(original_value * (row["ratio"] / base_ratio))
                converted_units[row["unit"]] = converted_value
        return converted_units

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

    def generate_choice(self, knowid, knowstr, knowcata, inference):
        """
        选项生成函数

        参数：
            knowid：知识唯一标识。
            knowstr：知识内容。
            knowcata：知识所在的目录，指向目录节点的唯一标识。
            inference：本条知识包含的推理逻辑。
            antecedent_converted:存储antecedent的单位转换结果
            consequence_converted:存储consequence的单位转换结果
            (用于生成两种情况的选项)
                
        返回值：
            generate_result：一个列表，列表中的每个元素为一个满足选项schema的JSON。

        异常处理：
            提示(notice)情况：
                1.知识推理列表没有数值约束
                2.数值约束中的单位在单位换算表中无法查到
                3.jsonschema.exceptions.ValidationError异常;知识推理列表为空，或者知识不存在推理列表
                (应文档要求，type分别是11，13，9)
                    
            崩溃(corrupt)情况：
                1.jsonschema.exceptions.SchemaError异常
                2.读取文件抛出异常

        运行日志记录：
            成功生成选项时，将生成选项信息写入运行日志。
        """
        generate_result = []
        validate_index = False
         
        #验证inference是否合法，前件后件是否存在（notice）
        if not inference or not isinstance(inference, dict):
            self.log_manager.generate_error_log(time(), knowid, "lim_unit_transform", "notice", 9, "推理内容为空或格式错误")
            return generate_result

        if "antecedent" not in inference or "consequence" not in inference:
            self.log_manager.generate_error_log(time(), knowid, "lim_unit_transform", "notice", 9, "推理内容缺少前件或后件")
            return generate_result
                
        # 验证推理前件（corrupt和notice）
        try:
            validate(instance=inference["antecedent"]["cond"], schema=self.schema)
        except jsonschema.exceptions.SchemaError as e:
            # jsonschema.exceptions.SchemaError异常，属于corrupt情况
            self.log_manager.generate_error_log(time(), knowid, "lim_unit_transform", "corrupt", 1, str(e))
            validate_index = True
        except jsonschema.exceptions.ValidationError as e:
            # jsonschema.exceptions.ValidationError异常，属于notice情况
            self.log_manager.generate_error_log(time(), knowid, "lim_unit_transform", "notice", 11, str(e))
            validate_index = True

        if validate_index:
            return generate_result

        # 验证推理后件（corrupt和notice）
        try:
            validate(instance=inference["consequence"]["cond"], schema=self.schema)
        except jsonschema.exceptions.SchemaError as e:
            # jsonschema.exceptions.SchemaError异常，属于corrupt情况
            self.log_manager.generate_error_log(time(), knowid, "lim_unit_transform", "corrupt", 1, str(e))
            validate_index = True
        except jsonschema.exceptions.ValidationError as e:
            # jsonschema.exceptions.ValidationError异常，属于notice情况
            self.log_manager.generate_error_log(time(), knowid, "lim_unit_transform", "notice", 11, str(e))
            validate_index = True

        if validate_index:
            return generate_result

        # 知识推理列表没有数值约束，属于notice情况
        has_antecedent_constraint = "compare" in inference["antecedent"]["cond"]["constraint"]
        has_consequence_constraint = "compare" in inference["consequence"]["cond"]["constraint"]

        if not has_antecedent_constraint and not has_consequence_constraint:
            self.log_manager.generate_error_log(time(), knowid, "lim_unit_transform", "notice", 11, "知识推理列表没有数值约束。")
            return generate_result
            
        # 数值约束中的单位在单位换算表中无法查到，属于notice情况 
        antecedent_converted = None
        consequence_converted = None
        if has_antecedent_constraint:
            antecedent_converted = self._convert_unit(inference["antecedent"]["cond"])
        if has_consequence_constraint:
            consequence_converted = self._convert_unit(inference["consequence"]["cond"])
        
        # 处理知识唯一标识（"knowid"）、知识目录（"knowcata"）属性，构建选项唯一标识（"id"）、选项关联知识（"cataid"）、选项关联指标（"evaluation"）。
        
        # 两件都没有转化 -> 输出notice
        if not antecedent_converted and not consequence_converted:
            self.log_manager.generate_error_log(time(), knowid, "lim_unit_transform", "notice", 13, "前后件的单位在单位换算表中均无法查到。")
            return generate_result
        if not antecedent_converted and has_antecedent_constraint:
            self.log_manager.generate_error_log(time(), knowid, "lim_unit_transform", "notice", 13, "前件的单位在单位换算表中无法查到。")
        if not consequence_converted and has_consequence_constraint:
            self.log_manager.generate_error_log(time(), knowid, "lim_unit_transform", "notice", 13, "后件的单位在单位换算表中无法查到。")

        # 选项真值为True。
        # 情况1：仅前件
        if antecedent_converted:
            for i, (unit, value) in enumerate(antecedent_converted.items(), start=0):
                new_ante = copy.deepcopy(inference["antecedent"]["cond"])
                new_ante["constraint"].update(unit=unit, index=value)
                option_text = self._make_string(new_ante, inference["consequence"]["cond"])
                # 后件不变
                generate_result.append(make_JSON(knowid + "15A" + str(i).zfill(2), option_text, True, 6, knowcata))
         
         # 情况2：仅后件  
        if consequence_converted:
            for i, (unit, value) in enumerate(consequence_converted.items(), start=0):
                new_cons = copy.deepcopy(inference["consequence"]["cond"])
                new_cons["constraint"].update(unit=unit, index=value)
                option_text = self._make_string(inference["antecedent"]["cond"],  new_cons)
                # 前件不变
                generate_result.append(make_JSON(knowid + "15B" + str(i).zfill(2), option_text, True, 6, knowcata))
                                    
        # 成功生成选项时，将生成选项信息写入运行日志。
        self.log_manager.generate_run_log(time(), knowid, "lim_unit_transform", len(generate_result))

        return generate_result