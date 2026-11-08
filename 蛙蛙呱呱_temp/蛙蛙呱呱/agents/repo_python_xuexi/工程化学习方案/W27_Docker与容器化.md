# W27：Docker 与容器化（1/26 — 2/1）

> 🎯 **本周目标**：你的代码在你电脑上能跑（W1-W26）。但别人的电脑呢？服务器上呢？CI 里呢？Docker 用一行代码解决"在不同环境中运行"的问题——不是"保证代码正确"，是"保证环境一致"。学完这周，你的项目有一个 `Dockerfile`——一行 `docker run` 就能在任意机器上跑通。
>
> 📎 **本周主课**：行业数据深耕——行业 KPI/业务逻辑/数据源
>
> 🏢 **本周场景**：鲜果多换了一台新服务器——Ubuntu 系统。你把 Python 脚本拷过去——`pip install` 炸了——某个包需要系统级的 C 库（`libffi-dev` 之类的）。你花了两天配环境。Docker 就是解决这个的——"在你的电脑上能跑"⇾"在 Docker 里能跑"⇾"在任何地方都能跑"。

---

## D1（周一 1/26）：Docker 是什么——不深入原理，先理解"它解决什么问题"


---

---

### Docker 的安装与验证——Windows 环境

**Docker Desktop for Windows——安装后验证三步:**

```bash
# 1. 验证 Docker 安装
docker --version

# 2. 验证 Docker 能运行容器
docker run hello-world

# 3. 构建并运行你的项目
cd xianguoduo
docker build -t xianguoduo-analysis .
docker run --rm xianguoduo-analysis
```

**常见 Windows 安装问题:**

| 问题 | 原因 | 修复 |
|------|------|------|
| Docker Desktop 启动失败 | WSL 2 未安装或未启用 | 安装 WSL 2——Docker Desktop 依赖它 |
| docker build 报 permission denied | Windows 文件权限 | 确保项目目录在 WSL 文件系统中——不在 /mnt/c 下（性能差且权限问题多） |
| docker run 报 port already in use | 端口被占用 | 改 docker-compose.yml 中的端口映射——如 "5433:5432" |

**验证清单——全部通过——Docker 环境就绪:**
- [ ] `docker --version` 输出正常
- [ ] `docker run hello-world` 输出 "Hello from Docker!"
- [ ] `docker build -t xianguoduo .` 成功构建——无报错
- [ ] `docker run --rm xianguoduo` 全流程跑通——输出结果在宿主机的 output/ 目录


---

---

### Docker 面试速查卡——完整版

**Q1:** Docker 的三个核心概念——Dockerfile/Image/Container？

> **A:** Dockerfile = 环境配置说明书——用代码写的——定义 Python 版本/系统依赖/文件结构。Image = Dockerfile 构建后的产物——一个冻结的环境快照。Container = Image 的运行实例——隔离的、用完即抛的进程。

**Q2:** Docker 和虚拟机的两个关键区别？

> **A:** (1) 虚拟机虚拟整个 OS——含内核——几 GB——启动 30s-2min。Docker 共享宿主机内核——只隔离应用——几百 MB——启动 1-3s。(2) Docker 对数据分析师的核心价值——"环境一致性"——不是"服务器运维"。新同事 clone 后——docker-compose up 一键启动——不需要配 Python 环境/装系统库/处理跨平台差异。

**Q3:** Dockerfile 为什么要先 COPY requirements.txt 再 COPY . .？

> **A:** 利用 Docker 的层缓存。只要 requirements.txt 不变——pip install 这层就不会重新执行——省掉每次构建都重新下载依赖的 2 分钟。代码的任何改动只影响 COPY . . 之后的层——不影响 pip install。

**Q4:** 数据持久化——容器删了数据库还在吗？

> **A:** 在——数据库数据用 named volume 持久化——不随容器删除。output/ 目录用 bind mount 挂载到宿主机——容器跑完后可以在宿主机查看输出文件。Docker 不是数据丢了就丢了——是通过 volume 机制保证数据持久化。

**Q5:** 环境变量的三级优先级？

> **A:** 代码默认值（最低）-> .env 文件 -> 命令行覆盖（最高）。同一个 Docker 镜像——通过环境变量切换行为——不需要为日报/周报/月报建三个镜像。

