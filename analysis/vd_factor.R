# 由 data/ 下所有CSV算時段擴大係數：全日量÷（07至09時＋17至19時）
# 只用base R。在repo根目錄執行：Rscript analysis/vd_factor.R

files <- list.files("data", pattern = "\\.csv$", full.names = TRUE)
d <- do.call(rbind, lapply(files, read.csv, fileEncoding = "UTF-8"))

# 以交控中心資料時間為準；同一路段同一分鐘只留一筆
d$t    <- as.POSIXct(d$exchange, format = "%Y/%m/%dT%H:%M:%S", tz = "Asia/Taipei")
d      <- d[!is.na(d$t) & !duplicated(d[, c("id", "exchange")]), ]
d$date <- as.Date(format(d$t, "%Y-%m-%d"))
d$hour <- as.integer(format(d$t, "%H"))
d$wday <- as.integer(format(d$t, "%u"))   # 1＝週一 ... 7＝週日
holidays <- as.Date(character(0))           # 國定假日請填在這裡
d <- d[d$wday <= 5 & !(d$date %in% holidays), ]

# 每小時平均流量（比例不受原始資料單位影響）；每小時至少30分鐘有資料才算
h  <- aggregate(total_vol ~ id + date + hour, data = d, FUN = mean)
nm <- aggregate(total_vol ~ id + date + hour, data = d, FUN = length)
h  <- h[nm$total_vol >= 30, ]
n_h <- aggregate(hour ~ id + date, data = h, FUN = length)
full_days <- n_h[n_h$hour == 24, c("id", "date")]
if (nrow(full_days) == 0) stop("還沒有任何路段收滿一個完整平日（24小時、每小時至少30分鐘）")
h <- merge(h, full_days)

counted <- c(7, 8, 17, 18)   # 路口計數涵蓋的4個小時
f <- do.call(rbind, lapply(split(h, list(h$id, h$date), drop = TRUE), function(x)
  data.frame(id = x$id[1], date = x$date[1],
             factor = sum(x$total_vol) / sum(x$total_vol[x$hour %in% counted]))))
names_tbl <- unique(d[, c("id", "name")])
res <- aggregate(factor ~ id, data = f, FUN = function(v) c(mean = mean(v), sd = sd(v), n = length(v)))
res <- do.call(data.frame, res)
names(res) <- c("id", "擴大係數平均", "標準差", "天數")
res <- merge(names_tbl[!duplicated(names_tbl$id), ], res)
print(res, row.names = FALSE)

prof <- aggregate(total_vol ~ id + hour, data = h, FUN = mean)
prof$share <- ave(prof$total_vol, prof$id, FUN = function(v) v / sum(v))
write.csv(prof, "analysis/hourly_profile.csv", row.names = FALSE, fileEncoding = "UTF-8")
cat("\n用法：辛亥路全日量 ≈（07至09時＋17至19時的計數合計）× 擴大係數\n")
