import os
CONFIG_BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# 调用deepseek的账号密钥，建议通过环境变量DEEPSEEK_API_KEY设置。
API_KEY = os.environ.get("DEEPSEEK_API_KEY", "")

# DeepSeek API的基础地址。
API_BASE_URL = "https://api.deepseek.com"

# cond的schema字符串。
COND_CONSTRAINT_SCHEMA = """{
    "type": "object",
    "properties": {
        "entity": {"type": "string"},
        "bool": {"type": "boolean"},
        "constraint": {
            "oneOf": [
                {
                    "type": "object",
                    "properties": {
                        "verb": {"type": "string"},
                        "entity": {"type": "array", "items": {"type": "string"}}
                    },
                    "required": ["entity"]
                },
                {
                    "type": "object",
                    "properties": {
                        "compare": {"enum": ["large", "equal", "below", "largeequal", "notequal", "belowequal"]},
                        "index": {"type": "number"},
                        "unit": {"type": "string"}
                    },
                    "required": ["compare", "index", "unit"]
                }
            ]
        }    
    },
    "required": ["entity", "bool", "constraint"]
}"""
# 推理后件的schema字符串。
CONSEQUENCE_SCHEMA = """{
    "$schema": "http://json-schema.org/draft-07/schema#",
    "$defs": {
        "cond": {
            "type": "object",
            "properties": {
                "entity": {"type": "string"},
                "bool": {"type": "boolean"},
                "constraint": {
                    "oneOf": [
                        {
                            "type": "object",
                            "properties": {
                                "verb": {"type": "string"},
                                "entity": {"type": "array", "items": {"type": "string"}}
                            },
                            "required": ["entity"]
                        },
                        {
                            "type": "object",
                            "properties": {
                                "compare": {"enum": ["large", "equal", "below", "largeequal", "notequal", "belowequal"]},
                                "index": {"type": "number"},
                                "unit": {"type": "string"}
                            },
                            "required": ["compare", "index", "unit"]
                        }
                    ]
                }    
            },
            "required": ["entity", "bool", "constraint"]
        }
    },
    
    "type": "object",
    "properties":{
        "cond": {"$ref": "#/$defs/cond"}
    },
    "required": ["cond"]
}"""
# 选项schema。
CHOICE_SCHEMA = """{
    "$schema": "http://json-schema.org/draft-07/schema#",
    "$defs": {
        "id": {"type": "string", "pattern": "^[0-9]+$", "maxLength": 30}
    },
    "type": "object",
    "properties": {
        "id": {"type": "string", "maxLength": 30},
        "text": {"type": "string"},
        "value": {"type": "boolean"},
        "evaluation": {"type": "integer", "minimum": 0},
        "cataid": {"$ref": "#/$defs/id"}
    },
    "required": ["id", "text", "value", "evaluation", "cataid"]
}"""
#推理前件 推理后件的schema
CONSTRAINT_SCHEMA= """{
    "type": "object",
    "properties": {
        "entity": {"type": "string"},
        "bool": {"type": "boolean"},
        "constraint": {
            "oneOf": [
                {
                    "type": "object",
                    "properties": {
                        "verb": {"type": "string"},
                        "entity": {"type": "array", "items": {"type": "string"}}
                    },
                    "required": ["entity"]
                },
                {
                    "type": "object",
                    "properties": {
                        "compare": {"enum": ["large", "equal", "below", "largeequal", "notequal", "belowequal"]},
                        "index": {"type": "number"},
                        "unit": {"type": "string"}
                    },
                    "required": ["compare", "index", "unit"]
                }
            ]
        }    
    },
    "required": ["entity", "bool", "constraint"]
}"""
#并置关系的schema
Parallel_SCHEMA="""{
    "$schema": "http://json-schema.org/draft-07/schema#",

    "type": "array",
    "items": {
        "type": "object",
        "properties": {
            "Parallel": {"type": "string"}
        },
        "required": ["Parallel"]
    }
}"""