**W27 面试 30 秒版:**

> "我用 Docker 保证分析环境的可复现。Dockerfile 定义了 Python 版本/系统依赖/代码复制顺序——利用了层缓存优化构建速度。docker-compose.yml 定义了多服务编排——app+db 一键启动——含健康检查——数据用 volume 持久化。所有配置通过环境变量传入——三级优先级——同一个镜像日报/周报/月报切换。CI 中四层 Docker 验证——构建+冒烟+集成+安全扫描——任何一层失败不允许合并。新同事 clone 后——不需要配环境——一行 docker-compose up 全搞定。"


---

---

### Docker 的核心概念——用数据分析师能理解的语言

**Docker 不是虚拟机——它不虚拟整个操作系统。它只是隔离你的应用和它的依赖。**

说人话——你把你的 Python 代码 + Python 解释器 + 所有依赖包 + 所有系统库——打包成一个镜像文件。这个镜像在任何安装了 Docker 的机器上都能跑——Windows/Mac/Linux 都行。

**三个核心概念——面试时必须能说清楚:**

| 概念 | 一句话解释 | 类比 |
|------|----------|------|
| Dockerfile | 环境配置说明书——用代码写的——不是 Word 写的 | requirements.txt 的升级版——不仅定义 Python 包——还定义 Python 版本/系统库/文件结构 |
| Image（镜像） | Dockerfile 构建后的产物——一个"冻结的环境快照" | 一个 zip 包——含你的代码+Python+所有依赖——可以在任何地方解压运行 |
| Container（容器） | Image 的运行实例——隔离的、用完即抛的 | 从 zip 包启动的进程——跑完后可以删掉——不留任何痕迹 |

**Dockerfile 的最小版本——数据分析项目:**

```dockerfile
FROM python:3.10-slim
RUN apt-get update && apt-get install -y libgomp1 && rm -rf /var/lib/apt/lists/*
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
CMD ["python", "main.py"]
```

**面试时——面试官问"你用过 Docker 吗"——你不能只说"用过——docker build && docker run"——你说——"我用 Docker 来保证分析环境的可复现。Dockerfile 定义了 Python 版本、系统依赖、项目代码的复制顺序。镜像构建后——任何人——不管用 Windows/Mac/Linux——一行 docker run 就能跑通我的分析管线。我把 Docker 集成到了 CI 中——每次 push 自动验证镜像能成功构建。"**

> 📓 今日主课：行业数据——理解业务逻辑

---

### 🔴 认知冲突

你听说过 Docker——"轻量级虚拟机"、"容器化"、"Kubernetes"。你觉得这是运维的东西——数据分析师不需要。

但你每次换电脑都要花半天配环境——装 Python、装依赖、处理"这个库在 Windows/Linux 上的行为不同"。Docker 让你**配置一次环境——然后任何地方都能用**。

---

### 📖 核心原理

**Docker 不是虚拟机——它不虚拟整个操作系统。它只是"隔离"你的应用和它的依赖。**

说人话：你把你的 Python 代码 + Python 解释器 + 所有依赖包 + 所有系统库——打包成一个"镜像文件"。这个镜像在任何安装了 Docker 的机器上都能跑——Windows/Mac/Linux 都行。

**Dockerfile = "环境配置说明书"——用代码写的，不是用 Word 写的。**

```dockerfile
# Dockerfile——数据分析项目的最小版本
FROM python:3.10-slim

# 安装系统级依赖（pandas/matplotlib 需要的底层库）
RUN apt-get update && apt-get install -y \
    libgomp1 \
    && rm -rf /var/lib/apt/lists/*

# 设置工作目录
WORKDIR /app

# 先复制依赖文件——利用 Docker 缓存层
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 再复制项目代码
COPY . .

# 默认命令——容器启动时自动执行
CMD ["python", "main.py"]
```

---

### ✍️ 动手练习

1. 安装 Docker Desktop（Windows 版）。
2. 创建 `Dockerfile`——放在鲜果多项目根目录。
3. 构建镜像：`docker build -t xianguoduo-analysis .`
4. 运行容器：`docker run --rm xianguoduo-analysis`
5. 如果跑通了——你的代码现在在任何有 Docker 的机器上都能跑了。
6. `git add Dockerfile && git commit -m "add Dockerfile for reproducible execution" && git push`

