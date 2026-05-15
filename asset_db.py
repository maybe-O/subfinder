"""
asset_db.py — 资产数据库管理工具

SQLite 数据库，存储来自 FOFA / Dorking / Subfinder / Kali-MCP 的资产数据。
支持 JSON 导入、去重、查询、导出。

用法:
  python asset_db.py init                                    # 初始化数据库
  python asset_db.py import-fofa results.json --target example.com
  python asset_db.py import-dork results.json --target example.com
  python asset_db.py import-subfinder results.json
  python asset_db.py import-kali results.json --source kali-gobuster-dns --target example.com
  python asset_db.py import-kali results.json --source kali-nmap --target example.com
  python asset_db.py list [--target example.com] [--source fofa|dork|subfinder|kali-gobuster-dns|kali-nmap]
  python asset_db.py stats
  python asset_db.py export [--target example.com] -o output.json
  python asset_db.py merge-hosts                            # 从所有来源合并唯一主机列表
"""

from __future__ import annotations

import argparse
import json
import sqlite3
import sys
from datetime import datetime
from pathlib import Path

DB_PATH = str(Path(__file__).parent / "assets.db")


def get_conn() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


def init_db():
    """建表"""
    conn = get_conn()
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS targets (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            domain      TEXT NOT NULL UNIQUE,
            created_at  TEXT NOT NULL DEFAULT (datetime('now','localtime')),
            notes       TEXT
        );

        CREATE TABLE IF NOT EXISTS assets (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            target_id   INTEGER NOT NULL REFERENCES targets(id),
            host        TEXT NOT NULL,
            ip          TEXT,
            port        TEXT,
            protocol    TEXT,
            title       TEXT,
            domain      TEXT,
            url         TEXT,
            source      TEXT NOT NULL DEFAULT 'unknown',
            source_detail TEXT,
            found_at    TEXT NOT NULL DEFAULT (datetime('now','localtime')),
            UNIQUE(target_id, host, source)
        );

        CREATE TABLE IF NOT EXISTS import_log (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            target      TEXT NOT NULL,
            source      TEXT NOT NULL,
            file        TEXT,
            imported    INTEGER NOT NULL DEFAULT 0,
            skipped     INTEGER NOT NULL DEFAULT 0,
            created_at  TEXT NOT NULL DEFAULT (datetime('now','localtime'))
        );

        CREATE INDEX IF NOT EXISTS idx_assets_host     ON assets(host);
        CREATE INDEX IF NOT EXISTS idx_assets_target   ON assets(target_id);
        CREATE INDEX IF NOT EXISTS idx_assets_source   ON assets(source);
        CREATE INDEX IF NOT EXISTS idx_assets_ip       ON assets(ip);
    """)
    conn.commit()
    conn.close()
    print(f"Database initialized: {DB_PATH}")


def _ensure_target(conn, domain: str) -> int:
    """确保 target 存在，返回 id"""
    row = conn.execute("SELECT id FROM targets WHERE domain=?", (domain,)).fetchone()
    if row:
        return row["id"]
    cur = conn.execute("INSERT INTO targets (domain) VALUES (?)", (domain,))
    conn.commit()
    return cur.lastrowid


# =============================================================================
# FOFA 导入
# =============================================================================

def import_fofa(file_path: str, target: str):
    """
    导入 FOFA API 返回的 JSON。

    支持两种格式:
    1. fofa_tool.py 的输出: {"records": [{host:"...", ip:"...", ...}], "domains_extracted": [...], "hosts_extracted": [...]}
    2. FOFA API 原始返回: {"results": [["host","ip",...]], "fields": "host,ip,..."}
    """
    with open(file_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    conn = get_conn()
    tid = _ensure_target(conn, target)
    imported, skipped = 0, 0

    # 格式1: fofa_tool.py 输出 (records 是 dict 列表)
    if isinstance(data.get("records"), list) and data["records"] and isinstance(data["records"][0], dict):
        for rec in data["records"]:
            raw_host = rec.get("host", "")
            # 去掉协议和端口
            host = raw_host.split("://")[-1].split(":")[0] if raw_host else ""
            if not host:
                continue
            try:
                conn.execute(
                    "INSERT OR IGNORE INTO assets (target_id, host, ip, port, protocol, title, domain, source, source_detail) "
                    "VALUES (?,?,?,?,?,?,?,'fofa',?)",
                    (tid, host, rec.get("ip"), rec.get("port"), rec.get("protocol"),
                     rec.get("title"), rec.get("domain"), data.get("query", "")),
                )
                if conn.total_changes > (imported + skipped):
                    imported += 1
                else:
                    skipped += 1
            except sqlite3.IntegrityError:
                skipped += 1

    # 格式2: FOFA API 原始返回 (results 是二维数组)
    elif isinstance(data.get("results"), list):
        fields = data.get("fields", "host,ip,port,protocol,title,domain").split(",")
        fields = [f.strip() for f in fields]
        field_idx = {f: i for i, f in enumerate(fields)}

        for row in data["results"]:
            if not isinstance(row, list):
                continue

            def _get(field, default=""):
                idx = field_idx.get(field, -1)
                return str(row[idx]) if idx >= 0 and idx < len(row) else default

            raw_host = _get("host")
            host = raw_host.split("://")[-1].split(":")[0] if raw_host else ""
            if not host:
                continue

            try:
                conn.execute(
                    "INSERT OR IGNORE INTO assets (target_id, host, ip, port, protocol, title, domain, source, source_detail) "
                    "VALUES (?,?,?,?,?,?,?,'fofa','')",
                    (tid, host, _get("ip"), _get("port"), _get("protocol"),
                     _get("title"), _get("domain")),
                )
                if conn.total_changes > (imported + skipped):
                    imported += 1
                else:
                    skipped += 1
            except sqlite3.IntegrityError:
                skipped += 1

    # 记录导入日志
    conn.execute(
        "INSERT INTO import_log (target, source, file, imported, skipped) VALUES (?,?,?,?,?)",
        (target, "fofa", file_path, imported, skipped),
    )
    conn.commit()
    conn.close()
    print(f"[FOFA] {target}: imported {imported}, skipped {skipped}")


# =============================================================================
# Dork 导入
# =============================================================================

def import_dork(file_path: str, target: str):
    """
    导入 dork_tool.py 的输出:
    {"records": [{host:"...", source_query:"...", url:"..."}], "subdomains": [...]}
    """
    with open(file_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    conn = get_conn()
    tid = _ensure_target(conn, target)
    imported, skipped = 0, 0

    records = data.get("records", [])
    for rec in records:
        host = rec.get("host", "")
        if not host:
            continue
        try:
            conn.execute(
                "INSERT OR IGNORE INTO assets (target_id, host, url, source, source_detail) VALUES (?,?,?,'dork',?)",
                (tid, host, rec.get("url", ""), rec.get("source_query", "")),
            )
            if conn.total_changes > (imported + skipped):
                imported += 1
            else:
                skipped += 1
        except sqlite3.IntegrityError:
            skipped += 1

    conn.execute(
        "INSERT INTO import_log (target, source, file, imported, skipped) VALUES (?,?,?,?,?)",
        (target, "dork", file_path, imported, skipped),
    )
    conn.commit()
    conn.close()
    print(f"[DORK] {target}: imported {imported}, skipped {skipped}")


# =============================================================================
# Subfinder 导入
# =============================================================================

def import_subfinder(file_path: str):
    """
    导入 subfinder_tool.py 的输出:
    {"target":"...", "records": [{host:"...", input:"...", sources:[...]}], "source_stats":{...}}
    """
    with open(file_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    target = data.get("target", "")
    if not target:
        print("Error: no 'target' field in subfinder output")
        return

    conn = get_conn()
    tid = _ensure_target(conn, target)
    imported, skipped = 0, 0

    for rec in data.get("records", []):
        host = rec.get("host", "")
        if not host:
            continue
        srcs = rec.get("sources") or [rec.get("source", "unknown")]
        source_detail = ",".join(srcs) if isinstance(srcs, list) else str(srcs)
        try:
            conn.execute(
                "INSERT OR IGNORE INTO assets (target_id, host, source, source_detail) VALUES (?,?,'subfinder',?)",
                (tid, host, source_detail),
            )
            if conn.total_changes > (imported + skipped):
                imported += 1
            else:
                skipped += 1
        except sqlite3.IntegrityError:
            skipped += 1

    conn.execute(
        "INSERT INTO import_log (target, source, file, imported, skipped) VALUES (?,?,?,?,?)",
        (target, "subfinder", file_path, imported, skipped),
    )
    conn.commit()
    conn.close()
    print(f"[SUBFINDER] {target}: imported {imported}, skipped {skipped}")


# =============================================================================
# Kali-MCP 导入
# =============================================================================

def import_kali(file_path: str, target: str, kali_source: str):
    """
    导入 Kali-MCP 工具的输出。

    支持格式:
    1. Gobuster DNS 输出: {"mode": "dns", "url": "example.com", "results": [{"host": "admin.example.com"}, ...]}
    2. Gobuster Dir  输出: {"mode": "dir", "url": "https://...", "results": [{"path": "/admin", "status": 200}, ...]}
    3. Nmap 扫描输出: {"target": "host", "results": [{"host": "...", "ports": [{"port": 80, "service": "http"}]}, ...]}
    4. 通用格式: {"hosts": ["host1.example.com", "host2.example.com"]}
    5. 简单文本: 每行一个 host
    """
    # 试 JSON
    records = []
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            data = json.load(f)
    except (json.JSONDecodeError, UnicodeDecodeError):
        data = None

    if data and isinstance(data, dict):
        # 格式 1/2: results 列表
        results = data.get("results", [])
        if results:
            for r in results:
                if isinstance(r, dict):
                    host = r.get("host") or r.get("hostname") or r.get("url") or r.get("path", "")
                elif isinstance(r, str):
                    host = r
                else:
                    continue
                # 去掉协议和路径
                host = host.split("://")[-1].split("/")[0].split(":")[0]
                if host:
                    records.append(host)
        # 格式 4: hosts 列表
        hosts = data.get("hosts", [])
        for h in hosts:
            if isinstance(h, str):
                h = h.split("://")[-1].split("/")[0].split(":")[0]
                if h:
                    records.append(h)
    else:
        # 格式 5: 纯文本，每行一个 host (支持 "Found: host" 格式)
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                for line in f:
                    host = line.strip()
                    if not host or host.startswith("#") or host.startswith("["):
                        continue
                    # 处理 gobuster "Found: host" 格式
                    if host.startswith("Found: "):
                        host = host[len("Found: "):]
                    # 去掉协议、端口、路径
                    host = host.split("://")[-1].split("/")[0].rsplit(":", 1)[0] if ":" in host.split("://")[-1].split("/")[0] else host.split("://")[-1].split("/")[0]
                    # 简单提取: 去掉协议，去掉路径，去掉端口(如果看起来像端口)
                    clean = host.split("://")[-1].split("/")[0]
                    # 检查是否是 IP:port 或 host:port 格式
                    parts = clean.split(":")
                    if len(parts) == 2 and parts[1].isdigit():
                        host = parts[0]
                    elif len(parts) > 2:
                        # IPv6 or something else, just use full
                        host = clean
                    else:
                        host = clean
                    if host:
                        records.append(host)
        except Exception:
            print(f"Error: unable to parse {file_path}")
            return

    if not records:
        print(f"No hosts found in {file_path}")
        return

    conn = get_conn()
    tid = _ensure_target(conn, target)
    imported, skipped = 0, 0

    for host in set(records):  # 去重
        try:
            conn.execute(
                "INSERT OR IGNORE INTO assets (target_id, host, source, source_detail) VALUES (?,?,?,?)",
                (tid, host, kali_source, ""),
            )
            if conn.total_changes > (imported + skipped):
                imported += 1
            else:
                skipped += 1
        except sqlite3.IntegrityError:
            skipped += 1

    conn.execute(
        "INSERT INTO import_log (target, source, file, imported, skipped) VALUES (?,?,?,?,?)",
        (target, kali_source, file_path, imported, skipped),
    )
    conn.commit()
    conn.close()
    print(f"[{kali_source.upper()}] {target}: imported {imported}, skipped {skipped}")


# =============================================================================
# 查询
# =============================================================================

def list_assets(target: str | None = None, source: str | None = None):
    conn = get_conn()
    sql = """
        SELECT a.host, a.ip, a.port, a.protocol, a.title, a.source, t.domain as target
        FROM assets a JOIN targets t ON a.target_id = t.id
        WHERE 1=1
    """
    params: list = []
    if target:
        sql += " AND t.domain = ?"
        params.append(target)
    if source:
        sql += " AND a.source = ?"
        params.append(source)
    sql += " ORDER BY a.host"

    rows = conn.execute(sql, params).fetchall()
    conn.close()

    if not rows:
        print("No assets found.")
        return

    print(f"{'Host':<40} {'IP':<16} {'Port':<6} {'Source':<10} {'Title'}")
    print("-" * 100)
    for r in rows:
        title = (r["title"] or "")[:30]
        print(f"{r['host']:<40} {r['ip'] or '':<16} {r['port'] or '':<6} {r['source']:<10} {title}")
    print(f"\nTotal: {len(rows)}")


def show_stats():
    conn = get_conn()

    print("=== Targets ===")
    for r in conn.execute("SELECT domain, created_at FROM targets ORDER BY domain").fetchall():
        print(f"  {r['domain']}  (created: {r['created_at']})")

    print("\n=== Assets by Source ===")
    for r in conn.execute("SELECT source, COUNT(*) as cnt FROM assets GROUP BY source ORDER BY cnt DESC").fetchall():
        print(f"  {r['source']}: {r['cnt']}")

    print("\n=== Assets by Target ===")
    for r in conn.execute(
        "SELECT t.domain, COUNT(a.id) as cnt FROM targets t LEFT JOIN assets a ON t.id=a.target_id GROUP BY t.domain ORDER BY cnt DESC"
    ).fetchall():
        print(f"  {r['domain']}: {r['cnt']}")

    print("\n=== Unique Hosts (all sources combined) ===")
    total = conn.execute("SELECT COUNT(DISTINCT host) FROM assets").fetchone()[0]
    cross = conn.execute(
        "SELECT COUNT(*) FROM (SELECT host FROM assets GROUP BY host HAVING COUNT(DISTINCT source) >= 2)"
    ).fetchone()[0]
    print(f"  Total unique: {total}")
    print(f"  Cross-verified (2+ sources): {cross}")

    print("\n=== Import Log ===")
    for r in conn.execute("SELECT * FROM import_log ORDER BY created_at DESC LIMIT 10").fetchall():
        print(f"  [{r['created_at']}] {r['source']} → {r['target']}: +{r['imported']} (skip {r['skipped']}) from {r['file']}")

    conn.close()


def merge_hosts(target: str | None = None):
    """合并所有来源，输出唯一主机列表及交叉验证"""
    conn = get_conn()
    sql = """
        SELECT a.host, GROUP_CONCAT(DISTINCT a.source) as sources,
               COUNT(DISTINCT a.source) as source_count,
               GROUP_CONCAT(DISTINCT a.ip) as ips,
               GROUP_CONCAT(DISTINCT a.title) as titles
        FROM assets a JOIN targets t ON a.target_id = t.id
        WHERE 1=1
    """
    params: list = []
    if target:
        sql += " AND t.domain = ?"
        params.append(target)
    sql += " GROUP BY a.host ORDER BY source_count DESC, a.host"

    rows = conn.execute(sql, params).fetchall()
    conn.close()

    if not rows:
        print("No hosts found.")
        return

    cross = [r for r in rows if r["source_count"] >= 2]
    single = [r for r in rows if r["source_count"] == 1]

    print(f"=== Merged Hosts ({len(rows)} total) ===\n")
    print(f"--- Cross-verified ({len(cross)}) ---")
    for r in cross:
        print(f"  {r['host']:<40} [{r['sources']}]  IPs: {r['ips'] or '-'}")

    print(f"\n--- Single source ({len(single)}) ---")
    for r in single:
        print(f"  {r['host']:<40} [{r['sources']}]")


def export_assets(target: str | None = None, output: str | None = None):
    conn = get_conn()
    sql = """
        SELECT a.host, a.ip, a.port, a.protocol, a.title, a.domain, a.source, a.source_detail, a.url, t.domain as target_domain
        FROM assets a JOIN targets t ON a.target_id = t.id
        WHERE 1=1
    """
    params: list = []
    if target:
        sql += " AND t.domain = ?"
        params.append(target)
    sql += " ORDER BY a.host"

    rows = conn.execute(sql, params).fetchall()
    conn.close()

    records = [dict(r) for r in rows]
    result = {
        "target": target or "all",
        "total": len(records),
        "exported_at": datetime.now().isoformat(),
        "records": records,
    }

    text = json.dumps(result, ensure_ascii=False, indent=2)
    if output:
        Path(output).write_text(text, encoding="utf-8")
        print(f"Exported {len(records)} records to {output}")
    else:
        print(text)


# =============================================================================
# CLI
# =============================================================================

def main():
    p = argparse.ArgumentParser(description="资产数据库管理工具")
    sub = p.add_subparsers(dest="command")

    sub.add_parser("init", help="初始化数据库")

    imp_fofa = sub.add_parser("import-fofa", help="导入 FOFA JSON")
    imp_fofa.add_argument("file", help="JSON 文件路径")
    imp_fofa.add_argument("--target", required=True, help="目标域名")

    imp_dork = sub.add_parser("import-dork", help="导入 Dork JSON")
    imp_dork.add_argument("file", help="JSON 文件路径")
    imp_dork.add_argument("--target", required=True, help="目标域名")

    imp_sf = sub.add_parser("import-subfinder", help="导入 Subfinder JSON")
    imp_sf.add_argument("file", help="JSON 文件路径")

    imp_kali = sub.add_parser("import-kali", help="导入 Kali-MCP 工具输出")
    imp_kali.add_argument("file", help="JSON/文本文件路径")
    imp_kali.add_argument("--target", required=True, help="目标域名")
    imp_kali.add_argument("--source", required=True, help="Kali 工具来源 (kali-gobuster-dns/kali-nmap/kali-nikto/kali-gobuster-dir/kali-wpscan)")

    ls = sub.add_parser("list", help="列出资产")
    ls.add_argument("--target", help="按目标域名过滤")
    ls.add_argument("--source", help="按来源过滤 (fofa/dork/subfinder/kali-gobuster-dns/kali-nmap/kali-gobuster-dir)")

    sub.add_parser("stats", help="数据库统计")

    mh = sub.add_parser("merge-hosts", help="合并所有来源，输出唯一主机")
    mh.add_argument("--target", help="按目标域名过滤")

    ex = sub.add_parser("export", help="导出为 JSON")
    ex.add_argument("--target", help="按目标域名过滤")
    ex.add_argument("-o", "--output", help="输出文件路径")

    args = p.parse_args()

    if args.command == "init":
        init_db()
    elif args.command == "import-fofa":
        import_fofa(args.file, args.target)
    elif args.command == "import-dork":
        import_dork(args.file, args.target)
    elif args.command == "import-subfinder":
        import_subfinder(args.file)
    elif args.command == "import-kali":
        import_kali(args.file, args.target, args.source)
    elif args.command == "list":
        list_assets(args.target, args.source)
    elif args.command == "stats":
        show_stats()
    elif args.command == "merge-hosts":
        merge_hosts(args.target)
    elif args.command == "export":
        export_assets(args.target, args.output)
    else:
        p.print_help()


if __name__ == "__main__":
    main()
