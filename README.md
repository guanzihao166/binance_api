# 币安期货AI分析系统 🚀

[![GitHub License](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)
[![Python Version](https://img.shields.io/badge/python-3.8%2B-blue)](https://www.python.org/)
[![Streamlit](https://img.shields.io/badge/streamlit-v1.25%2B-red)](https://streamlit.io/)

一个基于 **AI（DeepSeek）** 和 **大数据分析** 的币安期货实时监控系统，集成智能分析、历史命中率跟踪、以及完整的风险管理工具。专为专业交易者和量化研究人员设计。

**[English](README_EN.md)** | **[快速开始](QUICKSTART.md)** | **[功能说明](FEATURES.md)** | **[故障排除](BUG_REPORT.md)**

---

## 🌟 核心功能

### 📊 实时账户监控
- **账户概览**: 钱包余额、保证金、可用资金、未实现盈亏、总回报率
- **仓位监控**: 实时持仓信息，包含方向、数量、开仓价格、标记价格、盈亏状态
- **K线分析**: 使用 Plotly 绘制交互式蜡烛线图，支持缩放、平移、指标叠加

### 🤖 AI智能分析
- **后台处理**: 每5分钟自动更新1次分析（不阻塞前端）
- **JSON验证**: 后端负责所有 JSON 解析，失败自动重试（最多3次）
- **完整建议**:
  - 是否建议入场（买/卖信号）
  - 做多/做空方向建议
  - 重仓/轻仓建议
  - 目标入场价、止损价、止盈价
  - 压力位、支撑位分析
  - 详细分析理由和风险提示

### 📈 数据分析与统计
- **7天数据存储**: 保存币安K线和资金费率数据，用于趋势分析
- **市场分析**: 计算7天内的价格波动率、资金费率变化趋势
- **命中率跟踪**: 记录AI分析命中情况，计算整体胜率和平均盈亏
- **历史记录**: 完整的分析历史，支持按交易对筛选、标记命中/失误、输入收益数据

### 🔐 企业级特性
- **环境变量管理**: 安全的配置管理，敏感信息不入代码
- **自动清理**: 过期数据自动删除，数据库自维护
- **后台管理**: 独立的后台分析线程，不影响UI响应
- **完整错误处理**: 结构化日志和异常捕获

---

## 📋 系统要求

### 最低要求
- **Python**: 3.8+
- **操作系统**: Linux / macOS / Windows
- **RAM**: 1 GB
- **磁盘**: 500 MB（用于数据库）

### 推荐配置（生产环境）
- **Python**: 3.10+
- **操作系统**: Ubuntu 20.04 LTS / Rocky Linux 8+
- **RAM**: 2 GB
- **磁盘**: 2 GB

### 外部依赖
- **币安期货账户**: 必需（获取API密钥）
- **DeepSeek API**: 必需（用于AI分析）
- **网络连接**: 必需（实时数据推送）

---

## 🚀 快速开始

### 1️⃣ 获取API密钥

#### 币安期货
1. 访问 [币安官网](https://www.binance.com) 并登录账户
2. 进入 **账户 → API管理**
3. 新建API Key
4. 启用 **期货权限**，禁用 **提现权限**
5. 复制 API Key 和 Secret

#### DeepSeek API
1. 访问 [DeepSeek开放平台](https://api.deepseek.com)
2. 注册账户并创建API Key
3. 确保账户有充足余额

### 2️⃣ 本地安装（开发环境）

#### Windows
```powershell
# 克隆项目
git clone https://github.com/guanzihao166/binance_api.git
cd binance_api

# 创建虚拟环境
python -m venv venv
.\venv\Scripts\activate

# 安装依赖
pip install -r requirements.txt

# 设置环境变量
$env:BINANCE_API_KEY="your-api-key"
$env:BINANCE_API_SECRET="your-api-secret"
$env:DEEPSEEK_API_KEY="your-deepseek-key"

# 运行应用
streamlit run main.py
# 访问 http://localhost:8501
```

#### Linux/macOS
```bash
# 克隆项目
git clone https://github.com/guanzihao166/binance_api.git
cd binance_api

# 创建虚拟环境
python3 -m venv venv
source venv/bin/activate

# 安装依赖
pip install -r requirements.txt

# 设置环境变量
export BINANCE_API_KEY="your-api-key"
export BINANCE_API_SECRET="your-api-secret"
export DEEPSEEK_API_KEY="your-deepseek-key"

# 运行应用
streamlit run main.py
# 访问 http://localhost:8501
```

### 3️⃣ Linux服务器部署

#### 完全自动化安装（推荐）
```bash
# 下载安装脚本
wget https://github.com/guanzihao166/binance_api/raw/master/scripts/install_linux.sh
chmod +x install_linux.sh

# 运行安装
sudo ./install_linux.sh
# 按提示输入API密钥

# 启动服务
sudo systemctl start binance-ai-analyzer
sudo systemctl status binance-ai-analyzer
```

#### 手动部署步骤
```bash
# 1. 更新系统
sudo apt update && sudo apt upgrade -y
sudo apt install -y python3.10 python3.10-venv python3-pip git

# 2. 创建应用目录
sudo mkdir -p /opt/binance-ai-analyzer
cd /opt/binance-ai-analyzer

# 3. 克隆项目
sudo git clone https://github.com/guanzihao166/binance_api.git .

# 4. 创建虚拟环境
sudo python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# 5. 创建 .env 文件
sudo tee .env > /dev/null << EOF
BINANCE_API_KEY=your-api-key
BINANCE_API_SECRET=your-api-secret
DEEPSEEK_API_KEY=your-deepseek-key
SERVER_ADDRESS=0.0.0.0
SERVER_PORT=8501
DEBUG_MODE=false
EOF

# 6. 设置权限
sudo chown -R ubuntu:ubuntu /opt/binance-ai-analyzer

# 7. 创建systemd服务（参考下面的配置）
sudo systemctl daemon-reload
sudo systemctl enable binance-ai-analyzer
sudo systemctl start binance-ai-analyzer
```

### Systemd服务配置

创建 `/etc/systemd/system/binance-ai-analyzer.service`：

```ini
[Unit]
Description=Binance AI Analyzer - 币安期货AI分析系统
Documentation=https://github.com/guanzihao166/binance_api
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
User=ubuntu
Group=ubuntu
WorkingDirectory=/opt/binance-ai-analyzer
Environment="PATH=/opt/binance-ai-analyzer/venv/bin"
EnvironmentFile=/opt/binance-ai-analyzer/.env

ExecStart=/opt/binance-ai-analyzer/venv/bin/streamlit run main.py \
    --server.address=0.0.0.0 \
    --server.port=8501 \
    --logger.level=info \
    --client.showErrorDetails=true

Restart=on-failure
RestartSec=10

StandardOutput=journal
StandardError=journal
SyslogIdentifier=binance-ai

[Install]
WantedBy=multi-user.target
```

启动命令：
```bash
sudo systemctl daemon-reload
sudo systemctl enable binance-ai-analyzer
sudo systemctl start binance-ai-analyzer

# 查看日志
sudo journalctl -u binance-ai-analyzer -f
```

---

## ⚙️ 环境变量配置

### 必需变量（部署前必须设置）

| 变量名 | 说明 | 示例值 |
|--------|------|--------|
| `BINANCE_API_KEY` | 币安期货API密钥 | `dFjsd1234...` |
| `BINANCE_API_SECRET` | 币安期货API密钥秘密 | `fhsdk5678...` |
| `DEEPSEEK_API_KEY` | DeepSeek AI API密钥 | `sk-c28...` |

### 可选变量

| 变量名 | 默认值 | 说明 |
|--------|--------|------|
| `REFRESH_INTERVAL` | `2` | K线数据刷新间隔（秒） |
| `KLINE_INTERVAL` | `1h` | K线时间间隔（1m, 5m, 15m, 30m, 1h, 4h, 1d） |
| `SERVER_PORT` | `8501` | Streamlit服务器端口 |
| `SERVER_ADDRESS` | `0.0.0.0` | 服务器监听地址 |
| `APP_TITLE` | `币安期货AI分析系统` | 应用标题 |
| `DATABASE_PATH` | `./analysis_cache.db` | SQLite数据库路径 |
| `DEBUG_MODE` | `false` | 调试模式（true/false） |

---

## 📊 使用指南

### 首次访问
1. 打开浏览器访问 `http://localhost:8501`（本地）或 `http://your-server:8501`（远程）
2. 系统自动加载账户信息和持仓数据
3. K线图自动刷新（默认2秒）

### 功能说明

#### 📱 账户概览面板
显示关键账户指标：
- **钱包余额**: 总资产值
- **保证金余额**: 持仓占用保证金
- **可用余额**: 新开仓可用资金
- **未实现盈亏**: 持仓的浮动盈亏
- **总回报率**: 累计收益百分比

#### 📍 仓位监控表格
- 实时更新所有持仓信息
- 支持排序和搜索
- 显示方向、数量、开仓价、标记价、盈亏

#### 🤖 智能分析建议
- 自动显示最近AI分析结果
- **注意**: 不支持手动请求（后台每5分钟自动更新）
- 包含入场建议、方向、仓位大小等

#### 📊 今日分析摘要
- 总分析数、覆盖币种数、整体胜率、平均盈亏
- 市场分析：7天波动率、资金费率趋势
- 实时更新，快速掌握市场状况

#### 📜 历史命中率分析
- 整体胜率统计
- 历史记录（按时间排序）
- 支持标记命中/失误和输入盈亏数据

---

## 📁 项目结构

```
binance-ai-analyzer/
├── main.py                      # 📱 Streamlit UI应用
├── utils.py                     # 🔧 API客户端和分析逻辑
├── database.py                  # 💾 SQLite数据库操作
├── config.py                    # ⚙️ 配置管理
├── requirements.txt             # 📦 Python依赖
├── README.md                    # 📖 本文档
├── QUICKSTART.md                # 🚀 快速开始指南
├── FEATURES.md                  # ✨ 功能详细说明
├── BUG_REPORT.md                # 🐛 故障排除指南
├── .gitignore                   # 🚫 Git忽略文件
├── .env.example                 # 📋 环境变量示例
├── .streamlit/
│   └── config.toml              # 🎨 Streamlit配置
├── scripts/
│   ├── install_linux.sh         # 🐧 Linux自动安装脚本
│   ├── deploy.sh                # 🚀 部署脚本
│   └── systemd-service.sh       # 🛠️ Systemd配置生成
├── docker/
│   ├── Dockerfile               # 🐳 Docker镜像
│   └── docker-compose.yml       # 🐳 Docker Compose
└── tests/                       # ✅ 单元测试
    ├── test_utils.py
    └── test_database.py
```

---

## 🐳 Docker部署

### 使用Docker Compose（推荐）

```bash
# 1. 创建 .env 文件
cat > .env << EOF
BINANCE_API_KEY=your-key
BINANCE_API_SECRET=your-secret
DEEPSEEK_API_KEY=your-key
EOF

# 2. 启动容器
docker-compose up -d

# 3. 查看日志
docker-compose logs -f

# 4. 停止容器
docker-compose down
```

### 手动构建

```bash
# 构建镜像
docker build -t binance-ai-analyzer .

# 运行容器
docker run -d \
  -p 8501:8501 \
  -e BINANCE_API_KEY="your-key" \
  -e BINANCE_API_SECRET="your-secret" \
  -e DEEPSEEK_API_KEY="your-key" \
  -v $(pwd)/data:/app/data \
  --name binance-analyzer \
  binance-ai-analyzer

# 查看日志
docker logs -f binance-analyzer
```

---

## 🔒 安全最佳实践

### API密钥安全
- ✅ **必须** 使用环境变量存储密钥
- ✅ 不要将密钥提交到Git（添加到 .gitignore）
- ✅ 使用 `.env` 文件管理本地配置
- ✅ 定期轮换API密钥
- ✅ 币安侧禁用API提现权限

### 服务器安全
- ✅ 使用防火墙限制访问端口
- ✅ 启用HTTPS（使用Let's Encrypt）
- ✅ 使用Nginx/Apache反向代理
- ✅ 定期更新系统和依赖包
- ✅ 启用SSH密钥认证

### 网络安全
- ✅ 不要在公网暴露端口
- ✅ 使用VPN或SSH隧道
- ✅ 限制IP白名单访问

---

## 📈 性能配置

### 低配置服务器（512MB RAM）
```bash
REFRESH_INTERVAL=5
KLINE_INTERVAL=4h
```

### 标准配置（1-2GB RAM）
```bash
REFRESH_INTERVAL=2
KLINE_INTERVAL=1h
```

### 高配置服务器（2GB+）
```bash
REFRESH_INTERVAL=1
KLINE_INTERVAL=15m
```

---

## 🐛 故障排除

### 常见问题

**问题：币安API连接失败**
- 检查网络连接：`ping fapi.binance.com`
- 验证API密钥是否正确
- 确认币安账户有期货权限
- 检查服务器时间同步

**问题：AI分析显示JSON错误**
- 系统已配置自动重试（3次）
- 检查DeepSeek API额度
- 查看应用日志获取详细信息

**问题：K线图加载缓慢**
- 增加 `REFRESH_INTERVAL` 值（如改为5秒）
- 减少监听币种数量
- 检查网络带宽

**问题：数据库文件过大**
- SQLite自动清理7天外数据
- 可删除 `analysis_cache.db` 重新开始

### 查看日志

```bash
# 本地开发
streamlit run main.py --logger.level=debug

# Docker容器
docker logs binance-analyzer

# Systemd服务
sudo journalctl -u binance-ai-analyzer -f -n 100
```

---

## 🤝 贡献指南

欢迎提交Issue和Pull Request！

### 代码规范
- 遵循 [PEP 8](https://www.python.org/dev/peps/pep-0008/)
- 使用 `black` 格式化代码
- 使用 `flake8` 检查质量
- 添加类型注解和文档字符串

```bash
# 代码检查
black *.py
flake8 *.py --max-line-length=100
```

---

## 📄 许可证

本项目采用 [MIT License](LICENSE)

---

## ⚠️ 免责声明

本应用提供的所有数据和分析建议**仅供参考**。使用者应：
- ✅ 自行进行充分的技术分析和风险评估
- ✅ 承担所有使用本应用带来的风险
- ✅ 不将此作为投资建议的唯一依据
- ⚠️ 杠杆交易风险极高，可能导致全部资金损失

**作者不对任何交易损失负责。**

---

## 📞 获取帮助

- 📖 [项目文档](docs/)
- 🚀 [快速开始](QUICKSTART.md)
- ✨ [功能说明](FEATURES.md)
- 🐛 [故障排除](BUG_REPORT.md)
- 💬 [GitHub Issues](https://github.com/guanzihao166/binance_api/issues)

---

**开发维护** • **版本 v3.0** • **更新于 2026-02-20**
