"""檢查 data/*.csv 的完整度：每天每小時有幾分鐘的資料、哪幾天是完整的平日。"""
import csv, glob, os
from collections import defaultdict
from datetime import datetime

base = os.path.join(os.path.dirname(__file__), "..", "data")
mins = defaultdict(set)   # (date, hour) -> set of minutes
for f in sorted(glob.glob(os.path.join(base, "*.csv"))):
    for r in csv.DictReader(open(f, encoding="utf-8")):
        try:
            t = datetime.strptime(r["exchange"], "%Y/%m/%dT%H:%M:%S")
        except ValueError:
            continue
        mins[(t.date(), t.hour)].add(t.minute)
days = sorted({d for d, _ in mins})
for d in days:
    cov = [len(mins.get((d, h), ())) for h in range(24)]
    full = all(c >= 30 for c in cov)
    tag = "平日" if d.isoweekday() <= 5 else "假日"
    print(f"{d} {tag} {'完整' if full else '不完整'}  每小時分鐘數：{cov}")
