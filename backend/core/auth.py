"""
X-Admin-Token 认证依赖。

这个文件专门负责：
1. 从请求头中读取 X-Admin-Token。
2. 与配置中的 settings.ADMIN_TOKEN 做比对。
3. 为不需要认证的路径提供白名单放行。
4. 以 FastAPI Depends 的方式复用，不使用中间件。
"""

from __future__ import annotations

from fastapi import Header, HTTPException, Request, status

from core.config import settings

# 无需做管理员令牌校验的路径白名单。
# 这些路径主要用于健康检查和接口文档访问。
EXCLUDED_PATHS = {
    "/ping",
    "/docs",
    "/openapi.json",
}


def verify_token(
    request: Request,
    x_admin_token: str | None = Header(default=None, alias="X-Admin-Token"),
) -> None:
    """
    校验请求头中的 X-Admin-Token。

    参数：
    - request: 当前请求对象，用于读取访问路径
    - x_admin_token: 从 Header 中提取的 X-Admin-Token 值

    行为说明：
    - 如果当前路径在白名单中，则直接放行
    - 如果请求头缺失 token 或 token 不匹配，则返回 401
    - 校验成功时不返回任何数据，只表示允许继续执行后续接口逻辑
    """
    # 先判断当前路径是否属于白名单。
    # /ping、/docs、/openapi.json 这些路径不要求管理员令牌。
    if request.url.path in EXCLUDED_PATHS:
        return

    # 如果没有传 X-Admin-Token，或者传入的值与配置项不一致，
    # 则直接拒绝访问，并返回 401 未授权状态码。
    if x_admin_token != settings.ADMIN_TOKEN:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid X-Admin-Token",
        )


# 为了兼容之前已经引用过 verify_admin_token 的代码，
# 这里保留一个同义别名，避免旧引用立即失效。
verify_admin_token = verify_token