---

## D2（周二 1/27）：docker-compose——多服务编排


---

---

### Docker 的数据持久化策略——面试必问

**Docker 容器是"用完即抛"的——容器删除后——容器内的所有数据都消失。怎么保留数据？**

**三种数据持久化方式——从简单到复杂:**

| 方式 | 语法 | 数据存在哪 | 什么时候用 |
|------|------|----------|----------|
| bind mount | `-v ./output:/app/output` | 宿主机目录——你手动管理 | 输出文件/日志——容器跑完后想在宿主机查看 |
| named volume | `-v pgdata:/var/lib/postgresql/data` | Docker 管理的卷——`/var/lib/docker/volumes/` | 数据库数据——不想手动管理路径——交给 Docker |
| tmpfs | `--tmpfs /app/cache` | 内存——容器停止即消失 | 临时缓存——不需要持久化——但需要快速读写 |

**面试时——面试官问"容器删了数据库还在吗"——你回答——"数据库数据用 named volume 持久化——不随容器删除。output/ 目录用 bind mount 挂载到宿主机——容器跑完后可以在宿主机查看输出文件。Docker 不是'数据丢了就丢了'——是通过 volume 机制保证数据持久化。"**


---

---

### docker-compose 的完整实战——数据分析项目的多服务编排

```yaml
# docker-compose.yml——鲜果多数据分析项目
version: '3.8'
services:
  app:
    build: .
    image: xianguoduo-analysis:latest
    depends_on:
      db:
        condition: service_healthy  # 等待 db 健康检查通过
    environment:
      - DATABASE_URL=postgresql://postgres:postgres@db:5432/xianguoduo
      - REPORT_TYPE=${REPORT_TYPE:-daily}
      - LOG_LEVEL=${LOG_LEVEL:-INFO}
    volumes:
      - ./output:/app/output        # 输出目录挂载——容器内写入——宿主机可见
      - ./data:/app/data            # 数据目录挂载
    command: python main.py

  db:
    image: postgres:15
    environment:
      POSTGRES_DB: xianguoduo
      POSTGRES_USER: postgres
      POSTGRES_PASSWORD: postgres
    ports:
      - "5432:5432"
    volumes:
      - pgdata:/var/lib/postgresql/data
      - ./src/sql/init:/docker-entrypoint-initdb.d  # 初始化 SQL——首次启动自动执行
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U postgres"]
      interval: 5s
      timeout: 5s
      retries: 5

volumes:
  pgdata:  # 持久化数据库数据——容器重启不丢失
```

**核心设计决策——面试时必须能解释:**

1. **depends_on + healthcheck:** 不是"等 db 容器启动"——是"等 db 容器启动且 PostgreSQL 准备好接受连接"。没有 healthcheck——app 可能在 PostgreSQL 还没 ready 时就尝试连接——启动失败。

2. **volumes 挂载:** output/ 和 data/ 挂载到宿主机——容器删除后数据不丢失。数据库用 named volume (pgdata)——Docker 管理——容器重启数据不丢失。

3. **环境变量:** REPORT_TYPE 和 LOG_LEVEL 通过 ${VAR:-default} 语法——有默认值——运行时可覆盖: `REPORT_TYPE=weekly docker-compose up`。

4. **初始化 SQL:** `docker-entrypoint-initdb.d` 目录——PostgreSQL 镜像首次启动时自动执行目录内的 .sql 文件——创建表——插入初始数据——不需要手动操作。

> 📓 今日主课：数据源识别——内部数据+外部数据+第三方 API

---

### 📖 核心原理

**如果项目依赖数据库（MySQL/PostgreSQL）——docker-compose 一句话启动"应用 + 数据库"：**

```yaml
# docker-compose.yml
version: '3.8'
services:
  app:
    build: .
    depends_on:
      - db
    volumes:
      - ./output:/app/output   # 挂载输出目录——容器内写入，宿主机可见
  db:
    image: postgres:15
    environment:
      POSTGRES_DB: xianguoduo
    ports:
      - "5432:5432"
```

