"""GitHub Actions 专用版报告渲染器：读取 docs/data/latest.json（含 trend），输出 docs/data/report.html。"""
import argparse
import html as html_mod
import json
import sys
import traceback
from datetime import datetime
from pathlib import Path
from string import Template

PLATFORM_NAMES  = {"fliggy":"飞猪","tuniu":"途牛","ctrip":"携程","qunar":"去哪儿","tongcheng":"同程"}
PLATFORM_COLORS = {"fliggy":"#FF6B00","tuniu":"#00A651","ctrip":"#0086F6","qunar":"#FF4500","tongcheng":"#7C3AED"}


CITY_NAMES = {
    "BJS": "北京", "SHA": "上海", "CAN": "广州", "SZX": "深圳", "CTU": "成都",
    "CKG": "重庆", "HGH": "杭州", "SIA": "西安", "KMG": "昆明", "LZO": "泸州",
    "DZH": "达州", "XMN": "厦门", "WUH": "武汉", "NKG": "南京", "KWE": "贵阳",
    "SYX": "三亚", "TAO": "青岛", "CSX": "长沙", "TSN": "天津", "HAK": "海口",
    "URC": "乌鲁木齐", "LHW": "兰州", "TNA": "济南", "HRB": "哈尔滨", "SHE": "沈阳",
    "DLC": "大连", "NNG": "南宁", "FOC": "福州", "KWL": "桂林", "LJG": "丽江",
}

def city(code):
    return CITY_NAMES.get(code, code)

def route_label(from_code, to_code):
    return f"{city(from_code)}→{city(to_code)}"

