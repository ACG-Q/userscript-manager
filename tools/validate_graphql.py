#!/usr/bin/env python3
"""用 GitHub 官方 GraphQL schema 校验仓库内全部查询与变更。

背景：单测里的假客户端按「查询子串」路由，字段名写错照样全绿——
`Query.discussion` 这类不存在的字段只有线上真请求才暴露。本工具在 CI 里
提前把它们拦下来。

用法::

    python tools/validate_graphql.py            # 自动下载/复用缓存 schema
    python tools/validate_graphql.py --schema path/to/schema.graphql
    python tools/validate_graphql.py --offline  # 只用缓存，缺了就报错

schema 来源：GitHub 官方发布的 schema（docs.github.com/public/fpt/schema.docs.graphql）
缓存于 tools/schema.docs.graphql（已 gitignore），可用 GITHUB_SCHEMA_FILE 指定。
退出码非 0 表示存在非法字段/参数/变量。
"""
from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

# GitHub 官方发布的 GraphQL schema（fpt = free/pro/team，即 Actions 令牌实际可用的 API 面）
SCHEMA_URL = "https://docs.github.com/public/fpt/schema.docs.graphql"
DEFAULT_CACHE = Path(__file__).resolve().parent / "schema.docs.graphql"


def collect_queries() -> dict[str, str]:
    """收集仓库内全部 GraphQL 文本（常量 + 生成式查询）。"""
    from panel_cleanup import DELETE_COMMENT_MUTATION, PANEL_QUERY
    from project_issues import (
        CLOSE_MUTATION,
        CREATE_LABEL_MUTATION,
        CREATE_MUTATION,
        LABELS_QUERY,
        LIST_QUERY,
        REOPEN_MUTATION,
        REPO_QUERY,
        UPDATE_MUTATION,
    )
    from userscript_manager.discussions import (
        CREATE_DISCUSSION_MUTATION,
        DISCUSSION_CATEGORIES_QUERY,
        DISCUSSION_NODE_QUERY,
    )
    from userscript_manager.issue_stats import build_query

    return {
        "project_issues.REPO_QUERY": REPO_QUERY,
        "project_issues.LABELS_QUERY": LABELS_QUERY,
        "project_issues.LIST_QUERY": LIST_QUERY,
        "project_issues.CREATE_LABEL_MUTATION": CREATE_LABEL_MUTATION,
        "project_issues.CREATE_MUTATION": CREATE_MUTATION,
        "project_issues.UPDATE_MUTATION": UPDATE_MUTATION,
        "project_issues.CLOSE_MUTATION": CLOSE_MUTATION,
        "project_issues.REOPEN_MUTATION": REOPEN_MUTATION,
        "discussions.DISCUSSION_CATEGORIES_QUERY": DISCUSSION_CATEGORIES_QUERY,
        "discussions.CREATE_DISCUSSION_MUTATION": CREATE_DISCUSSION_MUTATION,
        "discussions.DISCUSSION_NODE_QUERY": DISCUSSION_NODE_QUERY,
        "issue_stats.build_query(1)": build_query(1),
        "panel_cleanup.PANEL_QUERY": PANEL_QUERY,
        "panel_cleanup.DELETE_COMMENT_MUTATION": DELETE_COMMENT_MUTATION,
    }


def _download_schema() -> str:
    """下载 schema（带重试与体积校验，避免把残缺内容当缓存）。"""
    import time

    import requests

    last: Exception | None = None
    for attempt in range(1, 4):
        try:
            resp = requests.get(SCHEMA_URL, timeout=120)
            resp.raise_for_status()
            text = resp.text
            if len(text) < 100_000:
                raise RuntimeError(f"下载内容异常：仅 {len(text)} 字节")
            return text
        except Exception as e:  # 网络抖动常见，重试三次
            last = e
            print(f"schema 下载失败（第 {attempt}/3 次）：{e}", file=sys.stderr)
            time.sleep(2 * attempt)
    raise SystemExit(f"schema 下载失败：{last}")


def load_schema(path: Path, offline: bool):
    """读取 schema SDL；缓存缺失且非 offline 时下载一次（原子写入）。"""
    from graphql import build_schema

    if not path.exists():
        if offline:
            raise SystemExit(f"离线模式下找不到 schema：{path}")
        print(f"下载 schema → {path}", file=sys.stderr)
        tmp = path.with_suffix(path.suffix + ".part")
        tmp.write_text(_download_schema(), encoding="utf-8")
        tmp.replace(path)
    # assume_valid：GitHub 官方 schema 自身有若干 @deprecated 元数据不一致，
    # graphql-core 会据此拒绝整个 schema；我们只需要它的字段定义来做查询校验。
    return build_schema(path.read_text(encoding="utf-8"), assume_valid=True)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--schema", type=Path,
        default=Path(os.environ.get("GITHUB_SCHEMA_FILE") or DEFAULT_CACHE),
        help="schema SDL 文件路径（默认 tools/schema.docs.graphql）")
    parser.add_argument("--offline", action="store_true",
                        help="不下载，只用本地 schema")
    args = parser.parse_args(argv)

    from graphql import parse, validate

    schema = load_schema(args.schema, args.offline)
    queries = collect_queries()
    failed = 0
    for name, text in queries.items():
        try:
            document = parse(text)
        except Exception as e:  # 语法错误
            failed += 1
            print(f"✗ {name}: 语法错误 {e}", file=sys.stderr)
            continue
        errors = validate(schema, document)
        if errors:
            failed += 1
            for err in errors:
                print(f"✗ {name}: {err.message}", file=sys.stderr)
        else:
            print(f"✓ {name}")
    if failed:
        print(f"\n{failed}/{len(queries)} 个查询未通过 schema 校验",
              file=sys.stderr)
        return 1
    print(f"\n全部 {len(queries)} 个查询通过 schema 校验")
    return 0


if __name__ == "__main__":
    sys.exit(main())
