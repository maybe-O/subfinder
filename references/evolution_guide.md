# 自我进化机制详解

> Agent 通过 `agent_memory.py` 管理四个维度的长期记忆，实现从"工具"到"智能体"的蜕变。

---

## 维度 1: 动态经验库 (Payload 与字典的自生长)

### 原理

传统工具使用静态字典。进化的 Agent 自己"造轮子"——从每次收集中沉淀高价值模式。

### 进化场景

```text
场景: 在某次收集中，Agent 发现 dev.example.com 暴露了 /swagger-ui.html 调试端点。

Agent 行为:
1. 识别: "dev 子域 + swagger 调试端点" 是一个高价值模式
2. 记录:
   python agent_memory.py add-experience \
     --category pattern \
     --content "dev子域常暴露swagger调试页面，路径多为/swagger-ui.html或/api-docs" \
     --tags "dev,swagger,api-docs,high-value" \
     --confidence 0.8

3. 下次遇到同类目标:
   python agent_memory.py query-experiences --tags dev,high-value
   → 自动获得此经验，在报告中对 dev 子域额外标注 swagger 风险
```

### 命令

```bash
# 添加经验
python agent_memory.py add-experience --category {pattern|payload|route|insight} \
  --content "经验描述" --tags "t1,t2" --confidence 0.7

# 查询经验
python agent_memory.py query-experiences --category pattern --tags high-value --limit 20

# 反馈调整 (验证有效 → 提升，验证失败 → 降低)
python agent_memory.py bump-experience --id 3 --delta 0.05
python agent_memory.py bump-experience --id 3 --delta -0.1
```

### 经验类别

| Category | 含义 | 示例 |
| -------- | ---- | ---- |
| pattern  | 命名规律 | "env- 前缀常对应预发布环境" |
| payload  | 探测 Payload | "dev子域常暴露 /swagger-ui.html" |
| route    | 路由特征 | "/cgi-bin/ 变体常引发 RCE" |
| insight  | 综合洞察 | "该行业的子域多集中在某C段" |

---

## 维度 2: 数据源信誉度评分 (API 权重自适应)

### 原理

FOFA API + Kali-MCP 工具链，质量参差不齐。Agent 每次复盘打分，逐步学习哪些源更靠谱。

### 进化场景

```text
场景: 扫描后复盘，发现 FOFA-Domain 贡献了 45 个子域，存活率 85%；FOFA-Cert 贡献了 120 个。
      Kali-MCP gobuster DNS 发现了 3 个 FOFA 遗漏的子域（含高价值 vpn 入口）。

Agent 行为:
1. 评分:
   python agent_memory.py update-source --source fofa-domain --score 9 --context "科技公司" --notes "存活率高"
   python agent_memory.py update-source --source fofa-cert --score 7 --context "科技公司" --notes "发现额外证书关联"
   python agent_memory.py update-source --source kali-gobuster-dns --score 6 --context "科技公司" --notes "发现3个遗漏子域"

2. 下次扫描前:
   python agent_memory.py recommend-sources
   → fofa-domain (9.0) 排在前面，fofa-cert (7.0) 排在后面

3. 调整策略:
   # FOFA 多维度查询: domain + cert 组合覆盖
   # 同时调度 gobuster DNS 作为补充发现
```

### 评分标准

```text
 1-3: 垃圾数据多，泛解析严重
 4-6: 一般，有少量有效结果
 7-8: 质量好，存活率高
 9-10: 极高质量，几乎都是有效资产
```

### Kali-MCP 工具源评分

| 源 | 评分维度 |
| ---- | ----- |
| kali-gobuster-dns | 新子域发现数、新增高价值数、与 FOFA 互补度 |
| kali-nmap | 存活验证准确率、服务指纹完整度 |
| kali-nikto | 高危发现数、误报率 |
| kali-wpscan | 漏洞发现数、版本识别准确度 |
| kali-gobuster-dir | 隐藏路径发现数、敏感文件检出 |

---

## 维度 3: 决策树自优化 (工作流 ROI)

### 原理

Agent 的工作流是多步拼接的（收集 → 验证 → 分析 → 下一步）。让 Agent 评估每条决策路径的 ROI。

### ROI 定义

```text
ROI = (高价值发现数 / 总耗时) × 知识增益系数

高 ROI: 找到很多高价值资产，用时短
低 ROI:  跑了很久，大部分是垃圾
```

### 进化场景

```text
场景: 某套工作流 (fofa-domain → fofa-cert → kali-nmap → kali-nikto) 过去3次跟踪发现覆盖率极高。

Agent 行为:
1. 记录:
   python agent_memory.py record-workflow \
     --steps "fofa-domain->fofa-cert->kali-nmap->kali-nikto" --outcome "发现.git暴露+actuator未授权" --roi 0.9

2. 查询:
   python agent_memory.py recommend-workflow
   → 发现 "fofa-domain->fofa-cert->kali-nmap->kali-nikto" 平均 ROI 0.85，比纯被动收集更高

3. 调整: 高关注度任务默认开启 Kali 深度扫描，低关注度任务保持纯被动
```

---

## 维度 4: 解析规则与 Prompt 自迭代 (自我纠错)

### 原理

当 Agent 犯错时（分析错误、分类错误、用户纠正），记录纠正规则，下次主动应用。

### 进化场景

```text
场景: Agent 将 cdn.example.com 误标为高价值资产，用户纠正 "CDN不算高价值"。

Agent 行为:
1. 记录:
   python agent_memory.py record-error \
     --error "将cdn子域误分类为高价值资产" \
     --correction "cdn类子域应归入常规服务，不标记高价值" \
     --rule "分类时先检查cdn特征，cdn优先级高于其他分类"

2. 下次任务前:
   python agent_memory.py get-rules
   → 获得此规则，分析时先排除 CDN
```

---

## 记忆生命周期

```text
写入: 任务完成后 (Step 8)
读取: 任务开始前 (Step 1/2)

经验置信度:
  0.7 - 1.0 → 高优先级，始终应用
  0.4 - 0.7 → 中等，参考但不强制
  0.0 - 0.4 → 低置信度，逐渐遗忘 (不再推荐)

记忆不会删除，但低置信度的经验不会被主动推荐。
通过 bump-experience 的正负反馈自然调节。

推荐演化路径:
  fofa-domain → fofa-domain+fofa-cert → fofa-domain+fofa-cert+kali-nmap → fofa-domain+fofa-cert+kali-nmap+kali-nikto → 全链路
  从纯被动开始，逐步引入 FOFA 多维度查询和 Kali 主动验证，按 ROI 数据驱动决策。
```