CSS = """
*,*::before,*::after{box-sizing:border-box;margin:0;padding:0}
:root{--bg:#f0f2f7;--card:#fff;--border:#e8eaef;--text:#1a1d29;--sub:#6b7280;
  --accent:#2563eb;--red:#dc2626;--orange:#d97706;--radius:16px;--shadow:0 2px 12px rgba(0,0,0,.07)}
body{font-family:-apple-system,"PingFang SC","Helvetica Neue",sans-serif;background:var(--bg);color:var(--text)}
.page{max-width:980px;margin:0 auto;padding:28px 16px 60px}
.hero{background:linear-gradient(135deg,#1e3a8a 0%,#2563eb 60%,#60a5fa 100%);
  border-radius:var(--radius);padding:32px 36px;margin-bottom:20px;position:relative;overflow:hidden}
.hero::after{content:'✈';position:absolute;right:28px;top:50%;transform:translateY(-50%);
  font-size:72px;opacity:.12;pointer-events:none}
.hero h1{color:#fff;font-size:22px;font-weight:700;margin-bottom:6px}
.hero .sub{color:rgba(255,255,255,.75);font-size:13px}
.card{background:var(--card);border-radius:var(--radius);padding:22px 24px;
  margin-bottom:18px;box-shadow:var(--shadow)}
.card-title{font-size:14px;font-weight:600;color:var(--sub);text-transform:uppercase;
  letter-spacing:.05em;margin-bottom:16px;display:flex;align-items:center;gap:8px}
.card-title::before{content:'';display:inline-block;width:3px;height:15px;
  background:var(--accent);border-radius:2px}
.table-wrap{overflow-x:auto;border-radius:8px}
table{width:100%;border-collapse:collapse;font-size:14px;min-width:520px}
th{padding:10px 8px;text-align:center;background:#f8f9fc;color:var(--sub);
  font-weight:500;font-size:12px;border-bottom:2px solid var(--border)}
th:first-child{text-align:left}
td{padding:12px 8px;text-align:center;border-bottom:1px solid #f3f4f8;vertical-align:middle}
td:first-child{text-align:left}
tr:last-child td{border-bottom:none}
.na{color:#ccc}.best{color:var(--red);font-weight:800;font-size:16px}
.tag-d{display:inline-block;padding:2px 7px;border-radius:5px;font-size:11px;
  font-weight:600;background:#dbeafe;color:#1d4ed8}
.tag-r{display:inline-block;padding:2px 7px;border-radius:5px;font-size:11px;
  font-weight:600;background:#d1fae5;color:#065f46}
.badge{display:inline-block;padding:2px 7px;border-radius:4px;font-size:10px;font-weight:600;color:#fff;margin-top:3px}
.dot{display:inline-block;width:8px;height:8px;border-radius:50%;margin-right:4px;vertical-align:middle}
.time{font-size:12px;color:var(--sub);line-height:1.6}
.total{background:linear-gradient(90deg,#fff7ed,#fef3c7);border:1.5px solid #fde68a;
  border-radius:10px;padding:14px 18px;margin-top:14px;display:flex;align-items:center;flex-wrap:wrap;gap:12px}
.total-lbl{font-size:13px;color:var(--orange)}
.total-p{font-size:26px;font-weight:800;color:var(--red)}
.total-sub{font-size:12px;color:var(--sub)}
.trend-tabs{display:flex;gap:8px;flex-wrap:wrap;margin-bottom:12px}
.ttab{padding:6px 13px;border-radius:7px;font-size:13px;font-weight:500;cursor:pointer;
  border:1.5px solid var(--border);background:#f8f9fc;color:var(--sub);transition:all .15s}
.ttab.active{background:var(--accent);color:#fff;border-color:var(--accent)}
.legend{display:flex;gap:14px;flex-wrap:wrap;font-size:12px;color:var(--sub);margin-bottom:10px}
.legend-item{display:flex;align-items:center;gap:5px}
.lline{width:20px;height:3px;border-radius:2px;display:inline-block}
canvas{width:100%;border-radius:8px;background:#fafbff;display:block}
.nodata{text-align:center;padding:40px;color:var(--sub);font-size:13px}
.footer{text-align:center;color:#b0b7c3;font-size:12px;padding:20px 0 0}
.hero-routes{color:#fff;font-size:14px;font-weight:500;margin-bottom:6px;opacity:.92}
td.route{text-align:left;font-weight:600;font-size:13px;color:var(--text);white-space:nowrap}
td.route .rt{display:inline-block;padding:3px 9px;border-radius:6px;background:#eef2ff;color:#3730a3;font-size:12px}
.route-sep{border-top:2px solid var(--border)}
.bestgrid{display:flex;gap:12px;flex-wrap:wrap;margin-bottom:18px}
.bestcard{flex:1 1 180px;border:1.5px solid var(--border);border-radius:12px;padding:14px 16px;background:#fafbff}
.bc-route{font-size:13px;color:var(--sub);font-weight:600;margin-bottom:4px}
.bc-price{font-size:24px;font-weight:800;color:var(--red);line-height:1.2}
.bc-sub{font-size:12px;color:var(--sub);margin-top:4px}

"""

