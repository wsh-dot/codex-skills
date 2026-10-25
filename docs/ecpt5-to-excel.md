# ECPT5 转 Excel

将 EC5 / 长庆设计造价编审软件的 `.ecpt5` 定概项目分别导出为 Excel，
默认保留原工程层级和源数据值。支持已验证的风电、光伏及 CBS 项目格式。

## 安装到 Codex

可将下面的指令发给支持 GitHub Skill 安装的 Agent：

```text
请安装这个 Skill 子目录：
https://github.com/wsh-dot/codex-skills/tree/main/skills/ecpt5-to-excel
保留 SKILL.md、agents、references、scripts、assets 的完整结构。
```

也可以克隆仓库后在 Windows PowerShell 中复制整个技能目录：

```powershell
git clone https://github.com/wsh-dot/codex-skills.git
Copy-Item -Recurse ".\codex-skills\skills\ecpt5-to-excel" "$env:USERPROFILE\.codex\skills\ecpt5-to-excel"
```

目标已存在时，先检查本地版本，避免直接覆盖本地修改。仓库根 README 和
`docs/` 是发布说明，不需要复制进安装后的技能目录。

## 使用

上传一个或多个 ecpt5 文件后：

```text
使用 $ecpt5-to-excel，将这些文件分别导出为 Excel，沿用20列树结构格式。
```

每个输入文件生成一个独立工作簿，包含：

1. 树结构：工程、分部、定额、主材与设备。
2. 定额人材机：以父层级编号关联预算节点。
3. 项目其他费用：保留源编制费用、送审费用及计算式。
4. 工程核对：对照目录造价与预算树根造价。
5. 来源与核对：读取范围、数量、标识差异及异常原因。

计算式作为文本，金额和工程量保留源文件存储值，不重新计算预算。

## 运行环境

- JDK 17+，包含 `java` 和 `javac`。
- Python；保存后核验需要 `openpyxl`，Codex 的工作区依赖运行时已提供。
- Node.js 与 Codex 工作区提供的 `@oai/artifact-tool`。
- db4o 6.4 读取 JAR 已放在 `assets/`，无需原软件目录、加密锁或 JNI。

`@oai/artifact-tool` 应通过 Codex 的工作区依赖工具获取。只有普通 Node.js
环境并不能保证可以生成 Excel；依赖不齐时应报告缺失项，不能将 JSON 当作
Excel 交付。其他兼容 SKILL.md 的 Agent 也需要满足这些运行时条件。

## 命令行与状态

技能会调用 `scripts/export_ecpt5.py`。运行时路径由当前环境解析，
不要复制其他机器的绝对路径：

```powershell
& "<python>" "<skill-dir>/scripts/export_ecpt5.py" `
  "<input-a.ecpt5>" "<input-b.ecpt5>" `
  --output-dir "<new-output-dir>" `
  --node-exe "<node>" --node-modules "<node_modules>"
```

退出码 `0` 表示全部完整、`2` 表示有部分导出、`1` 表示有失败。
每批 manifest 会逐文件记录状态、数量、输入哈希、核验结果和未读取工程。

损坏或不支持的工程库只保留该工程的项目目录汇总，并明确标注明细未读取。
未知的工程量、数量、预算树根及差额留空，不按零处理，也不从别的项目补数。

## 自检与评审

```powershell
python -B skills/ecpt5-to-excel/scripts/test_integrity.py
```

自检使用合成样例，不需要私人项目文件。完整回归和独立评分见
[评审与验证摘要](reviews/ecpt5-to-excel.md)。
