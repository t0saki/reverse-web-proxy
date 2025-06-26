# 使用官方 Python 运行时作为父镜像
FROM python:3.13-slim

# 在容器中设置工作目录
WORKDIR /app

# 将依赖文件复制到工作目录
COPY requirements.txt .

# 安装 requirements.txt 中指定的任何所需包
RUN pip install --no-cache-dir -r requirements.txt

# 将应用程序的其余代码复制到工作目录
COPY . .

# 使容器外的世界可以使用端口 8000
EXPOSE 8000

# 运行 app.py 当容器启动时
# 使用 Gunicorn 启动应用
CMD ["gunicorn", "--bind", "0.0.0.0:8000", "app:app"]