JS_TPL = r"""
const TD=$TREND_DATA;const CM=$COLOR_MAP;const NM=$NAME_MAP;
var allDates=Object.keys(TD).sort(),idx=0;
var cv=document.getElementById('cv'),nd=document.getElementById('nd'),ctx=cv?cv.getContext('2d'):null;
function tabs(){var el=document.getElementById('tabs');if(!el)return;el.innerHTML='';
  allDates.forEach(function(d,i){var b=document.createElement('button');
    b.className='ttab'+(i===idx?' active':'');b.textContent=d;
    b.onclick=function(){idx=i;tabs();draw(d)};el.appendChild(b)})}
function draw(date){if(!ctx)return;var dd=TD[date]||{};
  var ps=Object.keys(dd).filter(function(p){return dd[p]&&dd[p].length>0});
  if(!ps.length){cv.style.display='none';nd.style.display='block';legend([]);return}
  cv.style.display='block';nd.style.display='none';
  var DPR=window.devicePixelRatio||1,W=cv.parentElement.offsetWidth||760,H=250;
  cv.width=W*DPR;cv.height=H*DPR;cv.style.width=W+'px';cv.style.height=H+'px';
  ctx.setTransform(DPR,0,0,DPR,0,0);ctx.clearRect(0,0,W,H);
  var PL=66,PR=20,PT=22,PB=50,pw=W-PL-PR,ph=H-PT-PB;
  var allTs=[],allV=[];ps.forEach(function(p){(dd[p]||[]).forEach(function(pt){allTs.push(pt.t);allV.push(pt.v)})});
  var tsU=allTs.filter(function(v,i,a){return a.indexOf(v)===i}).sort();
  var mn=Math.min.apply(null,allV),mx=Math.max.apply(null,allV),sp=mx-mn||1;
  var t0=new Date(tsU[0]).getTime(),tN=new Date(tsU[tsU.length-1]).getTime(),tSp=tN-t0||1;
  function tx(ts){return PL+pw*(new Date(ts).getTime()-t0)/tSp}
  function ty(v){return PT+ph*(1-(v-mn)/sp)}
  ctx.strokeStyle='#eef0f5';ctx.lineWidth=1;
  for(var g=0;g<=4;g++){var gy=PT+ph*(g/4);ctx.beginPath();ctx.moveTo(PL,gy);ctx.lineTo(W-PR,gy);ctx.stroke();
    ctx.fillStyle='#9ca3af';ctx.font='11px system-ui';ctx.textAlign='right';
    ctx.fillText('¥'+(mx-sp*(g/4)).toFixed(0),PL-8,gy+4)}
  ctx.fillStyle='#9ca3af';ctx.textAlign='center';ctx.font='10px system-ui';
  var sl=Math.max(1,Math.floor(tsU.length/7));
  tsU.forEach(function(ts,i){if(i%sl!==0&&i!==tsU.length-1)return;ctx.fillText(ts.slice(5,16),tx(ts),H-8)});
  ps.forEach(function(p){var pts=dd[p];if(!pts||!pts.length)return;var c=CM[p]||'#888';
    ctx.strokeStyle=c;ctx.lineWidth=2.5;ctx.lineJoin='round';ctx.lineCap='round';ctx.beginPath();
    pts.forEach(function(pt,i){var x=tx(pt.t),y=ty(pt.v);i?ctx.lineTo(x,y):ctx.moveTo(x,y)});ctx.stroke();
    pts.forEach(function(pt){ctx.beginPath();ctx.arc(tx(pt.t),ty(pt.v),4,0,Math.PI*2);
      ctx.fillStyle=c;ctx.fill();ctx.beginPath();ctx.arc(tx(pt.t),ty(pt.v),2,0,Math.PI*2);
      ctx.fillStyle='#fff';ctx.fill()});
    var last=pts[pts.length-1];ctx.fillStyle=c;ctx.font='bold 12px system-ui';
    ctx.textAlign='left';ctx.fillText('¥'+last.v.toFixed(0),tx(last.t)+8,ty(last.v)-6)});
  legend(ps)}
function legend(ps){var el=document.getElementById('lg');if(!el)return;
  el.innerHTML=ps.map(function(p){return'<div class="legend-item"><span class="lline" style="background:'+(CM[p]||'#888')+'"></span><span>'+(NM[p]||p)+'</span></div>'}).join('')}
if(allDates.length){tabs();draw(allDates[0])}else{if(nd)nd.style.display='block';if(cv)cv.style.display='none'}
window.addEventListener('resize',function(){if(allDates.length)draw(allDates[idx])});
"""


def e(s):
    return html_mod.escape(str(s))