`docker-compose up`——应用 + 数据库同时启动。`docker-compose down`——同时关闭。面试时面试官问"了解 Docker 吗"——你不仅能说 Dockerfile，还能说 docker-compose 的多服务编排——这是 L5 的硬指标。

---

### ✍️ 动手练习

1. 创建 `docker-compose.yml`——至少含你的 app + 一个数据库服务（即使你现在不用数据库——知道这个模式就行）。
2. 在 README 的"快速开始"章节——加 Docker 启动方式（一行命令替代四行手动操作）。
3. `git add docker-compose.yml README.md && git commit -m "add docker-compose for multi-service orchestration" && git push`

---

## D3（周三 1/28）：环境变量与配置管理——让 Docker 知道"今天是跑日报还是周报"


---

---

### 环境变量管理的工程化实践——从硬编码到 .env 文件

**.env 文件——所有环境变量的默认值——不被 git 追踪——每个环境独立维护:**

```bash
# .env.example——提交到 Git——作为模板
REPORT_TYPE=daily
DATABASE_URL=postgresql://localhost:5432/xianguoduo
LOG_LEVEL=INFO
OUTPUT_DIR=output
SAMPLE_SIZE=10000
ALERT_EMAIL_TO=boss@xianguoduo.com
```

```bash
# .env——不提交到 Git（在 .gitignore 中）——每个环境独立配置
REPORT_TYPE=daily
DATABASE_URL=postgresql://prod-db:5432/xianguoduo  # 生产环境——真实数据库
LOG_LEVEL=WARNING
ALERT_EMAIL_TO=real-boss@xianguoduo.com
```

**使用方式:**

```bash
# docker-compose 自动读取 .env 文件
docker-compose up

# 或手动指定 env file
docker-compose --env-file .env.production up

# 或命令行覆盖单个变量
REPORT_TYPE=weekly docker-compose up
```

**环境变量的三级优先级——从低到高:**

1. **代码中的默认值（最低）:** `os.getenv('REPORT_TYPE', 'daily')`
2. **.env 文件:** `REPORT_TYPE=weekly`
3. **命令行覆盖（最高）:** `REPORT_TYPE=monthly docker-compose up`

**这个优先级设计确保——不改代码——不改 .env——就能临时切换行为。** 面试时——面试官问"你怎么管理不同环境的配置"——你回答——"三级优先级——代码默认值最低——.env 文件中间——命令行覆盖最高。同一个 Docker 镜像——通过环境变量切换行为——不需要为日报/周报/月报建三个镜像。"


---

---

### 环境变量配置——从硬编码到可配置

**硬编码的配置在 Docker 里应该变成环境变量:**

```python
import os

# 所有"在不同场景下可能变化"的配置——通过环境变量传入——代码里不硬编码
REPORT_TYPE = os.getenv('REPORT_TYPE', 'daily')        # daily / weekly / monthly
DB_URL = os.getenv('DATABASE_URL', 'sqlite:///data.db')
LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO')
OUTPUT_DIR = os.getenv('OUTPUT_DIR', 'output')
SAMPLE_SIZE = int(os.getenv('SAMPLE_SIZE', '10000'))    # 开发时用小样本——生产用全量
```

**运行容器时通过 -e 传入环境变量:**

```bash
# 跑日报（默认）
docker run --rm xianguoduo-analysis

# 跑周报——覆盖 REPORT_TYPE
docker run --rm -e REPORT_TYPE=weekly xianguoduo-analysis

# 跑月报——用生产数据库
docker run --rm -e REPORT_TYPE=monthly -e DATABASE_URL=postgresql://prod:5432/xianguoduo xianguoduo-analysis
```

**同一个镜像——通过环境变量切换行为——不需要为日报/周报/月报建三个镜像。** 面试时——面试官问"你怎么处理不同环境的配置"——你回答——"所有配置通过 os.getenv() 读取——有合理默认值。同一个 Docker 镜像——通过 -e 环境变量切换行为——不需要为不同场景建不同镜像。"

> 📓 今日主课：业务指标——行业 KPI 体系

---

### 📖 核心原理

**硬编码配置（如 `REPORT_TYPE = 'daily'`）在 Docker 里应该变成环境变量：**

```python
import os
REPORT_TYPE = os.getenv('REPORT_TYPE', 'daily')  # 默认日报
```

