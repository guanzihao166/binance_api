# 币安期货AI分析系统 - 快速开始指南 🚀

## ⏱️ 5分钟快速开始

### 1️⃣ 获取API密钥 (2分钟)

#### 币安期货API
1. 访问 https://www.binance.com 登录账户
2. 点击 **账户 → API管理**
3. 点击 **创建API KEY**
4. WebSocket Streams 选择 **启用**
5. Futures / 杠杆交易所权限 选择 **启用**
6. 确认创建并复制 **API Key** 和 **Secret Key**

#### DeepSeek AI API
1. 访问 https://api.deepseek.com
2. 点击 **个人资料 → API密钥管理**
3. 点击 **创建新API密钥** 并复制

### 2️⃣ 本地安装 (2分钟)

#### Windows
```powershell
git clone https://github.com/guanzihao166/binance_api.git
cd binance_api
python -m venv venv
.\venv\Scripts\activate
pip install -r requirements.txt

$env:BINANCE_API_KEY="your-key"
$env:BINANCE_API_SECRET="your-secret"
$env:DEEPSEEK_API_KEY="your-deepseek-key"

streamlit run main.py
```

#### Linux/macOS
```bash
git clone https://github.com/guanzihao166/binance_api.git
cd binance_api
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

export BINANCE_API_KEY="your-key"
export BINANCE_API_SECRET="your-secret"
export DEEPSEEK_API_KEY="your-deepseek-key"

streamlit run main.py
```

**访问** `http://localhost:8501`

### 3️⃣ 首次体验 (1分钟)

系统自动：
1. ✅ 加载账户信息（钱包余额、保证金等）
2. ✅ 显示所有活跃持仓
3. ✅ 绘制K线图表
4. ✅ 后台预加载AI分析（每5分钟更新）

---

## 📊 主要界面说明

### 📱 账户概览
- 钱包余额、可用资金、保证金占用
- 未实现盈亏、总回报率

### 📍 持仓表格
- 所有活跃持仓的完整信息
- 方向、数量、价格、盈亏

### 🤖 AI分析 
后台自动生成（每5分钟更新一次）：
- 是否建议入场
- 做多/做空方向
- 轻仓/重仓建议
- 入场价/止损/止盈
- 支撑位/压力位

### 📈 市场分析摘要
- 今日分析数、覆盖币种
- 整体胜率、平均盈亏
- 7天走势分析

### 📜 历史命中率
- 完整分析历史
- 标记命中/失误
- 输入盈亏数据
- 自动计算胜率

---

## ⚙️ 常见配置

### 修改刷新频率

```bash
# 快速（1秒）
export REFRESH_INTERVAL=1

# 标准（2秒） - 推荐
export REFRESH_INTERVAL=2

# 低频（5秒）
export REFRESH_INTERVAL=5
```

### 修改K线时间框架

```bash
export KLINE_INTERVAL=5m    # 5分钟
export KLINE_INTERVAL=1h    # 1小时（推荐）
export KLINE_INTERVAL=4h    # 4小时
```

### 使用.env文件

创建根目录的 `.env` 文件：

```bash
BINANCE_API_KEY=your-key
BINANCE_API_SECRET=your-secret
DEEPSEEK_API_KEY=your-key
REFRESH_INTERVAL=2
KLINE_INTERVAL=1h
```

然后：
```bash
source .env
streamlit run main.py
```

---

## 🔧 解决常见问题

### API连接失败
```
❌ 无法连接到币安API
```
- 检查网络：`ping fapi.binance.com`
- 验证API密钥是否正确
- 确保币安账户已启用期货权限

### AI分析报错
```
⚠️ JSON解析失败
```
- 等待1-2分钟，系统自动重试
- 检查DeepSeek API密钥和账户余额
- 查看日志：`streamlit run main.py --logger.level=debug`

### K线加载缓慢
- 增加刷新间隔：`export REFRESH_INTERVAL=5`
- 减少监听的币种数量
- 检查网络速度

### 端口被占用
```bash
# 使用不同端口
streamlit run main.py --server.port 8502
```

---

## 🚀 部署到服务器

### 自动部署（推荐）
```bash
sudo bash <(curl -s https://raw.github.../install_linux.sh)
```

### 手动部署
参考 [README.md - Linux服务器部署](README.md#-linux服务器部署)

---

## 💡 使用建议

### ✅ 最佳实践
- 定期检查日志发现问题
- 监控API调用避免超额
- 定期备份 `analysis_cache.db`
- 保持依赖包更新
- 使用Nginx反向代理（生产环境）

### ⚠️ 注意事项
- 不要将API密钥提交到Git
- 定期轮换API密钥
- 杠杆交易风险极高
- 牢记这是辅助工具，不是购房建议

---

## 📚 更多资源

- 📖 [完整文档](README.md)
- 🐛 [故障排除](BUG_REPORT.md)
- ✨ [功能详解](FEATURES.md)
- 💬 [GitHub Issues](https://github.com/guanzihao166/binance_api/issues)

---

## 🎉 完成！

你现在拥有一个专业的AI交易分析系统！

**祝你使用愉快！如果有帮助请给个⭐ Star！**

*最后更新：2026-02-20*