def render(q, summary, trend):
    platforms = q["platforms"]
    platform_desc = "、".join(PLATFORM_NAMES.get(p, p) for p in platforms)

    # 本次涉及的所有航线（按出现顺序去重）
    routes = []
    for s in summary:
        rk = (s["from"], s["to"])
        if rk not in routes:
            routes.append(rk)
    multi = len(routes) > 1

    # 标题
    if multi:
        title_main = "多航线机票比价"
        title_sub_routes = " · ".join(route_label(f, t) for f, t in routes)
        head_title = "机票比价 · " + " / ".join(route_label(f, t) for f, t in routes)
    else:
        f0, t0 = routes[0] if routes else (q["from"]["code"], q["to"]["code"])
        title_main = f"{city(f0)}（{f0}） ⇄ {city(t0)}（{t0}）"
        title_sub_routes = ""
        head_title = f"机票比价 · {city(f0)}⇄{city(t0)}"

    # 列头
    def th(p):
        c = PLATFORM_COLORS.get(p, "#888")
        n = PLATFORM_NAMES.get(p, p)
        return f"<th><span class='dot' style='background:{c}'></span>{e(n)}</th>"
    ths = "".join(th(p) for p in platforms)
    route_th = "<th>航线</th>" if multi else ""

    # 每条航线内部按日期排序；航线之间按首次出现顺序
    ordered = sorted(summary, key=lambda s: (routes.index((s["from"], s["to"])), s["date"]))

    # 反向航线（A→B 与 B→A 同时存在）才算回程
    reverse_exists = {(f, t) for f, t in routes if (t, f) in routes}

    rows_html = []
    prev_route = None
    for s in ordered:
        rk = (s["from"], s["to"])
        # 只有存在反向航线时才区分去程/回程，否则一律算去程
        is_r = rk in reverse_exists and (s["to"], s["from"]) == routes[0]
        cells = ""
        for p in platforms:
            pr = s["per_platform"].get(p)
            if pr is None:
                cells += "<td class='na'>—</td>"
            elif pr == s["min_price"]:
                cells += f"<td class='best'>¥{pr:.0f}</td>"
            else:
                cells += f"<td>¥{pr:.0f}</td>"
        bc = PLATFORM_COLORS.get(s["best_platform"], "#888")
        bn = PLATFORM_NAMES.get(s["best_platform"], s["best_platform"])
        sep = " route-sep" if (multi and prev_route is not None and rk != prev_route) else ""
        route_td = (
            f"<td class='route{sep}'><span class='rt'>{e(route_label(*rk))}</span></td>"
            if multi else ""
        )
        rows_html.append(
            f"<tr>"
            f"{route_td}"
            f"<td class='{sep.strip()}'><span class='{'tag-r' if is_r else 'tag-d'}'>"
            f"{'回程' if is_r else '去程'}</span> {e(s['date'])}</td>"
            f"{cells}"
            f"<td class='best'>¥{s['min_price']:.0f}</td>"
            f"<td>{e(s['best_flight'])}<br><span class='badge' style='background:{bc}'>{e(bn)}</span></td>"
            f"<td class='time'>{e(s['best_depart_time'])}<br>→ {e(s['best_arrive_time'])}</td>"
            f"</tr>"
        )
        prev_route = rk

    # 每条航线的最低价小结
    best_html = ""
    if summary:
        items = []
        for f, t in routes:
            rs = [s for s in summary if (s["from"], s["to"]) == (f, t)]
            b = min(rs, key=lambda s: s["min_price"])
            items.append(
                f"<div class='bestcard'>"
                f"<div class='bc-route'>{e(route_label(f, t))}</div>"
                f"<div class='bc-price'>¥{b['min_price']:.0f}</div>"
                f"<div class='bc-sub'>{e(b['date'])} · {e(b['best_flight'])} · "
                f"{e(PLATFORM_NAMES.get(b['best_platform'], b['best_platform']))}</div>"
                f"</div>"
            )
        best_html = "<div class='bestgrid'>" + "".join(items) + "</div>"

    # 往返合计：仅当确实存在反向航线时
    total_html = ""
    done = set()
    for f, t in routes:
        if (t, f) in routes and (t, f) not in done:
            done.add((f, t))
            ob = [s for s in summary if (s["from"], s["to"]) == (f, t)]
            ib = [s for s in summary if (s["from"], s["to"]) == (t, f)]
            if ob and ib:
                bo = min(ob, key=lambda s: s["min_price"])
                bi = min(ib, key=lambda s: s["min_price"])
                tot = bo["min_price"] + bi["min_price"]
                total_html += (
                    f"<div class='total'>"
                    f"<span class='total-lbl'>{e(route_label(f, t))} 往返合计最低</span>"
                    f"<span class='total-p'>¥{tot:.0f}</span>"
                    f"<span class='total-sub'>去程 {e(bo['date'])} ¥{bo['min_price']:.0f} "
                    f"＋ 回程 {e(bi['date'])} ¥{bi['min_price']:.0f}</span>"
                    f"</div>"
                )

    # 走势：按「航线+日期」取桶，tab 标签带航线名
    trend_filtered = {}
    for s in ordered:
        key = f"{s['from']}-{s['to']}|{s['date']}"
        label = f"{route_label(s['from'], s['to'])} {s['date'][5:]}" if multi else s["date"]
        trend_filtered[label] = trend.get(key, {})
    all_plat = sorted({p for d in trend_filtered.values() for p in d})
    cm = {p: PLATFORM_COLORS.get(p, "#888") for p in all_plat}
    nm = {p: PLATFORM_NAMES.get(p, p) for p in all_plat}

    js = Template(JS_TPL).substitute(
        TREND_DATA=json.dumps(trend_filtered, ensure_ascii=False),
        COLOR_MAP=json.dumps(cm, ensure_ascii=False),
        NAME_MAP=json.dumps(nm, ensure_ascii=False),
    )

    sub_routes_html = (
        f"<div class='hero-routes'>{e(title_sub_routes)}</div>" if title_sub_routes else ""
    )

    return f"""<!DOCTYPE html>
<html lang="zh">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{e(head_title)}</title>
<style>{CSS}</style>
</head>
<body>
<div class="page">
  <div class="hero">
    <h1>✈️ {e(title_main)}</h1>
    {sub_routes_html}
    <div class="sub">机票多平台价格监控 · {e(q['query_time'])} · 数据仅供参考</div>
  </div>
  <div class="card">
    <div class="card-title">📊 比价结果</div>
    {best_html}
    <div class="table-wrap">
      <table>
        <thead><tr>{route_th}<th>日期</th>{ths}<th>最低价</th><th>最低价航班</th><th>起降时间</th></tr></thead>
        <tbody>{''.join(rows_html)}</tbody>
      </table>
    </div>
    {total_html}
  </div>
  <div class="card">
    <div class="card-title">📈 价格走势（近7天，多平台）</div>
    <div class="trend-tabs" id="tabs"></div>
    <div class="legend" id="lg"></div>
    <canvas id="cv" height="250"></canvas>
    <div class="nodata" id="nd" style="display:none">暂无足够历史数据，随监控积累后将显示</div>
  </div>
  <div class="footer">由 flight-price-monitor 自动生成 · {e(platform_desc)} · 以实际购票页面为准</div>
</div>
<script>{js}</script>
</body>
</html>"""


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--results-file", required=True)
    ap.add_argument("--out-dir", default="docs/data")
    args = ap.parse_args()

    rf = Path(args.results_file).expanduser()
    if not rf.exists():
        print(f"results file {rf} not found, skipping")
        return
    payload = json.loads(rf.read_text(encoding="utf-8"))
    if not payload.get("ok"):
        print("payload not ok, skipping")
        return
    data = payload["data"]
    trend = data.get("trend", {})

    out = Path(args.out_dir) / "report.html"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(render(data["query"], data["summary"], trend), encoding="utf-8")
    print(f"Report → {out}")


if __name__ == "__main__":
    try:
        main()
    except Exception:
        print(traceback.format_exc(), file=sys.stderr)
        sys.exit(1)
