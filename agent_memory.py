"""
agent_memory.py — Agent 自我进化记忆模块

四个维度的长期记忆:
  1. 动态经验库 — 高价值模式、Payload、特征沉淀
  2. 数据源信誉度 — API 源 + Kali-MCP 工具在不同场景下的质量评分
  3. 决策树日志 — 工作流执行记录与 ROI
  4. 错误纠正规则 — 解析失败、提取错误的自我修正

LLM 通过命令行调用，读写记忆:
  python agent_memory.py add-experience ...
  python agent_memory.py update-source ...
  python agent_memory.py record-workflow ...
  python agent_memory.py record-error ...
  python agent_memory.py query ...
  python agent_memory.py stats

支持的数据源:
  fofa, dork, crtsh, hackertarget, anubis, ...
  kali-gobuster-dns, kali-nmap, kali-nikto, kali-gobuster-dir, kali-wpscan

工作流步骤示例:
  subfinder→kali-nmap→kali-nikto
  fofa→dork→subfinder→kali-gobuster-dns
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

MEMORY_DIR = Path(__file__).parent / "memory"

FILES = {
    "experiences": MEMORY_DIR / "experiences.json",
    "source_scores": MEMORY_DIR / "source_scores.json",
    "workflow_log": MEMORY_DIR / "workflow_log.json",
    "error_corrections": MEMORY_DIR / "error_corrections.json",
}


def _load(name: str) -> list | dict:
    path = FILES[name]
    if not path.exists():
        return [] if name != "source_scores" else {}
    return json.loads(path.read_text(encoding="utf-8"))


def _save(name: str, data: list | dict):
    MEMORY_DIR.mkdir(parents=True, exist_ok=True)
    FILES[name].write_text(
        json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8"
    )


# ============================================================
# 1. 动态经验库
# ============================================================

def add_experience(category: str, content: str, tags: str, confidence: float):
    db = _load("experiences")
    entry = {
        "id": len(db) + 1,
        "category": category,
        "content": content,
        "tags": [t.strip() for t in tags.split(",")] if tags else [],
        "confidence": confidence,
        "hit_count": 0,
        "created_at": time.time(),
        "updated_at": time.time(),
    }
    db.append(entry)
    _save("experiences", db)
    print(json.dumps({"status": "ok", "id": entry["id"], "entry": entry}, ensure_ascii=False))


def query_experiences(category: str = "", tags: str = "", limit: int = 20):
    db = _load("experiences")
    results = db
    if category:
        results = [e for e in results if e["category"] == category]
    if tags:
        tag_set = set(t.strip() for t in tags.split(","))
        results = [e for e in results if tag_set & set(e["tags"])]
    results.sort(key=lambda e: e["confidence"], reverse=True)
    results = results[:limit]
    # 更新命中计数
    ids = {e["id"] for e in results}
    for e in db:
        if e["id"] in ids:
            e["hit_count"] += 1
            e["updated_at"] = time.time()
    _save("experiences", db)
    print(json.dumps(results, ensure_ascii=False, indent=2))


def bump_experience(entry_id: int, delta: float):
    """调整经验的置信度 (正向或负向反馈)"""
    db = _load("experiences")
    for e in db:
        if e["id"] == entry_id:
            e["confidence"] = max(0.0, min(1.0, e["confidence"] + delta))
            e["updated_at"] = time.time()
            _save("experiences", db)
            print(json.dumps({"status": "ok", "entry": e}, ensure_ascii=False))
            return
    print(json.dumps({"error": f"experience {entry_id} not found"}))


# ============================================================
# 2. 数据源信誉度评分
# ============================================================

def update_source(source: str, score: float, context: str, notes: str = ""):
    """更新某个 API 源在特定场景下的信誉分"""
    db = _load("source_scores")
    if source not in db:
        db[source] = {"records": [], "avg_score": 0.0, "total_uses": 0}
    rec = {
        "score": score,
        "context": context,
        "notes": notes,
        "timestamp": time.time(),
    }
    db[source]["records"].append(rec)
    db[source]["total_uses"] = len(db[source]["records"])
    scores = [r["score"] for r in db[source]["records"]]
    db[source]["avg_score"] = round(sum(scores) / len(scores), 2)
    # 只保留最近 50 条记录
    if len(db[source]["records"]) > 50:
        db[source]["records"] = db[source]["records"][-50:]
    _save("source_scores", db)
    print(json.dumps({"status": "ok", "source": source, "avg_score": db[source]["avg_score"]}))


def recommend_sources(context: str = ""):
    """推荐高信誉数据源，按平均分排序"""
    db = _load("source_scores")
    if not db:
        print(json.dumps({"message": "暂无数据源评分记录，请先积累数据"}))
        return
    ranked = sorted(
        ((src, info["avg_score"], info["total_uses"]) for src, info in db.items()),
        key=lambda x: x[1],
        reverse=True,
    )
    print(json.dumps(
        [{"source": s, "avg_score": sc, "total_uses": n} for s, sc, n in ranked],
        ensure_ascii=False, indent=2,
    ))


# ============================================================
# 3. 决策树日志 (工作流 ROI)
# ============================================================

def record_workflow(steps: str, outcome: str, roi: float, target: str = ""):
    """记录一次工作流的执行结果"""
    db = _load("workflow_log")
    entry = {
        "id": len(db) + 1,
        "steps": steps,
        "outcome": outcome,
        "roi": roi,
        "target": target,
        "timestamp": time.time(),
    }
    db.append(entry)
    _save("workflow_log", db)
    print(json.dumps({"status": "ok", "id": entry["id"]}, ensure_ascii=False))


def recommend_workflow(target: str = ""):
    """基于历史 ROI 推荐最优工作流"""
    db = _load("workflow_log")
    if not db:
        print(json.dumps({"message": "暂无工作流记录"}))
        return
    # 按 steps 分组，计算平均 ROI
    from collections import defaultdict
    groups: dict[str, list] = defaultdict(list)
    for e in db:
        groups[e["steps"]].append(e["roi"])
    ranked = sorted(
        ((steps, sum(roi) / len(roi), len(roi)) for steps, roi in groups.items()),
        key=lambda x: x[1],
        reverse=True,
    )
    print(json.dumps(
        [{"steps": s, "avg_roi": round(r, 3), "executions": n} for s, r, n in ranked],
        ensure_ascii=False, indent=2,
    ))


# ============================================================
# 4. 错误纠正规则
# ============================================================

def record_error(error: str, correction: str, rule: str):
    """记录一次错误及其纠正规则"""
    db = _load("error_corrections")
    entry = {
        "id": len(db) + 1,
        "error": error,
        "correction": correction,
        "rule": rule,
        "applied_count": 0,
        "timestamp": time.time(),
    }
    db.append(entry)
    _save("error_corrections", db)
    print(json.dumps({"status": "ok", "id": entry["id"]}, ensure_ascii=False))


def get_rules(context: str = ""):
    """获取所有纠正规则"""
    db = _load("error_corrections")
    # 更新应用计数
    for r in db:
        r["applied_count"] += 1
    _save("error_corrections", db)
    print(json.dumps(db, ensure_ascii=False, indent=2))


# ============================================================
# 汇总统计
# ============================================================

def show_stats():
    exp = _load("experiences")
    src = _load("source_scores")
    wf = _load("workflow_log")
    err = _load("error_corrections")

    stats = {
        "experiences": {
            "total": len(exp),
            "categories": list(set(e["category"] for e in exp)) if exp else [],
            "top_tags": _top_tags(exp, 10),
        },
        "source_scores": {
            "scored_sources": len(src),
            "top_sources": sorted(
                ((s, i["avg_score"]) for s, i in src.items()),
                key=lambda x: x[1], reverse=True,
            )[:10] if src else [],
        },
        "workflow_log": {
            "total_runs": len(wf),
            "avg_roi": round(sum(e["roi"] for e in wf) / len(wf), 3) if wf else 0,
        },
        "error_corrections": {
            "total_rules": len(err),
            "total_applications": sum(r["applied_count"] for r in err),
        },
    }
    print(json.dumps(stats, ensure_ascii=False, indent=2))


def _top_tags(experiences: list, n: int) -> list:
    from collections import Counter
    tags = Counter(t for e in experiences for t in e["tags"])
    return tags.most_common(n)


# ============================================================
# CLI
# ============================================================

def main():
    p = argparse.ArgumentParser(description="Agent 自我进化记忆模块")
    sub = p.add_subparsers(dest="command")

    # -- 经验库
    exp_add = sub.add_parser("add-experience", help="添加经验")
    exp_add.add_argument("--category", required=True, help="分类: pattern/payload/route/insight")
    exp_add.add_argument("--content", required=True, help="经验内容")
    exp_add.add_argument("--tags", default="", help="标签，逗号分隔")
    exp_add.add_argument("--confidence", type=float, default=0.7, help="初始置信度 0-1")

    exp_q = sub.add_parser("query-experiences", help="查询经验")
    exp_q.add_argument("--category", default="")
    exp_q.add_argument("--tags", default="")
    exp_q.add_argument("--limit", type=int, default=20)

    exp_bump = sub.add_parser("bump-experience", help="调整经验置信度")
    exp_bump.add_argument("--id", type=int, required=True)
    exp_bump.add_argument("--delta", type=float, required=True, help="正数提升，负数降低")

    # -- 数据源评分
    src_upd = sub.add_parser("update-source", help="更新数据源评分")
    src_upd.add_argument("--source", required=True)
    src_upd.add_argument("--score", type=float, required=True, help="评分 1-10")
    src_upd.add_argument("--context", default="general", help="场景描述")
    src_upd.add_argument("--notes", default="")

    src_rec = sub.add_parser("recommend-sources", help="推荐高信誉数据源")

    # -- 工作流
    wf_rec = sub.add_parser("record-workflow", help="记录工作流执行")
    wf_rec.add_argument("--steps", required=True, help="工作流步骤，如 subfinder->kali-nmap->kali-nikto")
    wf_rec.add_argument("--outcome", required=True, help="执行结果描述")
    wf_rec.add_argument("--roi", type=float, required=True, help="投资回报率 0-1")
    wf_rec.add_argument("--target", default="")

    wf_rec2 = sub.add_parser("recommend-workflow", help="推荐最优工作流")

    # -- 错误纠正
    err_rec = sub.add_parser("record-error", help="记录错误纠正")
    err_rec.add_argument("--error", required=True, help="错误描述")
    err_rec.add_argument("--correction", required=True, help="纠正方法")
    err_rec.add_argument("--rule", required=True, help="提取的通用规则")

    err_get = sub.add_parser("get-rules", help="获取所有纠正规则")

    # -- 统计
    sub.add_parser("stats", help="查看记忆统计")

    args = p.parse_args()

    if not args.command:
        p.print_help()
        return

    dispatch = {
        "add-experience": lambda: add_experience(args.category, args.content, args.tags, args.confidence),
        "query-experiences": lambda: query_experiences(args.category, args.tags, args.limit),
        "bump-experience": lambda: bump_experience(args.id, args.delta),
        "update-source": lambda: update_source(args.source, args.score, args.context, args.notes),
        "recommend-sources": lambda: recommend_sources(),
        "record-workflow": lambda: record_workflow(args.steps, args.outcome, args.roi, args.target),
        "recommend-workflow": lambda: recommend_workflow(),
        "record-error": lambda: record_error(args.error, args.correction, args.rule),
        "get-rules": lambda: get_rules(),
        "stats": lambda: show_stats(),
    }
    dispatch[args.command]()


if __name__ == "__main__":
    main()
