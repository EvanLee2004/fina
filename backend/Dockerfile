FROM python:3.12-slim

# 设置容器内工作目录为后端目录。
# 这样后续可以直接使用 uvicorn main:app 启动服务。
WORKDIR /app/backend

# 安装 matplotlib 绘图和中文字体所需的系统依赖。
# fonts-noto-cjk 用于保证容器内生成的中文图表不会出现乱码或方块字。
RUN apt-get update \
    && apt-get install -y --no-install-recommends fonts-noto-cjk \
    && rm -rf /var/lib/apt/lists/*

# 先复制依赖文件，便于利用 Docker 构建缓存。
COPY backend/requirements.txt ./requirements.txt

# 安装 Python 依赖。
RUN pip install --no-cache-dir -r requirements.txt

# 再复制后端代码。
COPY backend/ /app/backend/

# 暴露 FastAPI 服务端口。
EXPOSE 8000

# 启动 FastAPI 应用。
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
