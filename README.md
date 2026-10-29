# 邮件保活系统

通过邮件心跳确认“人还活着”，并自动更新一个远程仓库中的状态区块。全程零成本，运行在 GitHub Actions 上。

## 工作原理

```
GitHub Actions（每周一次）
        |
        v
   src/main.py
        |
        |-- 1. IMAP 查控制邮箱收件箱，取上一轮之后到达的邮件
        |-- 2. SMTP 向白名单每个邮箱发一封询问邮件
        |-- 3. 匹配：发件人在白名单 + 非自己发出 + 未处理过
        |-- 4. 命中则写 Active，未命中则写 Inactive 并累计静默周数
        |-- 5. 替换目标文件标记区块内的 callout
        |-- 6. 裁剪并保存 state.json
```

- **一个 Gmail 控制邮箱**负责发信和查信，收发同一账号。
- **白名单邮箱**中任意一个回信即可，回信统一落到控制邮箱收件箱，内容不限。
- **目标文件**只改 `<!-- alive_start -->` 与 `<!-- alive_end -->` 之间的内容，标记之外不动。

本项目只针对 Gmail 个人账户设计（应用密码认证），其他邮箱服务商未做适配；如需 Outlook、自建邮箱等方案，请自行 fork 改造。

## 目标文件效果

命中时：

```markdown
<!-- alive_start -->

> [!NOTE]
> Active · within 1 week

<!-- alive_end -->
```

未命中时：

```markdown
<!-- alive_start -->

> [!WARNING]
> Inactive · 3 weeks ago

<!-- alive_end -->
```

时间描述按 52 周进年、4 周进月、余数为周，例如 `1 year 1 month 1 week ago`。

## 目录结构

```
keepAlive/
├── .github/workflows/alive.yml   # Actions 执行入口
├── src/
│   ├── main.py                   # 总指挥：查、发、匹配、改仓库、存盘
│   ├── config.py                 # 从环境变量读取配置
│   ├── state.py                  # state.json 读写与裁剪
│   ├── checker.py                # IMAP 查收件箱
│   ├── mailer.py                 # SMTP 发询问邮件
│   ├── actions.py                # 替换目标文件的标记区块
│   └── utils.py                  # 时间、编号、文本描述、脱敏
├── scripts/
│   ├── run_local.py              # 本地入口
│   ├── probe_imap.py             # IMAP 连通性探路
│   └── probe_smtp.py             # SMTP 连通性探路
├── tests/
│   ├── conftest.py
│   ├── test_describe_active.py
│   ├── test_flow_mock.py
│   ├── test_mask_email.py
│   └── test_state.py
├── .env.example
├── .gitignore
├── .python-version
├── pyproject.toml
├── uv.lock
├── state.json
└── README.md
```

## 配置

### 获取 Gmail 应用密码

Gmail 个人账户不能用登录密码做 SMTP/IMAP 认证，必须生成应用密码，且前提是账户已开启两步验证（2FA）。

1. 访问 <https://myaccount.google.com/security>，登录并确认已开启"两步验证"。
2. 访问 <https://myaccount.google.com/apppasswords>。
3. 输入名称（如 `keepAlive`）并创建，复制显示的 16 位密码，它就是填入 `CONTROL_PASS` 的值（只显示一次）。

同时确认 IMAP 已开启：Gmail 网页版 → 设置 → 查看所有设置 → 转发和 POP/IMAP → **启用 IMAP**（默认是关闭的，不启用则收信直接失败）。

### 本地 `.env`

从 `.env.example` 复制一份：

```bash
cp .env.example .env
```

填写以下字段：

| 变量                                      | 说明                                                       |
| ----------------------------------------- | ---------------------------------------------------------- |
| `CONTROL_EMAIL`                           | 控制邮箱地址，负责收信和发信                                 |
| `CONTROL_PASS`                            | 控制邮箱的应用密码（16 位），不是登录密码                 |
| `IMAP_HOST` / `IMAP_PORT`                 | 默认 `imap.gmail.com` / `993`                                |
| `SMTP_HOST` / `SMTP_PORT`                 | 默认 `smtp.gmail.com` / `465`（隐式 TLS）                    |
| `WHITELIST_EMAILS`                        | 逗号分隔，回信发件人在此列表内即命中                       |
| `REMOTE_REPO`                             | 目标仓库，格式 `owner/repo`                                |
| `REMOTE_FILE`                             | 目标文件，例如 `README.md`                                 |
| `REMOTE_BRANCH`                           | 目标分支，例如 `main`                                      |
| `REMOTE_TOKEN`                            | PAT，需目标仓库 Contents 读写权限                          |
| `REMOTE_BLOCK_START` / `REMOTE_BLOCK_END` | 标记行，默认 `<!-- alive_start -->` / `<!-- alive_end -->` |
| `MAX_SENT_IDS` / `MAX_PROCESSED_UIDS`     | 状态裁剪上限，默认 `30` / `100`                            |
| `DRY_RUN`                                 | `true` 时不写仓库，只打印                                  |
| `MAIL_DRY`                                | `true` 时不发邮件，只打印                                  |
| `LOG_LEVEL`                               | 默认 `INFO`                                                |

`.env` 已在 `.gitignore` 中，不会提交。

### GitHub Secrets 与 Variables

