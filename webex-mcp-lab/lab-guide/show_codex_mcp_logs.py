# Show Codex MCP client logs from the SQLite log store (Codex >= 0.150).
# Usage:
#   python show_codex_mcp_logs.py            # last 50 MCP-related entries
#   python show_codex_mcp_logs.py --all      # all MCP-related entries
#   python show_codex_mcp_logs.py --follow   # live tail (poll every 1s)
#   python show_codex_mcp_logs.py --out FILE # write to a specific log file
# Output is always written to a .log file (default: codex-mcp.log next to this
# script) in addition to being printed to the console.

import argparse
import os
import sqlite3
import time

DB = os.path.join(os.environ["USERPROFILE"], ".codex", "logs_2.sqlite")
DEFAULT_LOG = os.path.join(os.path.dirname(os.path.abspath(__file__)), "codex-mcp.log")

# Targets/keywords that identify MCP client activity in Codex's log store.
FILTER = """
       lower(target) like '%mcp%'
    or lower(feedback_log_body) like '%mcp%'
    or lower(feedback_log_body) like '%webex%'
    or lower(feedback_log_body) like '%greet%'
"""


def rows(after_id: int = 0, limit: int | None = 50):
    con = sqlite3.connect(f"file:{DB}?mode=ro", uri=True)
    q = f"""
        select id, datetime(ts,'unixepoch','localtime') as t, level, target,
               substr(feedback_log_body,1,500)
        from logs
        where ({FILTER}) and id > ?
        order by id
    """
    data = list(con.execute(q, (after_id,)))
    con.close()
    if limit is not None and len(data) > limit:
        data = data[-limit:]
    return data


def show(data, sink):
    for r in data:
        line1 = f"[{r[1]}] {r[2]:5} {r[3]}"
        line2 = f"    {r[4]}"
        print(line1)
        print(line2)
        sink.write(line1 + "\n")
        sink.write(line2 + "\n")
    sink.flush()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--all", action="store_true", help="show all entries")
    ap.add_argument("--follow", action="store_true", help="live tail")
    ap.add_argument("--out", default=DEFAULT_LOG, help="log file path (default: codex-mcp.log)")
    args = ap.parse_args()

    # --follow appends so a live session extends the file; snapshots overwrite.
    mode = "a" if args.follow else "w"
    with open(args.out, mode, encoding="utf-8") as sink:
        print(f"# writing to {args.out}")
        if args.follow:
            last = rows(limit=1)
            last_id = last[-1][0] if last else 0
            show(rows(after_id=0, limit=20), sink)
            print("--- following (Ctrl+C to stop) ---")
            try:
                while True:
                    new = rows(after_id=last_id, limit=None)
                    if new:
                        show(new, sink)
                        last_id = new[-1][0]
                    time.sleep(1)
            except KeyboardInterrupt:
                pass
        else:
            show(rows(limit=None if args.all else 50), sink)


if __name__ == "__main__":
    main()
