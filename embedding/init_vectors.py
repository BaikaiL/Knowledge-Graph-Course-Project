from vector_manager import VectorManager

# 配置信息
NEO4J_URI = "bolt://10.252.172.153:7687"  # 或者是远程IP
NEO4J_USER = "neo4j"
NEO4J_PASSWORD = "88888888"
DASHSCOPE_API_KEY = "sk-93df5702a17d46678b356d19bad90d30"  # 填入你的 Key


def reset_and_initialize():
    vm = VectorManager(NEO4J_URI, NEO4J_USER, NEO4J_PASSWORD, api_key=DASHSCOPE_API_KEY)

    print("=== 开始初始化向量数据库 ===")

    # 1. (可选) 清理旧数据：如果你之前存过 768 维的向量，必须清理！
    # 如果是全新的库，可以注释掉下面两行
    # print("正在清理旧的索引和数据...")
    # with vm.driver.session() as session:
    #     try:
    #         session.run("DROP INDEX function_embedding_index")
    #     except:
    #         pass  # 索引不存在就算了
    #     session.run("MATCH (n:功效) REMOVE n.embedding")  # 删除旧向量属性

    # 2. 创建新索引 (1024维)
    vm.create_index_if_not_exists()

    # 3. 刷入数据
    # 这里会调用 API，如果数据量大可能会花点时间
    vm.refresh_embeddings(force_update=True)

    vm.close()
    print("=== 初始化完成 ===")


if __name__ == "__main__":
    reset_and_initialize()