然后运行容器时：`docker run -e REPORT_TYPE=weekly xianguoduo-analysis`——自动跑周报而不是日报。

所有"在不同场景下可能变化"的配置——数据库连接串、API 密钥、报表类型——都通过环境变量传入。代码里不留任何"可能因为环境变化而需要改"的值。

---

### ✍️ 动手练习

1. 扫描你的代码——找出至少 3 个硬编码的配置值。
2. 全部改为 `os.getenv()` 读取环境变量，并设合理的默认值。
3. 更新 Dockerfile 中的 `CMD`——允许通过环境变量覆盖默认行为。
4. `git add . && git commit -m "externalize config to environment variables" && git push`

---

## D4（周四 1/29）：将 Docker 集成到 CI——每次 push 自动验证镜像能构建


---

---

### Docker CI 的完整配置——从构建到冒烟测试

```yaml
# .github/workflows/ci.yml——Docker 部分
- name: Build Docker image
  run: docker build -t xianguoduo-analysis .

- name: Smoke test
  run: |
    docker run --rm xianguoduo-analysis python -c "
import pandas; import numpy; from pathlib import Path
print('Docker smoke test PASSED')
print(f'pandas {pandas.__version__}')
print(f'numpy {numpy.__version__}')
"

- name: Integration test with docker-compose
  run: |
    docker-compose up -d db
    for i in $(seq 1 10); do
      if docker-compose exec db pg_isready -U postgres; then break; fi
      echo "Waiting for PostgreSQL..."; sleep 3
    done
    docker-compose run --rm app python main.py --dry-run
    docker-compose down

- name: Security scan (optional)
  uses: aquasecurity/trivy-action@master
  with:
    image-ref: xianguoduo-analysis:latest
    format: table
    exit-code: 1
    severity: CRITICAL,HIGH
```

**CI 中 Docker 的完整验证链——从浅到深——4 层:**

| 层 | 验证什么 | 耗时 | 失败意味着什么 |
|------|---------|------|-------------|
| docker build | Dockerfile 语法——基础镜像——pip install | ~2min | 环境定义有问题 |
| smoke test | Python 能 import 核心库——无系统库缺失 | ~10s | 基础镜像缺少系统库 |
| integration test | 多服务协作——app 能连 db | ~30s | docker-compose 配置或健康检查有问题 |
| security scan | 镜像中的已知漏洞（CVE） | ~30s | 某个依赖有已知安全漏洞——需要升级 |

**面试时——你说"CI 里不只是 docker build——是四层验证——从构建到冒烟到集成到安全扫描。任何一层失败——CI 标红——不允许合并。"**


---

---

### Docker CI 集成的完整配置

**在 GitHub Actions 中加 Docker 构建验证——确保每次 push 镜像都能成功构建:**

```yaml
# .github/workflows/ci.yml 中加:
- name: Build Docker image
  run: docker build -t xianguoduo-analysis .

- name: Run smoke test in Docker
  run: docker run --rm xianguoduo-analysis python -c "import pandas; print('Docker OK')"

- name: Test with docker-compose
  run: |
    docker-compose up -d db
    sleep 10  # 等待 PostgreSQL ready
    docker-compose run --rm app python -c "from src.data.io import load_orders; print('DB connection OK')"
    docker-compose down
```

**CI 中 Docker 的三层验证——从浅到深:**

| 层次 | 验证什么 | 耗时 | 如果失败——说明什么 |
|------|---------|------|------------------|
| docker build | Dockerfile 语法正确——基础镜像可拉取——依赖可安装 | ~2min | Dockerfile 有语法错误——或 pip install 失败 |
| smoke test | 镜像能启动——Python 能 import 核心库 | ~10s | 基础镜像缺少系统库——import pandas 失败 |
| docker-compose test | 多服务能协作——app 能连接 db | ~30s | db 健康检查配置错误——或连接参数不对 |

**面试时——面试官问"你的 CI 里有没有 Docker"——你回答——"有——三层验证。第一层——docker build——确认镜像能构建。第二层——smoke test——确认 Python 能 import 核心库。第三层——docker-compose——确认多服务能协作。任何一层失败——CI 标红——不允许合并。"**