'''
由于句式转换的定义较为宽泛，大模型有时会理解成近义词替换和干扰
但是指定内容的话，不同知识可用的句式转换方式不同，所以这里我们不指定内容，而是指定要求。
而且向大模型发起一次请求的时间较长,所以暂时不采用多组prompt分类指定的方式。
如果之后有此类需求，可以在后续中更改。
'''
# 生成选项基本要求的prompt
TRANSFORM_PROMPT ="如上是一条正确的知识；请你生成句式转换后的陈述，要求不变核心含义，每一条陈述以“陈述：”开头，独立一行"
# 润色生成内容的prompt。
REFINE_PROMPT = """如上是一个包含推理关系的陈述，它要作为题目的一个选项，但是表达可能不够自然。请你对相关否定词进行修改，使之更符合中文表达习惯。
每条原始陈述生成一条修改后的陈述即可；修改后的陈述以“陈述：”开头，每条陈述独立一行。"""
# 生成倒果为因选项的prompt
TRAP_REVERSE_PROMPT = "如上是一条正确的知识；请你生成包含倒果为因推理陷阱的错误陈述，每一条陈述以“陈述：”开头，独立一行。"
# 生成非此即彼的prompt
TRAP_BLACK_WHITE_PROMPT = "如上是一条正确的知识；请你生成包含非此即彼推理陷阱的错误陈述，每一条陈述以“陈述：”开头，独立一行。"
# 生成循环论证的prompt
TRAP_RECYCLE_PROMPT = "如上是一条正确的知识；请你生成包含循环论证推理陷阱的错误陈述，每一条陈述以“陈述：”开头，独立一行。"
# 润色生成内容的prompt。 3-13使用
REFINE_PROMPT_REVERSE = """如上是一个包含推理关系的陈述，它要作为题目的一个选项，但是表达可能不够自然。请你对相关否定词进行修改，使之更符合中文表达习惯。
每条原始陈述生成一条修改后的陈述即可；修改后的陈述以“陈述：”开头，每条陈述独立一行。"""
# 大模型辅助掩码生成的prompt。 3-16使用
LLM_PROMPT="""如上依次是一个被掩码的句子（需要替换的位置已用[MASK]标注）以及被掩码的原始词,
请根据上面被掩码的句子和原始词，用一个错误的替换填充[MASK]（只替换[MASK]，不要改句子其他内容），然后直接给出完整的替换后句子。
输出仅一行，以前缀“陈述：”开头，后面紧跟完整的一句陈述。替换应制造语义错误如错误词汇或数值，但句子要通顺、语法正确。"""
# 润色生成内容的prompt。 3-25使用
REFINE_PROMPT_25 = """如上是一个包含推理关系的陈述，它要作为题目的一个选项，但是表达可能不够自然。请你进行修改，使之更符合中文表达习惯。
每条原始陈述生成一条修改后的陈述即可；修改后的陈述以“陈述：”开头，每条陈述独立一行。"""
# 对并置关系混淆之后进行润色的prompt
CONFUSE_PARALLEL_REFINE_PROMPT='''如上是一个陈述，但是表达可能不够自然，请你对这个陈述进行润色，使之更符合中文表达习惯，修改后的陈述以“陈述：”开头，每条陈述独立一行。'''
# 大模型对数值模糊生成选项的润色prompt。 3-29使用
ATT_FUZZY_PROMPT = """如上是一个包含推理关系的陈述，它要作为题目的一个错误选项，但是表达可能不够自然。请你对句子进行语言润色，使之更符合中文表达习惯。要求1.绝对不能修正原始句子中的任何事实错误、逻辑谬误或不符合常识的内容。2.改写后的句子必须与原句的意思【完全相同】。如果原句是错的，改写后也必须是错的。
每条原始陈述生成一条修改后的陈述即可；修改后的陈述以“陈述：”开头，每条陈述独立一行。"""
# 大模型对极端数值替换生成的语句进行润色的prompt。 3-30使用
REFINE_PROMPT_IRRATIONALITY = """如上是一个包含极端数值替换的陈述，它要作为题目的一个选项，但是表达可能不够自然。请你对其进行修改，使之更符合中文表达习惯。
每条原始陈述生成一条修改后的陈述即可；修改后的陈述以“陈述：”开头，每条陈述独立一行。"""

# 大模型对数值约束的语义进行更小范围的不合理替换的prompt。 3-31使用
SEMANTIC_IRRATIONALITY_PROMPT = """请你判断数值在比较关系和单位带来的约束之外，
是否还有语境隐藏的其它约束条件。如果有，把该知识中的数值替换成不符合隐藏约束条件的数值，
并组织新的不合理的陈述，要求不要生成LateX和Markdown格式的内容。生成的陈述以“陈述：”开头，每一条陈述单独一行。"""

