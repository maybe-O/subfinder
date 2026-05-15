# 数据源参考

> FOFA API (Python 直接调用) + Kali-MCP 主动工具链
> subfinder 已从工作流中移除 — 其 FOFA 请求 URL 写死为 fofa.info，无法通过代理访问

## 外部资产引擎

### FOFA (Python 直接调用)

| 属性 | 说明 |
| ---- | ---- |
| 类型 | 主动 API（需配置凭证） |
| 返回 | hosts, IPs, ports, titles, domains, servers, countries |
| 优势 | FOFA 全网扫描索引，能发现证书透明度日志以外的资产 |
| 限制 | API 配额取决于 FOFA 会员等级；subfinder 不可用 (URL 写死) |
| 配置 | 编辑 `api_config.json` 填入 apikey 和 base-url |
| 用法 | Python `urllib.request` 直接调用 `{base-url}/api/v1/search/all` |

---

## Kali-MCP 主动工具链 (Active Validation & Deep Scanning)

Kali Linux 服务器上的主动探测和深度扫描工具，通过 MCP 协议远程调用。

### Nmap (kali-mcp_nmap_scan)

| 属性 | 说明 |
| ---- | ---- |
| 类型 | 主动端口扫描 + 服务指纹 |
| 返回 | 开放端口、服务版本、OS 指纹 (可选) |
| 用途 | Step 5B: 存活验证、服务识别、高价值主机指纹 |
| 优势 | 最精确的存活验证方式，服务指纹可辅助分类 |
| 限制 | 主动扫描，可能触发 IDS/IPS；需确认目标授权 |
| 用法 | `kali-mcp_nmap_scan(target="host", scan_type="-sV -T4", ports="80,443,8080,8443")` |

### Gobuster DNS (kali-mcp_gobuster_scan mode=dns)

| 属性 | 说明 |
| ---- | ---- |
| 类型 | 主动 DNS 暴力破解 |
| 返回 | 通过字典爆破发现的子域名 |
| 用途 | Step 5B: 补充 FOFA 被动收集，发现 DNS 隐藏的子域 |
| 优势 | 发现不在证书透明度日志中的子域；支持自定义字典 |
| 限制 | 依赖字典质量；大字典耗时较长 |
| 用法 | `kali-mcp_gobuster_scan(url="example.com", mode="dns", wordlist="/usr/share/wordlists/seclists/Discovery/DNS/subdomains-top1million-5000.txt")` |

### Nikto (kali-mcp_nikto_scan)

| 属性 | 说明 |
| ---- | ---- |
| 类型 | Web 服务器漏洞扫描 |
| 返回 | 已知漏洞、配置问题、信息泄露 |
| 用途 | Step 6B: 对高价值 Web 服务器自动漏洞检测 |
| 优势 | 覆盖 6700+ 已知问题，自动识别过时软件版本 |
| 限制 | 主动扫描，每个目标平均 30-120 秒 |
| 用法 | `kali-mcp_nikto_scan(target="https://admin.example.com")` |

### Gobuster Dir (kali-mcp_gobuster_scan mode=dir)

| 属性 | 说明 |
| ---- | ---- |
| 类型 | Web 目录/文件爆破 |
| 返回 | 隐藏目录、文件路径 |
| 用途 | Step 6B: 发现管理后台、API 文档、配置文件等隐藏路径 |
| 优势 | 发现 `.git`、`/swagger`、`/actuator` 等敏感路径 |
| 限制 | 依赖字典质量；高频请求可能触发 WAF |
| 用法 | `kali-mcp_gobuster_scan(url="https://admin.example.com", mode="dir")` |

### WPScan (kali-mcp_wpscan_analyze)

| 属性 | 说明 |
| ---- | ---- |
| 类型 | WordPress 漏洞扫描 |
| 返回 | WordPress 版本、插件/主题漏洞、用户枚举 |
| 用途 | Step 6B: 检测 WordPress 站点漏洞 |
| 触发条件 | Nikto 或端口扫描检测到 WordPress 特征 |
| 用法 | `kali-mcp_wpscan_analyze(url="https://blog.example.com")` |

### Enum4linux (kali-mcp_enum4linux_scan)

| 属性 | 说明 |
| ---- | ---- |
| 类型 | Windows/Samba 服务枚举 |
| 返回 | 用户列表、共享列表、OS 信息 |
| 用途 | Step 6B: Nmap 发现 SMB/NetBIOS 端口时的深入枚举 |
| 触发条件 | Nmap 发现 445/tcp (SMB) 或 139/tcp (NetBIOS) 开放 |
| 用法 | `kali-mcp_enum4linux_scan(target="10.0.0.5")` |

### 进阶攻击工具 (需授权)

| 工具 | 用途 | 触发条件 |
| ---- | ---- | -------- |
| sqlmap | SQL 注入检测 | 发现管理后台/登录页面 |
| hydra | 口令爆破 | 发现登录表单，需确认授权 |
| metasploit | 漏洞利用 | 已知漏洞确认，需确认授权 |

### Execute Command (kali-mcp_execute_command)

| 属性 | 说明 |
| ---- | ---- |
| 类型 | 任意 Kali 命令执行 |
| 用途 | Amass 被动枚举、Sublist3r 子域发现、DNSRecon 区域传输 |
| 优势 | 灵活调用 Kali 原生工具链 |
| 用法 | `kali-mcp_execute_command(command="amass enum -passive -d example.com 2>&1 | tail -30")` |

---

## 配置文件

```text
api_config.json (项目根目录):
{
    "apikey": "your-fofa-key",
    "base-url": "https://fafaapi.ccwu.cc:8443"
}
```
