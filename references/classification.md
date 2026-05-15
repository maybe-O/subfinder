# 子域分类体系

> LLM 根据子域 `host` 字段中的关键词 + Nmap 端口/服务指纹，将子域归入以下类别。

## 分类表

| 类别 | 关键词 | 端口/服务特征 | 优先级 |
| ---- | ------ | ------------ | ------ |
| 管理/后台 | admin, manage, panel, dashboard, console, backend, control, cpanel, webmaster | :8080, :8443, :9090 (非标端口) | 高 |
| API/接口 | api, api-gateway, rest, graphql, grpc, webhook, apiv1, apiv2, apiv3 | :3000, :4000, :5000, :8000 | 高 |
| 开发/测试 | dev, develop, staging, stage, test, testing, uat, pre, beta, alpha, debug | :8080, :8443, :3000, :5000 (非标端口) | 高 |
| CI/CD | jenkins, gitlab, github, bitbucket, ci, cd, deploy, builder, runner, pipeline | :8080 (Jenkins), :9090 | 高 |
| 认证/SSO | sso, auth, login, oauth, cas, iam, idp, ldap, ad, saml | :443 (强制 HTTPS) | 高 |
| 基础设施 | vpn, proxy, nginx, docker, k8s, kube, registry, harbor, db, redis, mysql, mongo, elastic, es, rabbitmq, kafka, zookeeper | :6379 (redis), :9200 (es), :27017 (mongo), :9092 (kafka) | 高 |
| 监控 | monitor, grafana, prometheus, zabbix, nagios, alert, kibana, datadog, newrelic | :3000 (grafana), :9090 (prometheus), :5601 (kibana) | 高 |
| 企业应用 | oa, erp, crm, hr, wiki, jira, confluence, notion, slack, teams | :443 (HTTPS) | 中 |
| 邮件 | mail, smtp, webmail, email, pop, imap, mx, exchange | :25, :587, :993, :443 | 中 |
| 文档/存储 | docs, static, cdn, assets, media, files, s3, oss, cos, gcs, blob | :80, :443 | 低 |
| 常规服务 | www, ftp, ssh, telnet, ns, dns, whois, blog, shop, store, app, m, mobile, wap | :80, :443, :21, :22 | 低 |

## 分类规则

1. **优先级高者优先**: 如果一个子域同时命中多个类别，取优先级最高的
2. **最长匹配**: `api-gateway` 优先匹配 "API" 而不是简单匹配 "api"
3. **端口辅助判定**: Nmap 扫描发现的端口号可辅助判定类别 (如 :6379 → 基础设施/Redis)
4. **服务指纹辅助**: Nginx/1.18 vs Apache/2.4.29 可辅助判断资产年龄和维护状态
5. **未匹配归入 "其他"**: 无法归类的子域放入 "其他" 类别
6. **CDN 排除**: 包含 `cdn`, `cloudfront`, `akamai`, `cloudflare`, `fastly` 的子域归入 "文档/存储"，不标记高价值
