#!/usr/bin/env python3
"""把冰神 A 股名单加入已存在的富途自选分组。默认仅预览，不交易、不写提醒。"""

from __future__ import annotations

import argparse
import json

from futu import ModifyUserSecurityOp, OpenQuoteContext, RET_OK

CODES = [
    "SZ.002422", "SZ.002603", "SZ.002737", "SH.603983",
    "SH.688065", "SZ.300975", "SH.688662", "SH.688807",
    "SH.688143", "SH.688596", "SH.688758", "SH.688105",
    "SZ.301047", "SZ.000630", "SZ.001337", "SZ.301026",
    "SZ.300274",
]
CONFIRM = "ADD_17_A_SHARES"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--group", required=True, help="已在富途客户端创建的自选分组名")
    parser.add_argument("--apply", action="store_true", help="执行加入分组；不传则仅预览")
    parser.add_argument("--confirm", default="", help=f"执行时必须填写 {CONFIRM}")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=11111)
    args = parser.parse_args()

    ctx = OpenQuoteContext(host=args.host, port=args.port)
    try:
        ret, snapshot = ctx.get_market_snapshot(CODES)
        if ret != RET_OK:
            raise RuntimeError(f"证券核验失败: {snapshot}")
        validated = dict(zip(snapshot["code"].astype(str), snapshot["name"].astype(str)))
        missing = [code for code in CODES if code not in validated]
        if missing:
            raise RuntimeError(f"OpenD 未返回这些代码: {missing}")

        ret, before = ctx.get_user_security(args.group)
        if ret != RET_OK:
            raise RuntimeError(f"无法读取分组“{args.group}”: {before}")
        before_codes = set(before["code"].astype(str))
        additions = [code for code in CODES if code not in before_codes]
        preview = {
            "status": "DRY_RUN_NO_FUTU_WRITE",
            "group": args.group,
            "validated": validated,
            "already_present": [code for code in CODES if code in before_codes],
            "to_add": additions,
        }
        if not args.apply:
            print(json.dumps(preview, ensure_ascii=False, indent=2))
            return 0
        if args.confirm != CONFIRM:
            raise SystemExit(f"拒绝写入：请加 --apply --confirm {CONFIRM}")

        if additions:
            ret, message = ctx.modify_user_security(
                args.group, ModifyUserSecurityOp.ADD, additions
            )
            if ret != RET_OK:
                raise RuntimeError(f"加入分组失败: {message}")

        ret, after = ctx.get_user_security(args.group)
        if ret != RET_OK:
            raise RuntimeError(f"写后回读失败: {after}")
        absent = [code for code in CODES if code not in set(after["code"].astype(str))]
        if absent:
            raise RuntimeError(f"回读仍缺少: {absent}")

        print(json.dumps({
            "status": "VERIFIED_FUTU_OPEND",
            "group": args.group,
            "added": additions,
            "verified_count": len(CODES),
            "orders_created": 0,
            "reminders_created": 0,
        }, ensure_ascii=False, indent=2))
        return 0
    finally:
        ctx.close()


if __name__ == "__main__":
    raise SystemExit(main())
