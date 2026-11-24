"""抓北市交控中心即時VD資料（GetVD.xml.gz），只留辛亥路周邊路段，附加到 data/YYYY-MM-DD.csv。"""
import csv, gzip, os, re, urllib.request
from datetime import datetime, timedelta, timezone

SRC = "https://tcgbusfs.blob.core.windows.net/blobtisv/GetVD.xml.gz"
TARGETS = {
    "Z1001A0",  # 建國快往北 辛亥路上匝道
    "Z12G2E0",  # 建國快往南 辛亥路下匝道
    "Z1001B0",  # 建國快往北 辛亥高架接建高
    "Z3311G0",  # 辛亥高架 辛亥上匝道
    "Z3132C0",  # 辛亥高架 辛亥路下匝道
    "Z3320G0",  # 辛亥高架 新生泰順
    "ZDYN960",  # 辛亥路 基隆路-辛亥隧道
    "ZEFMN60",  # 辛亥路 辛亥隧道-基隆路
}
TPE = timezone(timedelta(hours=8))

def tag(block, name):
    m = re.search(rf"<vd:{name}>([^<]*)</vd:{name}>", block)
    return m.group(1) if m else ""

def main():
    req = urllib.request.Request(SRC, headers={"User-Agent": "xinhai-vd-collector"})
    raw = urllib.request.urlopen(req, timeout=60).read()
    txt = gzip.decompress(raw).decode("utf-8")
    xtime = tag(txt, "ExchangeTime")
    now = datetime.now(TPE)
    rows = []
    for b in re.findall(r"<vd:SectionData>.*?</vd:SectionData>", txt, flags=re.S):
        sid = tag(b, "SectionId")
        if sid in TARGETS:
            rows.append([now.strftime("%Y-%m-%d %H:%M:%S"), xtime, sid, tag(b, "SectionName").strip(),
                         tag(b, "AvgSpd"), tag(b, "AvgOcc"), tag(b, "TotalVol")])
    os.makedirs("data", exist_ok=True)
    path = os.path.join("data", now.strftime("%Y-%m-%d") + ".csv")
    new = not os.path.exists(path)
    with open(path, "a", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        if new:
            w.writerow(["fetched", "exchange", "id", "name", "avg_speed", "avg_occ", "total_vol"])
        w.writerows(rows)
    print(f"{now:%Y-%m-%d %H:%M} 寫入 {len(rows)} 筆")

if __name__ == "__main__":
    main()