在仓库 `Settings -> Secrets and variables -> Actions` 中创建。

**Secrets（加密，适合凭据与个人信息）**

| 名称               | 说明                                     |
| ------------------ | ---------------------------------------- |
| `CONTROL_EMAIL`    | 控制邮箱地址                             |
| `CONTROL_PASS`     | 应用密码（16 位）                     |
| `REMOTE_TOKEN`     | 目标仓库 PAT                             |
| `WHITELIST_EMAILS` | 白名单含真实邮箱，属个人信息，放 Secrets |

**Variables（明文，适合非敏感配置）**

| 名称                 | 说明           |
| -------------------- | -------------- |
| `IMAP_HOST`          | IMAP 服务器    |
| `IMAP_PORT`          | IMAP 端口      |
| `SMTP_HOST`          | SMTP 服务器    |
| `SMTP_PORT`          | SMTP 端口      |
| `REMOTE_REPO`        | `owner/repo`   |
| `REMOTE_FILE`        | 目标文件       |
| `REMOTE_BRANCH`      | 目标分支       |
| `MAX_SENT_IDS`       | 可选，默认 30  |
| `MAX_PROCESSED_UIDS` | 可选，默认 100 |

`DRY_RUN` 与 `MAIL_DRY` 在 workflow 中已固定为 `"false"`，无需配置。

### 日志脱敏

日志中的邮箱地址经 `mask_email` 处理，只显示首字符和域名，例如 `k***@gmail.com`。Message-ID 不写入日志，排查去重问题时查看 `state.json` 中的 `sent_message_ids` 与 `processed_uids`。

## 本地运行

安装依赖：

```bash
uv sync
```

运行测试：

```bash
uv run pytest tests/ -v
```

探路脚本（先确认邮箱能连上）：

```bash
uv run python scripts/probe_imap.py
uv run python scripts/probe_smtp.py
```

运行主流程：

```bash
uv run python scripts/run_local.py
```

建议按三档推进：

| 档位     | `DRY_RUN` | `MAIL_DRY` | 验证内容                     |
| -------- | --------- | ---------- | ---------------------------- |
| 纯逻辑   | `true`    | `true`     | 查、匹配、生成文本，无副作用 |
| 邮件链路 | `true`    | `false`    | 真发真收、白名单命中、去重   |
| 端到端   | `false`   | `false`    | 真实写入目标仓库标记区块     |

## 部署到 GitHub Actions

1. 提交代码，包含 `state.json` 的当前内容。
2. 在仓库中配置好 Secrets 和 Variables。
3. 确认 `Settings -> Actions -> General -> Workflow permissions` 允许读写，或依赖 workflow 中的 `permissions: contents: write`。
4. 手动触发一次 `workflow_dispatch`，检查日志与本地一致。
5. 之后由 cron 每周一 08:00 UTC 自动运行。

cron 在 GitHub 上可能延迟数分钟到数十分钟，对每周频率没有影响。

## 状态文件

`state.json` 只存记忆，不存配置：

| 字段               | 含义                                                |
| ------------------ | --------------------------------------------------- |
| `last_alive_at`    | 上次确认存活的 UTC 时间                             |
| `last_ping_at`     | 上次发出询问的时间                                  |
| `silent_weeks`     | 当前静默整周数                                      |
| `sent_message_ids` | 最近发出的询问邮件 Message-ID，用于排除自己发的邮件 |
| `processed_uids`   | 最近处理过的回信 UID，用于去重                      |
| `enabled`          | 手动开关，设为 `false` 可暂停                       |

`sent_message_ids` 与 `processed_uids` 只保留最近若干条，避免无限增长。裁剪不影响 `last_alive_at`，因此静默周数不会因裁剪出错。候选窗口只有最近一轮，保留条数远大于窗口，旧记录被裁掉也不会再进入匹配。

上限由 `MAX_SENT_IDS` 与 `MAX_PROCESSED_UIDS` 控制，可在 `.env` 或 Variables 中覆盖，默认 30 / 100。

## 防误判设计

匹配回信时同时要求：

1. 发件人在白名单内；
2. `Message-ID` 不在 `sent_message_ids` 中，排除自己发出的询问邮件；
3. 邮件 UID 不在 `processed_uids` 中，同一封回信只算一次。

此外，流程是先查收件箱、再发新询问，本轮发出的邮件不会混入本轮匹配。

## 常见问题

**IMAP/SMTP 登录失败（535）**

Gmail 不能用登录密码做 SMTP/IMAP 认证，必须用应用密码（见上文「获取 Gmail 应用密码」）。若报 `Basic authentication is disabled`，先检查 Gmail 设置里 IMAP 是否已启用。

**目标仓库写入失败**

403 通常是 token 权限不足，404 通常是 `REMOTE_REPO` 或 `REMOTE_FILE` 路径错误。fine-grained token 需要单独勾选目标仓库的 Contents 读写权限。

**标记缺失**

目标文件中必须恰好各出现一次 `<!-- alive_start -->` 和 `<!-- alive_end -->`，顺序正确。缺失、重复或顺序反了会直接报错，不写文件。

**日志里看不到完整邮箱**

这是设计行为。日志经 `mask_email` 脱敏，只保留首字符和域名，避免白名单和个人邮箱出现在公开的 Actions 日志中。需要完整信息时查看 `state.json` 或邮箱本身。
