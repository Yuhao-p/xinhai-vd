"""辛亥路事故地圖（GIS）
底圖：OpenStreetMap（gis/osm_xinhai.geojson，由 .github/workflows/osm.yml 抓取；© OpenStreetMap contributors, ODbL）
事故：accident_classified.csv（accident_classify.py輸出）
座標系：TWD97 / TM2 121（EPSG:3826）
用法：python3 accident_map.py <accident_classified.csv> <polygon.geojson> <輸出資料夾>
"""
import json, sys
import geopandas as gpd, pandas as pd, numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib import font_manager
from matplotlib.lines import Line2D
from shapely.geometry import LineString, Polygon, Point

CSV, POLY, OUT = sys.argv[1], sys.argv[2], sys.argv[3]
HERE = __file__.rsplit("/", 1)[0]
for f in font_manager.findSystemFonts():
    if "NotoSansCJK-Regular" in f or "NotoSansCJK-Medium" in f: font_manager.fontManager.addfont(f)
plt.rcParams["font.family"] = ["Noto Sans CJK TC", "Noto Sans CJK JP", "sans-serif"]

# ---- 底圖 ----
raw = gpd.read_file(f"{HERE}/osm_xinhai.geojson")
rows = []
for _, e in raw.iterrows():
    t = {k: v for k, v in e.items() if k != "geometry" and isinstance(v, str)}
    g = e.geometry
    if g is None: continue
    poly_like = g.geom_type in ("Polygon", "MultiPolygon")
    if "building" in t and poly_like: kind = "building"
    elif poly_like and (t.get("leisure") in {"park", "pitch", "garden", "playground", "sports_centre", "track", "stadium"} or t.get("landuse") in {"grass", "forest", "recreation_ground"}): kind = "green"
    elif poly_like and t.get("amenity") == "university": kind = "campus"
    elif "highway" in t and g.geom_type == "LineString": kind = "road:" + t["highway"]
    else: continue
    rows.append(dict(kind=kind, name=t.get("name", ""), bridge=t.get("bridge", ""), layer=t.get("layer", "0"), geometry=g))
base = gpd.GeoDataFrame(rows, crs=4326).to_crs(3826)

# ---- 事故 ----
d = pd.read_csv(CSV)
def cls(s):
    if s.startswith("A"): return "A"
    if s.startswith("B"): return "B"
    return "C2" if "不在辛亥路主線" in s else "C1"
d["cls"] = d["分類"].map(cls)
acc = gpd.GeoDataFrame(d, geometry=gpd.points_from_xy(d["經度"], d["緯度"]), crs=4326).to_crs(3826)
# 同一座標的事故以螺旋散開（僅供視覺辨識）
key = acc.geometry.x.round(0).astype(str) + "," + acc.geometry.y.round(0).astype(str)
n = acc.groupby(key).cumcount().values
r, a = 2.6 * np.sqrt(n), n * 2.4
acc["px"], acc["py"] = acc.geometry.x + r * np.cos(a), acc.geometry.y + r * np.sin(a)
poly = gpd.read_file(POLY).to_crs(3826)

STYLE = {"A": dict(fc="#c8371e", ec="#7a1d0c", label="A 可望消失：直行汽車之間"),
         "B": dict(fc="white", ec="#c8371e", label="B 部分減少：直行汽車與機車、自行車、行人"),
         "C1": dict(fc="#4a4641", ec="white", label="C 不受影響：主線上無直行汽車"),
         "C2": dict(fc="#a39d94", ec="white", label="C 不受影響：匝道或交叉道路")}
MAJOR = {"trunk", "primary", "secondary", "tertiary", "trunk_link", "primary_link", "secondary_link", "tertiary_link"}
MINOR = {"residential", "unclassified", "service", "living_street"}

minx, miny, maxx, maxy = poly.total_bounds
pad = 70
EXT = (minx - pad, maxx + pad, miny - pad * 0.9, maxy + pad * 0.9)

def draw_base(ax, labels=True):
    ax.set_facecolor("#f3f1ed")
    b = base
    b[b.kind == "campus"].plot(ax=ax, color="#e3e6da", lw=0, zorder=1)
    b[b.kind == "green"].plot(ax=ax, color="#d3dcc4", lw=0, zorder=2)
    b[b.kind == "building"].plot(ax=ax, color="#dcd7cf", ec="#cbc5bb", lw=0.3, zorder=3)
    roads = b[b.kind.str.startswith("road:")].copy(); roads["hw"] = roads.kind.str[5:]
    roads[roads.hw.isin(MINOR)].plot(ax=ax, color="white", lw=2.2, zorder=4)
    for lw, col, z in [(9.5, "#b9b3aa", 5), (8, "white", 6)]:
        roads[roads.hw.isin(MAJOR) & (roads.bridge == "")].plot(ax=ax, color=col, lw=lw, zorder=z, capstyle="round")
    elev = roads[roads.hw.isin(MAJOR) & (roads.bridge != "")]
    elev.plot(ax=ax, color="#8f877c", lw=5.5, zorder=7, alpha=0.55)
    bx, by = poly.geometry.iloc[0].exterior.xy; ax.plot(bx, by, color="#151412", lw=1, ls=(0, (4, 3)), zorder=8)
    if labels:
        done = set()
        mj = roads[roads.hw.isin(MAJOR)].copy(); mj["L"] = mj.geometry.length
        for _, rr in mj.sort_values("L", ascending=False).iterrows():
            nm = rr["name"]
            if not nm or nm in done or "匝道" in nm or rr.geometry.length < 60: continue
            seg = rr.geometry.intersection(Polygon([(EXT[0]+30, EXT[2]+30), (EXT[1]-30, EXT[2]+30), (EXT[1]-30, EXT[3]-30), (EXT[0]+30, EXT[3]-30)]))
            if seg.is_empty or seg.length < 60: continue
            if seg.geom_type != "LineString": seg = max(seg.geoms, key=lambda g: g.length)
            p = seg.interpolate(0.5, normalized=True); q = seg.interpolate(min(seg.length, seg.project(p) + 10))
            ang = np.degrees(np.arctan2(q.y - p.y, q.x - p.x))
            if ang > 90: ang -= 180
            if ang < -90: ang += 180
            label = nm + ("（高架）" if rr["bridge"] else "")
            ax.text(p.x, p.y, label, rotation=ang, ha="center", va="center", fontsize=8.5, color="#3b3731", zorder=9,
                    rotation_mode="anchor", bbox=dict(fc="white", ec="none", pad=0.6, alpha=0.85))
            done.add(nm)
    ax.set_xlim(EXT[0], EXT[1]); ax.set_ylim(EXT[2], EXT[3]); ax.set_aspect("equal"); ax.set_xticks([]); ax.set_yticks([])
    ax.set_xlabel(""); ax.set_ylabel("")
    for s in ax.spines.values(): s.set_color("#c9c4bc")

