from vector_manager import VectorManager
from utils.config import NEO4J_URI, NEO4J_USER, NEO4J_PASSWORD, DASHSCOPE_API_KEY


def reset_and_initialize():
    vm = VectorManager(NEO4J_URI, NEO4J_USER, NEO4J_PASSWORD, api_key=DASHSCOPE_API_KEY)

    # 创建新索引 (1024维)
    vm.create_index_if_not_exists()

    # 刷入数据
    vm.refresh_embeddings(force_update=True)

    vm.close()
    print("=== 初始化完成 ===")


if __name__ == "__main__":
    reset_and_initialize()