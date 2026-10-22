# 财报卡片规范

## 默认模板

- 用户只说“财报”且未指定其他视觉模板时，默认使用公开仓库 `iroryagame-afk/earnings-templates`。
- 模板基准固定为 commit `d832b6678f1c8c21b3c15bae0fe62f0032b15c35`：单公司使用 `single-company/template.html`，多公司合并使用 `combined/template.html`。
- 必须遵守该仓库 README 的字段顺序、公开 Whisper、实际值、锁定 Beat 线、✓△✕□ 验收和多公司排序规则；不得复制模板示例公司的数据。

## 通用要求

- 默认尺寸为 9:16；所有文字必须在手机端可读，模板与品牌资产存入 `assets/templates/` 并版本化。
- 标明公司、代码、财报期间、发布日期、发布时间及明确时区。
- reported、non-GAAP、调整后口径和自行计算值必须分开。
- 每项实际值与一致预期必须使用相同币种、期间、单位和会计口径。
- 图片不得比对应数据记录更早更新；无法核验的字段宁可留空或标“待证真”。

## 财报预告图

必须包含：

- 发布时间和时区；
- 收入、EPS/经营利润、毛利率或经营利润率、现金流等关键一致预期；
- 公司正式指引及中点；
- 市场最关心的 3–5 个验证问题；
- 强化、证伪、等待回踩和不追涨条件；
- 一致预期来源及截至时间。

预告图只能描述“市场预期”，不得提前把推测写成实际结果。

## 财报后验证图

必须逐项比较：

| 字段 | 要求 |
| --- | --- |
| `metric` | 指标名称及口径 |
| `reported_period` | 财报期间 |
| `consensus_value` | 一致预期 |
| `consensus_source` | 预期来源 |
| `consensus_as_of` | 预期截至时间 |
| `actual_value` | 实际值 |
| `actual_source` | 公司 IR、监管文件或公告原文 |
| `beat_or_miss` | 超预期、符合、低于或不可比 |
| `comparison_basis` | 币种、单位、GAAP/non-GAAP、是否自行计算 |

图中至少覆盖收入、利润/每股收益、利润率、现金流和下一期/全年指引；给出论文强化、弱化、证伪和待确认事项。

## 文件组织

建议按 Issue 保存源文件与导出文件：

```text
assets/charts/issue-128/
  sources.md
  earnings-preview-v1.png
  earnings-review-v1.png
```

源文件、最终图片与引用记录应在同一 PR 中可追溯。