def furniture(ax, big=True):
    x0, y0 = EXT[0] + 130, EXT[2] + 25
    ax.plot([x0 - 100, x0], [y0, y0], color="#151412", lw=2, zorder=20, solid_capstyle="butt")
    ax.text(x0 - 50, y0 + 8, "100 m", ha="center", fontsize=8 if big else 7, zorder=20)
    ax.annotate("N", xy=(EXT[1] - 25, EXT[3] - 20), xytext=(EXT[1] - 25, EXT[3] - 60), ha="center", fontsize=9,
                arrowprops=dict(arrowstyle="-|>", color="#151412", lw=1.2), zorder=20)

def pts(ax, sub, scale=1.0):
    for c in ["C2", "C1", "B", "A"]:
        s = sub[sub.cls == c]
        st = STYLE[c]
        ax.scatter(s.px, s.py, s=(14 + 10 * s["受傷"].clip(upper=4)) * scale, fc=st["fc"], ec=st["ec"],
                   lw=1.3 if c in "AB" else 0.5, zorder=12 if c in "AB" else 11, alpha=0.95)

# ---- 圖1：全部事故依分類 ----
fig, ax = plt.subplots(figsize=(11, 6.4), dpi=220)
draw_base(ax); pts(ax, acc); furniture(ax)
handles = [Line2D([], [], marker="o", ls="", ms=8, mfc=STYLE[c]["fc"], mec=STYLE[c]["ec"], mew=1.3,
                  label=f'{STYLE[c]["label"]}（{(acc.cls == c).sum()}件）') for c in ["A", "B", "C1", "C2"]]
handles += [Line2D([], [], color="#151412", ls=(0, (4, 3)), lw=1, label="分析範圍"),
            Line2D([], [], color="#8f877c", lw=5, alpha=0.55, label="高架道路")]
fig.legend(handles=handles, loc="lower left", ncol=3, fontsize=8, frameon=False, bbox_to_anchor=(0.01, 0.035))
fig.text(0.012, 0.008, "底圖 © OpenStreetMap contributors；事故：臺北市政府警察局（110至113年）、內政部警政署（114年）A1A2事故。圓點大小代表受傷人數，同一座標的事故略為散開。",
        fontsize=6.5, color="#5f5a53")
fig.tight_layout(pad=0.3, rect=(0, 0.11, 1, 1)); fig.savefig(f"{OUT}/fig_accident_class.png"); plt.close(fig)

# ---- 圖2：依碰撞型態分面 ----
TG = lambda t: "人車事故" if t.startswith("人車") else "車輛本身" if t.startswith("車輛本身") else "對撞、對向擦撞" if t in ("對撞", "對向擦撞") else t
acc["tg"] = acc["類型"].map(TG)
panels = ["追撞", "同向擦撞", "側撞", "車與車其他", "人車事故", "其他型態"]
acc["panel"] = acc["tg"].where(acc["tg"].isin(panels[:-1]), "其他型態")
fig, axs = plt.subplots(3, 2, figsize=(11, 8.4), dpi=220)
for ax, p in zip(axs.flat, panels):
    sub = acc[acc.panel == p]
    draw_base(ax, labels=False); pts(ax, sub, 0.75)
    nA, nB = (sub.cls == "A").sum(), (sub.cls == "B").sum()
    extra = "（交岔撞、對撞、倒車撞等）" if p == "其他型態" else ""
    ax.set_title(f"{p}{extra}　{len(sub)}件，其中A {nA}件、B {nB}件", fontsize=9.5, loc="left", pad=4)
furniture(axs.flat[-1], big=False)
fig.legend(handles=handles[:4], loc="lower center", ncol=4, fontsize=8, frameon=False, bbox_to_anchor=(0.5, -0.005))
fig.tight_layout(pad=0.4, rect=(0, 0.03, 1, 1)); fig.savefig(f"{OUT}/fig_accident_types.png"); plt.close(fig)
print("ok", len(base), base.kind.value_counts().head(8).to_dict())
