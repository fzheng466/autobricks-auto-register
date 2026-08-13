# autobricksai.com 全自动注册

[autobricksai.com](https://creators.autobricksai.com) 全自动注册脚本，完整 6 步流程直达 API Key。

## 前置条件

- Python 3.8+
- M2API Turnstile 过盾引擎（免费，本地自托管）

## 快速开始

```bash
git clone https://github.com/fzheng466/autobricks-auto-register.git
cd autobricks-auto-register

# 终端1: 一键启动免费过盾引擎
bash setup_solver.sh

# 终端2: 安装依赖 + 注册
pip install -r requirements.txt
python3 register_m2api.py
```

## 引擎选择

| 引擎 | 文件 | 费用 | 说明 |
|------|------|:---:|------|
| M2API | `register_m2api.py` | **免费** | 本地 Camoufox 自托管，~8s/次 |
| YesCaptcha | `register_yescaptcha.py` | 25点/次 | 第三方付费 API，需填入 key |

## 注册流程

```
创建临时邮箱 → 过盾 → 注册 → 收确认邮件 → 确认邮箱 → 过盾 → 登录 → 创建API Key
```

每账号消耗 2 次 Turnstile 过盾（注册 + 登录）。

## 批量注册

```bash
python3 register_m2api.py -n 5   # 注册5个账号
```

账号间自动延迟 5 秒避免限速。

## API Key 使用

获取到的 Key 是 OpenAI 兼容格式：

```bash
curl https://api.autobricksai.com/v1/chat/completions \
  -H "Authorization: Bearer abai_sk_live_YOUR_KEY" \
  -H "Content-Type: application/json" \
  -d '{"model":"autobricksai/claude-sonnet-4.6","messages":[{"role":"user","content":"Hello"}]}'
```

覆盖 **33+ 模型**（Claude Opus/Sonnet/Haiku, GPT-5.4/4.1/4o-mini, Gemini 3.1/2.5, DeepSeek V4/R1, Grok 4, Qwen, Kimi, Llama 等）。
