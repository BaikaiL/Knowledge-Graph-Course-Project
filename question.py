from utils.ConnectUtils import ConnectUtils
from utils.KBQAService import KBQAService
from openai import OpenAI
import os

# 1. 初始化数据库连接
# 假设你的连接配置在这里
conn_manager = ConnectUtils("bolt://localhost:7687", "neo4j", "88888888")
conn_manager.connect()

# 2. 初始化 LLM 客户端
# 这里可以使用 OpenAI，也可以使用 DeepSeek, 阿里通义千问等兼容 OpenAI SDK 的模型
client = OpenAI(
    api_key="sk-xxxx", # 替换你的 API Key
    base_url="https://dashscope.aliyuncs.com/compatible-mode/v1" # 如果用其他模型，修改此处 Base URL
)

# 3. 实例化问答服务
qa_service = KBQAService(conn_manager, client)

# 4. 测试问答
if __name__ == "__main__":
    questions = [
        "傻逼茶有什么嘛功效",
        "金银花茶有什么功效？",
        "夏季适合喝什么茶？",
        "我最近有点上火，推荐喝什么代茶饮？",
        "清热解毒的代茶饮有哪些？"
    ]

    for q in questions:
        print("-" * 50)
        answer = qa_service.answer(q)
        print(f"AI 回答: {answer}")


conn_manager.close()
