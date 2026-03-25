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

    # 记忆数据库连接地址。
    # 这个库专门存放对话历史和长期记忆，和财务主库分离。
    # 如果你暂时不想维护两套数据库，也可以不填；
    # 程序会自动回退到 DATABASE_URL。
    MEMORY_DATABASE_URL: str | None = None

    # JWT 签名密钥。
    # 后续在登录、鉴权、中间件或安全模块里都会使用这个值。
    JWT_SECRET: str

    # 通用 AI 服务访问密钥。
    # 当前允许为空字符串，方便你先把系统跑起来，
    # 真正调用模型时再手动填入对应服务商的 Key。
    AI_API_KEY: str = ""

    # OpenAI 兼容接口的基础地址。
    # 默认指向 DeepSeek 的 OpenAI 兼容入口。
    # 后续如需切换到其他兼容服务，只需要改这个值。
    AI_BASE_URL: str = "https://api.deepseek.com/v1"

    # 默认使用的模型名称。
    # 这是“默认模型”，如果某次请求没有显式指定 model，就会回落到这个值。
    # 这里不要写 API Key，只能写模型名，例如 deepseek-chat / gpt-4o-mini / qwen-max。
    AI_MODEL: str = "deepseek-chat"

    # 允许调用的模型白名单，使用英文逗号分隔。
    # 这个字段为空时，表示允许调用方临时指定任意 OpenAI 兼容模型；
    # 一旦配置了值，后端就只允许从这份列表里选，避免传错模型名。
    AI_ALLOWED_MODELS: str = ""

    # 后台管理访问令牌。
    # 后续会用于校验请求头中的 X-Admin-Token 是否合法。
    ADMIN_TOKEN: str

    # Stripe 服务端密钥。
    # 当前主要用于后续扩展从服务端回查对象或补数据；即使暂时不用，也先统一纳入配置。
    STRIPE_API_KEY: str = ""

    # Stripe webhook 签名密钥。
    # 用于校验 webhook 请求是否真的来自 Stripe。
    STRIPE_WEBHOOK_SECRET: str = ""

    # 导出文件目录。
    # Excel 和 Word 报告会统一输出到这个目录下，方便调用方下载或二次处理。
    EXPORTS_DIR: str = str(PROJECT_ROOT / "exports")


# 创建一个全局单例。
# 这样做的目的，是让整个项目都共享同一份配置对象，
# 避免每次使用时都重新实例化 Settings。
settings = Settings()