# 文档依赖的停用词表保存地址。
STOPWORDS_FILE_DIR = CONFIG_BASE_DIR + os.sep + "document"+ os.sep + "stopwords.txt"
# 文档依赖的常用单位表保存地址。
UNIT_TABLE_PATH = CONFIG_BASE_DIR + os.sep + "document"+ os.sep + "unit_conversion_table.csv"
#文件依赖的不合理单位值表保存地址。
UNIT_IRRATIONALITY_TABLE_PATH = CONFIG_BASE_DIR + os.sep + "document"+ os.sep + "unit_irrationality_table.csv"
# 文档依赖的单位转换表保存地址。
TRANSFORM_UNIT_DIR = CONFIG_BASE_DIR + os.sep + "document"+ os.sep + "transform_unit.csv"
# JSON文件的保存地址。
CHOICE_JSON_FILENAME = CONFIG_BASE_DIR + os.sep + "choice" + os.sep + "json_choice_4.4.txt"
# 目录文件的地址。
CATALOG_FILENAME = CONFIG_BASE_DIR + os.sep + "document" + os.sep + "catalog.csv"

# 日志文件路径配置。
ERROR_LOG_PATH = CONFIG_BASE_DIR + os.sep + "log" + os.sep + "error_log.txt"
RUN_LOG_PATH = CONFIG_BASE_DIR + os.sep + "log" + os.sep + "run_log.txt"

# 一道题选项的数字，目前指定为4。
CHOICE_NUMBER = 4
# 不定项选择题的比例，目前指定为0.2。
UNCERTAIN_MULTIPLE_RATIO = 0.2
# 题目输出的位置。
QUESTION_OUTPUT = CONFIG_BASE_DIR + os.sep + "question" + os.sep + "json_question.txt"
#日志写入文件的阈值
THRESHOLD_LOG=1
# 并置规则头提取：足够切分句子的标点符号
SENTENCE_SPLIT_PUNCTUATIONS = ["。", "：", "；", "，", ",", ":", ";", ".", "、", "！", "?", "？", "；"]

# 语义鲁棒性指标配置
SEMANTIC_ROBUSTNESS_CONFIG = {
    # 基础指标分级
    "BASE_SCORES": {
        "noun": 1,        # 名词替换：基础语义鲁棒性测试
        "verb": 2,        # 动词替换：涉及动作语义，稍复杂
        "adjective": 1,   # 形容词替换：属性描述替换
        "adverb": 1       # 副词替换：修饰成分替换
    },
    
    # 指标等级说明
    "LEVEL_DESCRIPTIONS": {
        1: "基础同义词替换（名词、形容词、副词）",
        2: "动词替换（涉及动作语义）", 
        3: "长词替换短词（语义泛化）",
        4: "短词替换长词（语义具化）",
        5: "复杂语义变化替换"
    },
    
    # 词长差异调整因子
    "LENGTH_ADJUSTMENT": {
        "min_score": 1,
        "max_score": 5,
        "length_factor_threshold": 2  # 词长差异超过2时调整分数
    },
    
    # 特殊词性处理
    "SPECIAL_POS_RULES": {
        "technical_terms": 3,    # 技术术语替换
        "proper_nouns": 4,       # 专有名词替换
        "compound_words": 2      # 复合词替换
    }
}

# 选项真值判断配置
OPTION_VALUE_CONFIG = {
    # 经过实体库过滤的近义词默认为安全，真值恒为True
    "DEFAULT_VALUE": True,
    
    # 说明：由于算法采用一致性核查机制（步骤3过滤），
    # 所有保留的近义词都不在实体库中，语义上是安全的
    "REASONING": "经过实体库过滤的近义词不会产生领域冲突，语义安全"
}

# 算法运行配置
ALGORITHM_CONFIG = {
    # 近义词获取配置
    "MAX_SYNONYMS": 5,
    
    # 输出配置
    "OUTPUT_FORMAT": "json",
    
    # 选项ID格式
    "OPTION_ID_FORMAT": "{knowid}_opt_{sequence:03d}"
}
