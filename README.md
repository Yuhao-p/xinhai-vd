# xinhai-vd

用GitHub Actions每分鐘抓一次臺北市交控中心的即時VD資料（GetVD.xml.gz），只保留辛亥路周邊路段，存到 `data/日期_執行編號.csv`。用途：計算辛亥路的時段擴大係數（全日量÷07至09時＋17至19時）。

- 資料來源：臺北市即時交通資訊，臺北交控中心
- 欄位：fetched（抓取時間，台北時間）、exchange（交控中心資料時間）、id、name、avg_speed、avg_occ、total_vol
- 停止收集：到 Actions 頁面把 collect-vd 停用（Disable workflow）

## 檢查與分析
- `python3 analysis/check_coverage.py`：每天每小時有幾分鐘資料，哪幾天是完整平日
- `Rscript analysis/vd_factor.R`：算時段擴大係數（全日量÷07至09時＋17至19時）
