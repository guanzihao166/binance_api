# 🚀 快速运行指南

> **如果你刚部署好应用，找不到 streamlit 命令，请按照本指南解决！**

## 问题诊断

```bash
$ streamlit run main.py
streamlit: command not found
```

这是因为 streamlit 被安装在了虚拟环境中，而不是系统全局环境。

---

## ✅ 解决方案

### **方法 1：运行便捷脚本（最简单 ⭐ 推荐）**

```bash
# 进入项目目录
cd /path/to/binance_api

# 运行启动脚本
./run.sh
```

这个脚本会自动：
- 检测和创建虚拟环境（如果不存在）
- 安装所有依赖
- 启动应用

---

### **方法 2：使用虚拟环境中的 streamlit**

```bash
# 进入项目目录
cd /path/to/binance_api

# 直接使用虚拟环境中的 streamlit
./venv/bin/streamlit run main.py
```

或者如果是部署脚本创建的环境：
```bash
# 运行启动脚本（部署脚本已为你创建）
./start.sh
```

---

### **方法 3：手动激活虚拟环境**

这是标准的 Python 虚拟环境做法：

```bash
# 1. 进入项目目录
cd /path/to/binance_api

# 2. 激活虚拟环境
source venv/bin/activate

# 虚拟环境已激活，你会看到 (venv) 前缀
(venv) $ 

# 3. 运行应用
streamlit run main.py

# 4. 退出虚拟环境（可选）
deactivate
```

---

## 🌐 访问应用

无论使用哪种方法，应用启动后可以访问：

```
http://localhost:8501
```

或者从远程访问（如果在服务器上）：

```
http://your-server-ip:8501
```

---

## 📋 常见问题

### Q1: 虚拟环境在哪里？
```bash
ls -la venv/
# 虚拟环境存储在项目目录下的 venv/ 文件夹中
```

### Q2: 虚拟环境占用多少空间？
```bash
du -sh venv/
# 通常 100-200 MB，取决于依赖包
```

### Q3: 如何卸载虚拟环境？
```bash
rm -rf venv/
# 删除虚拟环境文件夹即可，不影响应用代码
```

### Q4: 为什么需要虚拟环境？
虚拟环境的优点：
- ✅ 隔离项目依赖，不污染系统环境
- ✅ 可以为不同项目使用不同的包版本
- ✅ 便于部署和版本管理
- ✅ 容易清理和迁移

---

## 🔧 故障排除

### 如果 `./run.sh` 权限不足

```bash
# 给脚本添加可执行权限
chmod +x run.sh

# 然后再运行
./run.sh
```

### 如果虚拟环境损坏

```bash
# 删除旧虚拟环境
rm -rf venv/

# 重新运行 install_linux.sh 或 run.sh
# 脚本会自动重建虚拟环境
./install_linux.sh
```

### 如果 pip 安装超时

```bash
# 使用国内镜像加速（阿里云）
pip config set global.index-url https://mirrors.aliyun.com/pypi/simple/

# 然后重新运行脚本
./run.sh
```

---

## 📚 相关文档

- **[README.md](README.md)** - 项目完整文档
- **[QUICKSTART.md](QUICKSTART.md)** - 快速开始指南  
- **[requirements.txt](requirements.txt)** - 项目依赖列表

---

## 💡 提示

- 第一次运行会比较慢，因为要安装依赖
- 之后的启动会很快
- 按 `Ctrl+C` 可以停止应用
