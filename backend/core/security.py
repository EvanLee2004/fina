"""
JWT 安全模块。

这个文件专门负责：
1. 生成登录后的 JWT Token。
2. 校验客户端传入的 JWT Token。
3. 在校验成功后返回 user_id，供后续鉴权逻辑使用。

当前约定：
- 算法使用 HS256
- Token 有效期为 7 天
- 使用 settings.JWT_SECRET 作为签名密钥
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from jose import ExpiredSignatureError, JWTError, jwt

from core.config import settings

# JWT 签名算法。
# HS256 是对称加密算法，编码和解码都使用同一份密钥。
ALGORITHM = "HS256"

# Token 过期时间。
# 这里按你的要求固定为 7 天。
ACCESS_TOKEN_EXPIRE_DAYS = 7


class TokenValidationError(Exception):
    """
    Token 校验失败时抛出的统一异常。

    这样做的好处是：
    - 调用方只需要捕获一个明确的业务异常
    - 不需要感知底层到底是过期、签名错误，还是 payload 不合法
    """


def create_token(user_id: int) -> str:
    """
    生成 JWT Token。

    参数：
    - user_id: 当前登录用户的主键 ID

    返回：
    - str: 编码后的 JWT 字符串

    Payload 说明：
    - sub: JWT 标准声明之一，这里用来存储用户 ID
    - exp: 过期时间，python-jose 会在 decode 时自动校验
    """
    # 生成一个带时区的当前 UTC 时间，避免时区引发的过期判断问题。
    now = datetime.now(timezone.utc)

    # 计算 Token 的过期时间。
    expire_at = now + timedelta(days=ACCESS_TOKEN_EXPIRE_DAYS)

    # 组装 JWT 的载荷数据。
    # 这里把 user_id 转成字符串存入 sub，符合 JWT 对 subject 的常见约定。
    payload = {
        "sub": str(user_id),
        "exp": expire_at,
    }

    # 使用项目配置中的 JWT_SECRET 对 payload 进行签名并生成 token。
    token = jwt.encode(payload, settings.JWT_SECRET, algorithm=ALGORITHM)
    return token


def verify_token(token: str) -> int:
    """
    校验 JWT Token，并返回其中的 user_id。

    参数：
    - token: 客户端传入的 JWT 字符串

    返回：
    - int: 解码成功后得到的用户 ID

    异常：
    - TokenValidationError: 当 token 为空、已过期、签名错误或 payload 非法时抛出
    """
    # 先做最基础的空值校验，避免把明显非法输入继续传给解码逻辑。
    if not token:
        raise TokenValidationError("Token 不能为空。")

    try:
        # 解码并校验 JWT。
        # 这一步会同时验证：
        # 1. 签名是否正确
        # 2. 算法是否匹配
        # 3. exp 是否已过期
        payload = jwt.decode(
            token,
            settings.JWT_SECRET,
            algorithms=[ALGORITHM],
        )

        # 从 payload 中取出用户标识。
        user_id_raw = payload.get("sub")

        # 如果 sub 缺失，说明 token 结构不符合系统约定。
        if user_id_raw is None:
            raise TokenValidationError("Token 缺少用户标识。")

        # 将 sub 转为 int 返回，供数据库查询或权限校验直接使用。
        user_id = int(user_id_raw)
        return user_id

    except ExpiredSignatureError as exc:
        # Token 已过期。
        raise TokenValidationError("Token 已过期，请重新登录。") from exc
    except JWTError as exc:
        # 包括签名错误、格式错误、算法不匹配等所有 JWT 相关异常。
        raise TokenValidationError("Token 无效。") from exc
    except (TypeError, ValueError) as exc:
        # 处理 sub 不是合法整数等 payload 数据异常情况。
        raise TokenValidationError("Token 中的用户标识不合法。") from exc
