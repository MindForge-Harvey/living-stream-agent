#!/bin/bash
# 部署脚本 - 只部署 App，连接外部 MySQL

set -e

echo "=========================================="
echo "直播脚本生成智能体 - 部署脚本"
echo "=========================================="

# 检查 Docker 是否安装
if ! command -v docker &> /dev/null; then
    echo "错误: Docker 未安装，请先安装 Docker"
    exit 1
fi

if ! command -v docker compose &> /dev/null; then
    echo "错误: Docker Compose 未安装，请先安装 Docker Compose"
    exit 1
fi

# 创建目录
echo "创建部署目录..."
mkdir -p /opt/living-stream-agent
cd /opt/living-stream-agent

# 加载镜像
echo "加载 Docker 镜像..."
docker load -i images.tar.gz

# 检查 .env 文件
if [ ! -f .env ]; then
    echo "创建 .env 配置文件..."
    cp .env.example .env
    echo ""
    echo "⚠️  请编辑 .env 文件，配置以下内容："
    echo "   - OPENAI_API_KEY: OpenAI API Key"
    echo "   - MYSQL_HOST: MySQL 服务器地址"
    echo "   - MYSQL_PASSWORD: MySQL 密码"
    echo ""
    echo "   vi .env"
    echo ""
    exit 1
fi

# 启动服务
echo "启动服务..."
docker compose up -d

echo ""
echo "=========================================="
echo "部署完成！"
echo "=========================================="
echo ""
echo "访问地址："
echo "  - 主页面: http://localhost:5172/chat/"
echo "  - 管理后台: http://localhost:5172/chat/login"
echo ""
echo "默认账号："
echo "  - 管理员: admin123 / admin123"
echo "  - 超级管理员: admin / admin"
echo ""
echo "查看日志: docker compose logs -f"
echo "停止服务: docker compose down"
echo ""