> 📓 今日主课：行业 case study

---

### 📖 核心原理

**在 GitHub Actions 中加一个 step——`docker build .`——确认每次 push 后 Docker 镜像能成功构建。**

如果构建失败——说明有人引入了一个系统级依赖但没更新 Dockerfile。CI 会拦下来。

---

### ✍️ 动手练习

1. 在 `.github/workflows/test.yml` 中加 `docker build .` 步骤。
2. push——确认 CI 全绿（ruff + mypy + pytest + docker build）。

---

## D5（周五 1/30）：Docker 面试准备——你不需要是 DevOps，但你需要能说清楚


---

---

### Docker 面试追问三连——提前准备

**追问 1: "你的 Dockerfile 为什么要先 COPY requirements.txt 再 COPY . .——不能一起 COPY 吗？"**

> "这是为了利用 Docker 的层缓存。Docker 构建时——每一行 RUN/COPY 生成一个层——如果层的输入没变——Docker 复用缓存。COPY requirements.txt 单独一行——只要 requirements.txt 不变——pip install 这层就不会重新执行——省掉每次构建都重新下载依赖的 2 分钟。如果 COPY . . 放在前面——代码的任何改动都会导致 pip install 重新执行——浪费构建时间。"

**追问 2: "docker-compose 和 Dockerfile 有什么区别？什么时候用哪个？"**

> "Dockerfile 定义单个镜像的构建过程——docker-compose 定义多个容器的协作关系。如果只有一个 Python 应用——不需要数据库——Dockerfile + docker run 就够了。如果有应用+数据库+缓存——docker-compose 定义它们之间的网络/依赖/启动顺序。我的项目两者都有——Dockerfile 定义应用的构建——docker-compose.yml 定义应用+数据库的协作。"

**追问 3: "你会在生产环境用 Docker 部署你的分析项目吗？"**

> "当前阶段——Docker 的核心价值在于'开发环境一致性'——不是'生产环境部署'。新同事 clone 后——docker-compose up 一键启动——不需要配 Python 环境/装系统库/处理跨平台差异。生产环境部署——我会考虑用 Docker——但需要加上健康检查、日志收集、资源限制、多副本——这些是 DevOps 的工作——我作为数据分析师——理解这些概念——但不会在生产环境单独负责 Docker 部署。"


---

---

### Docker 面试全攻略——数据分析师版本

**面试必问 1: "你用过 Docker 吗？说说你的理解。"**

> "我用 Docker 来保证分析环境的可复现。我的项目有 Dockerfile——定义了 Python 版本、系统依赖、代码复制顺序。配合 docker-compose 可以一键启动分析应用和数据库。CI 里每次 push 都会验证镜像能成功构建。这意味着任何人——不管用 Windows/Mac/Linux——docker run 就能跑通我的分析管线。"

**面试必问 2: "Docker 和虚拟机有什么区别？"**

> "虚拟机虚拟了整个操作系统——含内核——一个 VM 几 GB。Docker 共享宿主机的内核——只隔离应用和依赖——一个镜像几百 MB。启动速度——VM 30 秒-2 分钟——Docker 1-3 秒。对数据分析师来说——Docker 的实用价值是'pip install 在我的机器上能跑——在别人的机器上也能跑'——不需要担心'你用的是 Python 3.9 我的是 3.11'。"

**面试必问 3: "docker-compose 是什么——为什么需要它？"**

> "docker-compose 是管理多容器应用的工具。比如我的分析项目依赖 PostgreSQL 数据库——用 docker-compose 可以定义'app 服务'和'db 服务'——一行 docker-compose up 同时启动两个——app 自动等待 db 就绪后再启动。docker-compose down 同时关闭两个。没有 docker-compose——你需要分别手动启动 db 容器——等它启动完成——再启动 app 容器——容易出错。"

**面试追问: "你会在生产环境用 Docker 吗？"**

> "对数据分析师来说——Docker 在'开发环境一致性'上的价值远大于'生产环境部署'。我的核心场景是——新同事 clone 项目后——不需要配 Python 环境——不需要装系统库——不需要处理'Windows 上能跑——Linux 上不能跑'——一行 docker-compose up 全搞定。这比'README 里写六步手动操作'可靠得多。"

