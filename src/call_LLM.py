from openai import OpenAI

from config import config_choice
'''
3-22 大模型调用

版本迭代情况
[脱敏] 版本迭代记录

库依赖情况
openai==1.92.0

配置变量使用情况:
API_KEY:大模型调用的密钥
'''

def call_LLM(LLM_prompt):
    '''
    参数:LLM_prompt:大模型提示词
    返回值:LLM_answer

    异常处理:
    这里不做异常处理，当出现异常的时候抛出，被调用的组件捕获，写入日志的异常种类由调用的组件决定

    需要额外说明的是,返回的字符串是没有经过处理的，仍然需要调用方处理，获取到可用的字符串
    '''
    api_key = config_choice.API_KEY
    client = OpenAI(api_key=api_key, base_url=config_choice.API_BASE_URL)
    LLM_answer = ""

    for i in range(0, 4):  # 重复4次调用，减少网络干扰,这四次调用，不会抛出异常
        try:
            response = client.chat.completions.create(
                model="deepseek-chat",
                messages=[
                    {"role": "user", "content": LLM_prompt},
                ],
                max_tokens=1024,
                temperature=0.7,
                stream=False
            )
            if response.choices[0].message.content != "":
                LLM_answer = response.choices[0].message.content
                return LLM_answer
        except Exception as e:
            continue

    #如果前四次由于异常返回结果为空，进行第五次调用，如果再次失败，就抛出异常
    response = client.chat.completions.create(
        model="deepseek-chat",
        messages=[
            {"role": "user", "content": LLM_prompt},
        ],
        max_tokens=1024,
        temperature=0.7,
        stream=False
    )

    #如果调用结果不为空，返回调用结果
    if response.choices[0].message.content != "":
        LLM_answer = response.choices[0].message.content

    LLM_answer = response.choices[0].message.content
    if LLM_answer != "":
        return LLM_answer
    else:
        return ""