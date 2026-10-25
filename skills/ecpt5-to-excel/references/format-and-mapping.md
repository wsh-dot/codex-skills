# 格式与数据映射

仅在解释字段、定制模板或适配变体时读取。

## 已验证的存储链

`ZIP arr → DES/ECB/PKCS5Padding → GBK XML → EditorCellEntity.costFileId → 同名.ecd → db4o通用对象 → CostFile.zmItemList.items`。
有些包的 arr 为明文 XML；读取器只在 XML 头明确存在时跳过解密。不要使用 Java 原生反序列化加载应用对象。

工程库 `db4o` 签名前有不定长前缀，不假定固定21字节。当前脚本支持 db4o 文件头版本1：块大小位于逻辑偏移36；37处为变量头块地址；变量头首8字节给类目录地址与长度。目录的类数量必须为正且与槽长度、文件边界相符，再调用库打开。

## 20列树结构

| 列 | 来源或规则 |
|---|---|
| 序号 | 当前工作簿树结构数据行序号，从1开始 |
| 层级编号 | 项目：orderCode；工程内部：以工程orderCode替换本地BSID根1 |
| 父层级编号 | 已存在层级编号的父段；ZCSpend指向所属预算节点 |
| 层级 | 当前完整层级段数；附件为所属节点层级+1 |
| 标识 | 源mark；ZMGljEntity按EditorRCJ.gljType识别 |
| 编号、名称、单位 | 源no/name/unit；独立材料设备从edrcj的sysCode/name/unit读取 |
| 工程量计算式 | gclFormula文本；不是gclExp，也不写成Excel公式 |
| 工程量、单价 | gcl、unitPrice；ZCSpend为actSpend、scPrice |
| 人工/材料/机械单价 | rgFee、clFee、jxFee |
| 主材费、设备费 | zcFee、sbFee；ZCSpend按类型将totalPrice放入对应列 |
| 基价合计、造价合计 | totalPrices、zzj；附件造价为其存储的totalPrice |
| 数据库对象ID | ZIP数据库条目标识:库内对象数字ID；项目及费用保留UUID |
| 来源类型 | 原对象类名；未读取的工程汇总标为EditorCellEntity（明细未读取） |

GLJ类型：10人工、20材料、30机械、40主材、50设备、60仪表。未识别类型保留源标识，不猜成主材。

项目目录行使用 `bzzcfee/bzsbfee/bzcost`；预算文件保存造价为 `CostFile.cost`；预算树根为 `zzj`。这三个位置独立读取，不能用其中一个覆盖另一个。

层级按数字分段排序：1.2在1.10之前。每个工程的ZCSpend紧跟所属节点，且保留其列表顺序。人材机取节点rcjSpend；耗量spend、定额耗量deSpend，按父层级、费用编码及对象ID确定性排序。

目录工程数量和唯一预算库数量分别统计：多个工程可以引用同一个costFileId。成功库数按成功读取的唯一库标识计数；未读取原因逐目录工程保留，不能把失败工程条数从唯一库数中直接扣减。

项目其他费用取项目secFeeItemList→items→SecFeeEntity；按所属项目和原费用bSID排序。fee为编制费用，ssFee为送审费用；两者不能互换。无费用记录不表示读取失败；没有其他费用的项目仍保留该sheet表头。

## 适配边界

遇到未知根对象、缺失BSID、重复层级或缺失父级，不补造源记录。将具体工程标为未读取，保留其目录汇总；项目目录本身无有效根或缺少费用关联时，当前文件失败，其他文件继续。未知版本需先检查源代码和格式证据再扩展读取器，不扩大允许类加载范围。