> 📓 今日主课：行业数据综合

---

### 📖 核心原理

**数据分析师面试中 Docker 必问的一个问题："你用过 Docker 吗？说说你的理解。"**

你的回答（30 秒版）：
> "我用 Docker 来保证分析环境的可复现。我的项目有 Dockerfile——定义了 Python 版本、系统依赖、项目代码的复制顺序。配合 docker-compose 可以一键启动分析应用和数据库。CI 里每次 push 都会验证镜像能成功构建。这意味着任何人——不管用 Windows/Mac/Linux——`docker run` 就能跑通我的分析管线。"

---

## D6（周六 1/31）：周项目——Docker 化全流程


---

---

### Docker 化全流程的 10 项验收清单

| # | 验收项 | 验证命令 | 通过标准 |
|---|--------|---------|---------|
| 1 | Dockerfile 能构建 | docker build -t xianguoduo . | 构建成功——无报错 |
| 2 | docker run 能跑通 | docker run --rm xianguoduo | 全流程跑通——输出文件在 output/ |
| 3 | docker-compose 能启动 | docker-compose up -d | app+db 同时启动——app 等待 db ready |
| 4 | 环境变量可配置 | REPORT_TYPE=weekly docker-compose up | 同一个镜像——不同行为 |
| 5 | 数据持久化 | docker-compose down && docker-compose up -d | 数据库数据不丢失——output/ 文件在宿主机可见 |
| 6 | CI 中 docker build 通过 | GitHub Actions——最新 run | docker build 步骤绿色 |
| 7 | CI 中 smoke test 通过 | GitHub Actions log | "Docker smoke test PASSED" |
| 8 | Dockerfile 有层缓存优化 | 检查 Dockerfile | COPY requirements.txt 在 COPY . . 之前 |
| 9 | .env.example 提交到 Git | git ls-files | .env.example 在 Git 中——.env 在 .gitignore 中 |
| 10 | README 有 Docker 启动方式 | 打开 README | 一行 docker-compose up 替代四行手动操作 |

**Docker 化完成后的新同事入职体验:**

```bash
git clone https://github.com/yourname/xianguoduo.git
cd xianguoduo
docker-compose up
# 等待 3 分钟——分析完成——输出文件在 output/ 目录
```

**面试时——你展示的就是这个体验——"我刚 clone 了这个项目——一行 docker-compose up——全流程跑通——不需要配 Python 环境——不需要装 PostgreSQL——不需要处理跨平台差异。"**


---

---

### Docker 化全流程的完整交付物清单

**鲜果多项目 Docker 化——5 个文件——全部在 Git 中:**

| 文件 | 作用 | 关键内容 |
|------|------|---------|
| Dockerfile | 应用镜像构建 | FROM python:3.10-slim + apt-get + pip install + COPY |
| docker-compose.yml | 多服务编排 | app + db + volumes + healthcheck + depends_on |
| .env.example | 环境变量模板 | REPORT_TYPE/DATABASE_URL/LOG_LEVEL/ALERT_EMAIL——含注释 |
| .github/workflows/ci.yml | CI Docker 验证 | docker build + smoke test + integration test |
| README.md Docker 章节 | 文档 | docker-compose up 一键启动——替代四行手动操作 |

**新同事入职——不需要配 Python 环境——不需要装 PostgreSQL——不需要处理跨平台差异。** `git clone -> docker-compose up`——两行命令——3 分钟后——分析管线在容器里运行——输出文件在宿主机的 output/ 目录。

**面试时——面试官问"你怎么保证新同事能跑通你的项目"——你回答——"Docker 化——不是 README 里写六步手动操作——是一行 docker-compose up。我刚才展示的——就是新同事入职时的真实体验——clone -> docker-compose up -> 等待 3 分钟 -> 分析完成。"**


---

---

### W27 周项目验收——Docker 化的 L4 标准

**Docker 化全流程的 5 个标准——全部满足——鲜果多项目容器化完成:**

