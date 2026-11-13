# 本地脚本协议

Python 3.10+，仅标准库，无网络或模型调用。Antigravity负责语义生成/审核并自主循环执行脚本。
脚本不是后台服务：只有Antigravity遵照SKILL.md循环执行时，生成—反馈—修改才会自动推进。

## 输入

prompt.txt保存用户原文。plan.json由Antigravity按来源阅读结果编写。例如：

    {
      "scope": "只修正文稿；代码、数据库和权威方案只读",
      "authority_policy": "遵从用户明确确认的现行方案；两个来源的冲突单列，不由日期或文件名裁决",
      "max_rounds": 6,
      "sources": [
        {
          "id": "S1",
          "path": "E:/project/docs/plan.md",
          "role": "authority",
          "purpose": "核验业务范围和关联计算合同",
          "version": "实际读取文档头部及生效说明所得版本",
          "order": 1,
          "ranges": [[1, 30], [100, 160]]
        },
        {
          "id": "S2",
          "path": "E:/project/docs/acceptance.json",
          "role": "acceptance",
          "purpose": "核验相应分支的验收预期",
          "version": "由现行方案明确引用",
          "order": 2,
          "ranges": []
        }
      ],
      "criteria": [
        {
          "id": "R1",
          "requirement": "说明与两份来源逐项对应；保留未决分歧，正文及图表不擅自选边",
          "prompt_quote": "来源冲突单独列出，不自行裁定",
          "source_ids": ["S1", "S2"]
        }
      ],
      "conflicts": [
        {
          "id": "K1",
          "description": "两个来源对同一条件下的规则存在分歧",
          "source_ids": ["S1", "S2"],
          "policy": "preserve"
        }
      ],
      "prior_findings": [
        {
          "id": "P1",
          "criterion_id": "R1",
          "problem": "上轮正文声明不裁定，但流程实际选用了其中一种规则"
        }
      ],
      "literal_checks": []
    }

不要原样使用示例路径、版本或问题。prompt_quote必须是本次prompt.txt中的逐字子串。
所有criteria都必须对应用户要求；source_ids是该项通过时必须引用的来源集合。
sources角色：authority、acceptance、implementation、evidence、historical。
没有外部来源要求的任务允许sources=[]，但所有source_ids必须为空。
版本无法确认就明确写“未确认”及原因；若影响正确性，阻止定稿。
conflicts的preserve适用于只需忠实呈现争议的文稿；block适用于不决定便无法正确完成的产物。
没有冲突时conflicts=[]，没有旧问题时prior_findings=[]。

literal_checks可选，仅适合用户明确要求的固定字符串。格式：

    {"criterion_id":"R2","kind":"not_contains","text":"用户禁止出现的确切文字"}

contains/not_contains不证明语义正确。不要用关键词代替适用性、事实或冲突审查。

## 每轮审查JSON

packet生成准确的JSON结构、当前request_id与draft_sha256；按它填报。
关键字段：

- coverage：冻结criteria逐项且恰好一次，状态PASS/FAIL/BLOCKED，理由、当前稿逐字引文、来源定位。
- cross_checks：source_fidelity、internal_consistency、scope、new_issues四项完整检查。
- findings：所有需修改的问题，含稳定ID、criterion_id、problem、draft_quote、citations、fix、needs_user_decision。
- prior_findings：历轮台账全部问题，FIXED/OPEN/INVALID；已修复问题也应复查回归。
- conflicts：全部预先登记冲突，PRESERVED/DECIDED/OMITTED。
- summary：本轮实际结论。脚本自己计算是否通过，不接受作者或审查者自行设置最终通过状态。

引用对象：

    {"source_id":"S1","start_line":100,"end_line":103,"quote":"该行段中的逐字短引"}

正文引用格式：〔S1:L100-L103〕。
quote在真实来源行段中存在只是必要条件；Antigravity仍须判断它是否支持对应结论。
正文无明确位置的遗漏问题draft_quote可为空；通过项和已修复问题必须给出当前正文证据。
没有新问题时findings=[]，不能保留输出模板里的F001占位项。
发现新的冲突或缺证需加入finding；必须人工决定时标needs_user_decision=true。
不得通过把问题移入“备注”或删掉问题来获取通过。

## 状态与退出码

- GENERATE/REVISE → draft
- REVIEW/VERIFY → review
- 一次干净审查 → VERIFY；同稿第二次干净审查 → PASSED
- 可修正问题 → REVISE
- 决策/关键证据阻塞 → BLOCKED
- 已到最大草稿版数且仍有问题 → LIMIT_REACHED
- 修订提交与原稿字节相同 → STALLED

退出码0只代表命令成功，不代表终版通过；必须看status。
退出码1是格式/来源/证据校验失败，原状态不前进；修正提交资料后重试。
退出码2是BLOCKED/LIMIT_REACHED/STALLED，不生成final.md。
默认最多6版，包含已有初稿；每版可审查两次。改变标准/补来源需新建run，并继承旧问题台账。
所有模型回答均由Antigravity写入run目录。来源、项目代码和权威文件不会被脚本修改。

## 通过后的产物

final.md与最后审核稿字节一致。
approval.json记录来源/标准合同hash、正文hash、轮次和审核历史。
保留contract.json、source-bundle.md、reading-guide.md、各轮草稿/报告和feedback.md用于追溯。
不要手改state.json推进状态；这不是防恶意宿主的安全沙箱，而是防误操作和错误通过的工作流门禁。

## Antigravity安装依据

项目技能路径：<workspace>/.agents/skills/<name>/SKILL.md。
按官方文档，旧.agent/skills路径仍可能兼容；本技能采用.agents/skills。
参考：https://antigravity.google/docs/skills
未在Antigravity实际加载时，不声称已经验证其界面发现或实际模型审查质量。

