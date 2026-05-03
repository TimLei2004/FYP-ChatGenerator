# Dorm Bot Generator

用于生成测试用户画像、自动登录宿舍咨询网站、批量发问并将问答回写 Supabase 的 Python 工具集。

## 1. 项目功能

- 通过 DashScope (百炼) 生成测试用户人设与结构化画像。
- 自动创建测试账号并写入 `bot_profile`。
- 使用 Selenium 自动登录前端页面并自动填写首登问卷。
- 自动生成多轮问题并发送到聊天页面。
- 从数据库轮询回答并写入 `bot_histories`。
- 支持单账号与并发多账号测试。

## 2. 项目结构

- `GenerateMessage.py`: Prompt、画像生成、问题生成、Supabase 查询工具。
- `Helper.py`: 模型输出 JSON 清洗与解析。
- `SeleniumFrame.py`: Selenium 启动与通用填表动作封装。
- `Test.py`: 端到端自动化测试主流程（登录、填表、问答、回写）。
- `UpdateBotHistories.py`: 将 chat log 同步为结构化 QA 记录。
- `requirements.txt`: Python 依赖。
- `bot_histories.csv`: 示例/导出数据样本。
- `Testing.ipynb`: Notebook 调试文件。

## 3. 运行环境

- macOS / Linux / Windows（需安装 Chrome）
- Python 3.10+

建议使用虚拟环境。

## 4. 安装依赖

```bash
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

## 5. 环境变量

在项目根目录创建 `.env`（或在系统环境中导出）：

```env
SUPABASE_URL=your_supabase_url
SUPABASE_KEY=your_supabase_service_or_api_key
BAILIAN_API_KEY=your_dashscope_api_key

# 可选：DashScope/百炼的 app_id（建议通过环境变量管理）
BAILIAN_APP_ID=your_dashscope_app_id

# 可选：测试账号默认密码（用于自动创建测试用户），建议在线上环境不要使用默认弱密码
TEST_ACCOUNT_PASSWORD=your_test_account_password
```

代码会读取以上变量用于：

- Supabase 数据读写
- DashScope 文本生成

## 6. Supabase 表依赖

当前代码默认使用以下表：

- `bot_profile`
- `profiles`
- `chat_logs`
- `bot_histories`

并依赖 Supabase Auth Admin API 创建测试用户。

## 7. 快速开始

### 7.1 单账号自动测试

```python
from Test import start_a_test

start_a_test("test001@example.com", auto=True)
```

说明：

- 若账号不存在，会先自动创建。
- 首次登录若 `form_preferences` 为空，会自动填表并提交。
- 默认目标对话轮次约 10 轮（根据历史长度判断）。

### 7.2 多账号并发测试

```python
from Test import start_tests_parallel

emails = [
    "test001@example.com",
    "test002@example.com",
    "test003@example.com",
]

start_tests_parallel(emails, auto=True, max_workers=2)
```

### 7.3 手动模式

```python
from Test import start_a_test

start_a_test("manual001@example.com", auto=False)
```

`auto=False` 时会在每轮提问前允许输入备注，且账号创建阶段支持人工审查画像。

## 8. 常用工具函数

### 8.1 生成账号

```python
from GenerateMessage import generate_test_account

generate_test_account("newtest@example.com", auto=True)
```

### 8.2 查询某用户聊天与画像

```python
from GenerateMessage import search_by_uid, get_email_to_uid

uid = get_email_to_uid()["test001@example.com"]
chat_logs, profiles = search_by_uid(uid)
```

### 8.3 回写 bot_histories

```python
from UpdateBotHistories import update_one_bot_histories

update_one_bot_histories("test001@example.com")
```

## 9. 常见问题

### 9.1 Selenium 启动慢或卡住

项目默认通过 `webdriver_manager` 启动 ChromeDriver，已尽量规避 Selenium Manager 卡住问题。

### 9.2 登录后出现密码提示干扰自动化

`Test.py` 已关闭 Chrome 密码管理与弱密码检测相关选项，减少弹窗干扰。

### 9.3 字段匹配失败

`SeleniumFrame.py` 内有字段别名映射，若前端字段命名变化，请在 `_build_field_aliases` 中补充映射。

## 10. 注意事项

- `GenerateMessage.py` 中的 `app_id` 与测试账号密码已改为从环境变量读取（`BAILIAN_APP_ID` / `TEST_ACCOUNT_PASSWORD`），请在运行前在环境或 `.env` 中设置。
- `get_email_to_profile()` 目前使用 `eval` 反序列化字符串，建议后续改为安全的 JSON 解析。
- 当前流程大量依赖外部服务（Supabase、DashScope、目标网站），请先确认网络与密钥有效。

## 11. 依赖版本

以 `requirements.txt` 为准：

- supabase==2.3.4
- dashscope>=1.20.0
- python-dotenv==1.0.0
- selenium>=4.20.0
- webdriver-manager>=4.0.2