| 标准 | 验证方法 | 面试官看到什么 |
|------|---------|-------------|
| Dockerfile 能构建 | docker build -t xianguoduo . | "不是手写的 Word 文档——是用代码定义的环境" |
| docker run 能跑通全流程 | docker run --rm xianguoduo | "容器启动->分析执行->输出结果->容器销毁——一气呵成" |
| docker-compose 能启动多服务 | docker-compose up -d | "理解多服务架构——不是只会单容器" |
| 环境变量可配置 | docker run -e REPORT_TYPE=weekly | "同一个镜像——不同行为——不给不同场景建不同镜像" |
| CI 中自动验证 | GitHub Actions 含 docker build 步骤 | "不是手动构建——是 CI 自动验证——镜像构建失败不允许合并" |

**W27 面试速查卡——30 秒版:**

> "我用 Docker 保证分析环境的可复现。Dockerfile 定义了 Python 版本/系统依赖/代码复制顺序——docker build 生成镜像——docker run 在任何机器上跑通全流程。docker-compose.yml 定义了多服务编排——app+db 一键启动。所有配置通过环境变量传入——同一个镜像日报/周报/月报切换。CI 中每次 push 自动验证镜像能构建——构建失败不允许合并。新同事 clone 后——不需要配 Python 环境——一行 docker-compose up 全搞定。"

确认鲜果多项目 Docker 化——Dockerfile + docker-compose.yml + 环境变量配置 + CI 验证。`docker run --rm xianguoduo-analysis` 能完整跑通。

---

## D7（周日 2/1）：W27 审计


---

---

### W27 工程化交付物清单

- [ ] Dockerfile——放在项目根目录——docker build . 能成功构建
- [ ] docker-compose.yml——含 app + db + volumes + healthcheck + depends_on
- [ ] .env.example——含所有环境变量的模板——有注释——提交到 Git
- [ ] >= 3 个配置项通过 os.getenv() 读取——有合理默认值
- [ ] CI 中含 docker build + smoke test + integration test——每次 push 自动验证
- [ ] README 快速开始——含 Docker 启动方式（一行替代四行手动操作）
- [ ] docker run --rm <image> 能完整跑通全流程——输出在宿主机 output/ 可见
- [ ] 数据持久化——数据库用 named volume——输出文件用 bind mount
- [ ] Dockerfile 利用了层缓存——COPY requirements.txt 在 COPY . . 之前
- [ ] 环境变量三级优先级——代码默认值 < .env < 命令行覆盖

**W27 Docker 面试速查卡——全部 5 个 Q&A 可以闭卷回答。**


---

---

### W27 闭卷自测 + 工程化交付物清单

**Q1:** Docker 的三个核心概念——Dockerfile/Image/Container——分别是什么？

> **A:** Dockerfile = 环境配置说明书——用代码写的——定义 Python 版本/系统依赖/文件结构。Image = Dockerfile 构建后的产物——一个冻结的环境快照——可以在任何地方运行。Container = Image 的运行实例——隔离的、用完即抛的进程。

**Q2:** Docker 和虚拟机的两个关键区别？

> **A:** (1) 虚拟机虚拟整个 OS——含内核——几 GB——启动 30s-2min。Docker 共享宿主机内核——只隔离应用——几百 MB——启动 1-3s。(2) 对数据分析师——Docker 解决的是"环境一致性"问题——不是"服务器运维"问题。

**Q3:** 环境变量在 Docker 中的正确使用方式？

> **A:** 所有"在不同场景下可能变化"的配置——通过 os.getenv() 读取——设合理默认值。运行容器时通过 docker run -e KEY=VALUE 覆盖。同一个镜像——通过环境变量切换行为——不需要建多个镜像。

**W27 工程化交付物清单:**
- [ ] Dockerfile——放在项目根目录——docker build . 能成功构建
- [ ] docker-compose.yml——含 app 服务 + db 服务（即使当前不需要——知道模式即可）
- [ ] >= 3 个配置项通过 os.getenv() 读取——有合理默认值
- [ ] CI 中含 docker build 步骤——每次 push 自动验证镜像能构建
- [ ] README 快速开始——含 Docker 启动方式（一行替代四行手动操作）
- [ ] docker run --rm <image> 能完整跑通全流程

- `docker build .` 能成功构建吗？
- `docker run --rm <image>` 能完整跑通吗？
- 环境变量配置了 ≥ 3 个可覆盖的参数吗？
- CI 中含 `docker build` 步骤且绿灯吗？
