"""
应用配置中心。

这个文件专门负责：
1. 使用 pydantic-settings 从项目根目录的 .env 中读取配置。
2. 将配置统一收口到 Settings 类里，避免在项目各处直接读 os.environ。
3. 暴露一个 settings 单例，供整个后端直接复用。

后续其他模块统一这样使用：
    from core.config import settings
"""

from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

# 计算项目根目录。
# 当前文件路径是：backend/core/config.py
# 向上取两级后就是项目根目录 fina/，也就是 .env 文件所在的位置。
PROJECT_ROOT = Path(__file__).resolve().parents[2]

# 明确指定 .env 文件的绝对路径。
# 这样无论你是在项目根目录启动，还是在 backend 目录启动，
# 都能稳定读取到同一份环境变量配置。
ENV_FILE_PATH = PROJECT_ROOT / ".env"


class Settings(BaseSettings):
    """
    项目配置模型。

    BaseSettings 的作用是：
    - 自动从环境变量读取同名字段
    - 支持从 .env 文件加载配置
    - 自动做基础类型校验

    这里把当前后端会用到的配置项都集中定义出来，
    后续新增配置时，继续在这个类里补字段即可。
    """

    # 指定 pydantic-settings 的加载规则。
    model_config = SettingsConfigDict(
        # 指向项目根目录下的 .env 文件。
        env_file=ENV_FILE_PATH,
        # 指定 .env 文件编码，避免中文注释或非 ASCII 内容读取异常。
        env_file_encoding="utf-8",
        # 忽略未在 Settings 类中声明的额外环境变量，避免报错。
        extra="ignore",
    )

    # 数据库连接地址。
    # 这个值会被 database.py、迁移脚本、任务调度等模块复用。
    DATABASE_URL: str

    # JWT 签名密钥。
    # 后续在登录、鉴权、中间件或安全模块里都会使用这个值。
    JWT_SECRET: str

    # DeepSeek API Key。
    # 当前允许为空字符串，方便你在本地先把系统跑起来，
    # 等接 AI 功能时再把真实 Key 填进去。
    DEEPSEEK_API_KEY: str = ""

    # 后台管理访问令牌。
    # 后续会用于校验请求头中的 X-Admin-Token 是否合法。
    ADMIN_TOKEN: str


# 创建一个全局单例。
# 这样做的目的，是让整个项目都共享同一份配置对象，
# 避免每次使用时都重新实例化 Settings。
settings = Settings()
