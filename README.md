# Codex Skills

这个仓库发布我日常使用的 Codex Skills，用来给 Codex 和其它兼容
`SKILL.md` 的 AI 编程 Agent 增加可复用工作流。

## Skills

### clarify-search

`clarify-search` 会在搜索前判断需求是否存在会改变检索结果的歧义：
明确的问题直接搜索；模糊、比较型或高风险问题则一次确认一个关键决策，
再整理为 Search Brief 并执行有证据支撑的搜索。

它目前支持：

- 豆包搜索 Custom API 的网页和图片搜索
- 按时间、域名、权威等级和内容格式限制结果
- 对探索、比较、技术选型、“最新”和“最热门”等请求采用不同证据策略
- 区分搜索结果、事实证据与最终建议
- 首次安全配置豆包搜索 API Key，之后在本机永久复用
- API Key 失效时重新配置；超时、限流和额度耗尽不会被误判为密钥失效
- 确定性测试、限流退避和凭据泄露防护

### building-c-concept-html-guides

`building-c-concept-html-guides` 用来创建精美的 C 语言概念 HTML 教程，
包含可视化图解、可运行示例、常见错误、响应式 QA 和可选的
Cloudflare Pages 部署检查。

## 最推荐的安装方式

如果你的 AI 编程软件支持从 GitHub 安装 Skill，请优先使用对应的
**Skill 子目录链接**。

安装 `clarify-search`：

```text
https://github.com/wsh-dot/codex-skills/tree/main/skills/clarify-search
```

也可以把下面这段话直接发给 AI IDE：

```text
请从这个 GitHub 子目录安装 Skill：
https://github.com/wsh-dot/codex-skills/tree/main/skills/clarify-search

只安装 skills/clarify-search/ 目录。安装后的 Skill 根目录必须直接包含
SKILL.md、agents/、references/ 和 scripts/。
不要把仓库根目录 README.md 复制进 Skill 安装目录。
```

不要只把仓库根地址作为自动安装地址。真正可安装的 Skill 位于
`skills/<skill-name>/`；根目录 README 只是 GitHub 说明文档。

## Skill 目录结构

```text
skills/
  clarify-search/
    SKILL.md
    agents/
    references/
    scripts/
  building-c-concept-html-guides/
    SKILL.md
    agents/
```

## 手动安装

先克隆仓库：

```bash
git clone https://github.com/wsh-dot/codex-skills.git
cd codex-skills
```

安装 `clarify-search` 到 Codex，Windows PowerShell：

```powershell
New-Item -ItemType Directory -Force `
  "$env:USERPROFILE\.codex\skills" | Out-Null

Copy-Item -Recurse -Force `
  ".\skills\clarify-search" `
  "$env:USERPROFILE\.codex\skills\clarify-search"
```

首次使用豆包搜索前，在安装后的 Skill 目录运行：

```powershell
python scripts/doubao_search.py --configure-key
```

命令会隐藏 API Key 输入，并将凭据保存到当前用户的本地配置目录。
API Key 不会写入 Skill 文件或 Git 仓库。

## 使用示例

```text
使用 $clarify-search，帮我调研 2026 年生产级 Agent 项目的技术栈。
```

```text
使用 $clarify-search，只用豆包搜索查找 OpenAI 官方 Logo 图片。
```

```text
使用 $building-c-concept-html-guides 创建一篇讲解 C 指针的 HTML 教程。
```
