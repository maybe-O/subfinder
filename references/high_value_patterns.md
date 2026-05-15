# 高价值资产识别模式

> 命中以下任一模式的子域需要**重点标记**并在报告中优先展示。

## 高价值类型

### 1. 暴露的后台管理系统

```text
关键词: admin, panel, manage, cpanel, backend, console, dashboard, control
风险: 可能有未授权访问、弱口令、默认凭据
标记: ⚠️ 管理后台
```

### 2. 内网穿透/VPN 入口

```text
关键词: vpn, proxy, tunnel, gateway, nat, forward
风险: 可能是内网入口，一旦突破等于内网权限
标记: ⚠️ VPN入口
```

### 3. 代码仓库

```text
关键词: gitlab, github, bitbucket, git, svn, code, repo
风险: 源码泄露、硬编码密钥、CI配置暴露
标记: ⚠️ 代码仓库
```

### 4. CI/CD 系统

```text
关键词: jenkins, runner, builder, pipeline, deploy, ci, cd, bamboo, teamcity
风险: 构建链劫持、供应链攻击、凭据泄露
标记: ⚠️ CI/CD系统
```

### 5. 身份认证系统

```text
关键词: sso, auth, login, oauth, cas, iam, idp, ldap, ad, saml, accounts, passport
风险: 认证绕过、会话劫持、Token泄露
标记: ⚠️ 认证系统
```

### 6. 预发布环境

```text
关键词: staging, uat, pre-release, pre, demo, beta, rc
风险: 配置与生产环境相似但安全控制更弱
标记: ⚠️ 预发布环境
```

### 7. 数据库暴露

```text
关键词: db, mysql, redis, mongo, elastic, es, postgres, pg, mssql, oracle, sql
风险: 数据泄露、未授权访问、注入
标记: ⚠️ 数据库
```

### 8. 监控面板

```text
关键词: grafana, prometheus, zabbix, kibana, nagios, datadog, newrelic, splunk
风险: 内部指标暴露、系统信息泄露
标记: ⚠️ 监控面板
```

### 9. 开发环境

```text
关键词: dev, develop, debug, test, testing
风险: 调试接口暴露、Swagger文档、详细错误信息、硬编码凭据
标记: ⚠️ 开发环境 (常暴露调试端点)
经验参考: dev子域常暴露 /swagger-ui.html 或 /api-docs 等调试页面
```

### 10. Kali 深度扫描发现的高危项

```text
来源: Nikto / Gobuster Dir 发现
```

| 发现 | 风险等级 | 说明 |
| ---- | -------- | ---- |
| `.git` 目录暴露 | 🔴 严重 | 源码泄露风险，可能导致整个代码仓库被下载 |
| `/actuator` 端点暴露 | 🔴 严重 | Spring Boot 监控端点未授权，泄露运行时配置 |
| `/backup/` 目录可列 | 🟠 高 | 备份文件可被下载，含数据库凭据 |
| `/swagger-ui.html` | 🟠 高 | API 文档暴露，接口参数结构一览无余 |
| `/phpmyadmin` | 🟠 高 | 数据库管理入口，暴力破解目标 |
| `.env` 文件暴露 | 🔴 严重 | 环境变量含数据库密码、API 密钥 |
| `/wp-admin` | 🟡 中 | WordPress 管理后台入口 |
| 过时软件版本 | 🟡 中 | Nikto 报告 Apache 2.4.29 (EOL)、nginx 1.14 等 |
| `X-Frame-Options` 缺失 | 🟢 低 | 可被 Clickjacking 攻击 |
| `Server` header 泄露版本 | 🟢 低 | 信息泄露，攻击者可针对性利用 |

```text
来源: Gobuster DNS 发现
```

| 发现 | 风险等级 | 说明 |
| ---- | -------- | ---- |
| `vpn.example.com` | 🔴 严重 | VPN 入口，一旦突破等于内网权限 |
| `jira.example.com` | 🟠 高 | 企业内部工单系统，可能含敏感项目信息 |
| `jenkins.example.com` | 🟠 高 | CI/CD 入口，代码仓库访问权限 |
| `grafana.example.com` | 🟡 中 | 监控面板，内部指标数据暴露 |

```text
来源: Nmap 端口扫描
```

| 端口 | 风险等级 | 说明 |
| ---- | -------- | ---- |
| 6379 开放 | 🟠 高 | Redis 未授权访问风险 |
| 9200 开放 | 🟠 高 | Elasticsearch 未授权访问风险 |
| 27017 开放 | 🟠 高 | MongoDB 未授权访问风险 |
| 3306/5432 开放 | 🟡 中 | MySQL/PostgreSQL 数据库对外暴露 |
| 22 开放 | 🟡 中 | SSH 服务，弱口令风险 |
| 3389 开放 | 🟡 中 | RDP 服务，弱口令风险 |

## 排除规则

以下模式**不算高价值**，应归入常规类别：

```text
cdn, cloudfront, akamai, cloudflare, fastly → CDN (常规)
static, assets, media, images → 静态资源 (常规)
*.github.io → GitHub Pages (常规)
*.s3.amazonaws.com → S3托管 (常规)
```
