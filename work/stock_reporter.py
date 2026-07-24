#!/usr/bin/env python3
"""Stock picker - daily morning report"""

import json
import smtplib
import os
import sys
import math
import urllib.request
from email.mime.text import MIMEText
from email.header import Header
from datetime import datetime

SMTP_HOST = os.environ.get("SMTP_HOST", "smtp.qq.com")
SMTP_PORT = int(os.environ.get("SMTP_PORT", "465"))
SMTP_USER = os.environ.get("SMTP_USER", "3306450835@qq.com")
SMTP_PASS = os.environ.get("SMTP_PASS")
MAIL_TO = os.environ.get("MAIL_TO", "3306450835@qq.com")

WATCH_LIST = [
    "sh600396","sh600011","sh600023","sh600027","sh600886","sh600795","sh601985","sh600900",
    "sh600036","sh600016","sh600030","sh601211","sh601318","sh601628","sh601398","sh601939",
    "sh600703","sh600745","sh603986","sh600460","sh600584","sh600171","sh688981","sh688012",
    "sh600438","sh601012","sh600089","sh600150","sh601615","sh600031",
    "sh600519","sh600809","sh600887","sh600690","sh600276","sh600196","sh600085","sh600763",
    "sh600418","sh600104","sh600585","sh600019","sh600010","sh600050","sh600941","sh601728",
    "sz000001","sz000002","sz000333","sz000651","sz000725","sz000858","sz000568","sz000625",
    "sz000063","sz000100","sz000301","sz000338","sz000596","sz000547","sz000768","sz000661",
    "sz002415","sz002594","sz002475","sz002714","sz002920","sz002230","sz002352","sz002236",
    "sz002460","sz002709","sz002812","sz002821","sz002850","sz300750","sz300059","sz300760",
    "sz300124","sz300274","sz300347","sz300413","sz300433","sz300450","sz300502","sz300661",
    "sz300676","sz300699","sz300750","sz300751","sz300760","sz300896","sz300900","sz300919",
    "sz300999",
]

SECTOR_MAP = {
    "sh600396":"电力","sh600011":"电力","sh600023":"电力","sh600027":"电力",
    "sh600886":"电力","sh600795":"电力","sh601985":"电力","sh600900":"电力",
    "sh600036":"银行","sh600016":"银行","sh601398":"银行","sh601939":"银行",
    "sh600030":"券商","sh601211":"券商","sh601318":"保险","sh601628":"保险",
    "sh600703":"半导体","sh600745":"半导体","sh603986":"半导体","sh600460":"半导体",
    "sh600584":"半导体","sh600171":"半导体","sh688981":"半导体","sh688012":"半导体",
    "sh600438":"光伏","sh601012":"光伏","sh600089":"电力设备","sh600150":"船舶","sh601615":"风电","sh600031":"机械",
    "sh600519":"白酒","sh600809":"白酒","sh600887":"食品","sh600690":"家电",
    "sh600276":"医药","sh600196":"医药","sh600085":"中药","sh600763":"医药",
    "sh600418":"汽车","sh600104":"汽车","sh600585":"建材","sh600019":"钢铁","sh600010":"钢铁",
    "sh600050":"通信","sh600941":"通信","sh601728":"通信",
    "sz000001":"银行","sz000002":"地产","sz000333":"家电","sz000651":"电器",
    "sz000725":"消费电子","sz000858":"白酒","sz000568":"白酒","sz000625":"汽车",
    "sz000063":"通信","sz000100":"面板","sz000301":"化纤","sz000338":"机械",
    "sz000596":"白酒","sz000547":"军工","sz000768":"军工","sz000661":"医药",
    "sz002415":"安防","sz002594":"新能源车","sz002475":"消费电子","sz002714":"养殖",
    "sz002920":"军工","sz002230":"AI","sz002352":"快递","sz002236":"安防",
    "sz002460":"锂矿","sz002709":"锂电","sz002812":"锂电","sz002821":"农业","sz002850":"锂电",
    "sz300750":"锂电","sz300059":"券商","sz300760":"医药","sz300124":"机械",
    "sz300274":"光伏","sz300347":"医药","sz300413":"VR","sz300433":"面板",
    "sz300450":"医药","sz300502":"通信","sz300661":"材料","sz300676":"芯片",
    "sz300699":"军工","sz300751":"医药","sz300896":"电商","sz300900":"航运","sz300919":"芯片",
    "sz300999":"食品",
}


def fetch_quotes(codes):
    url = "http://hq.sinajs.cn/list=" + ",".join(codes)
    req = urllib.request.Request(url, headers={"Referer": "https://finance.sina.com.cn"})
    try:
        resp = urllib.request.urlopen(req, timeout=15)
        raw = resp.read().decode("gbk")
    except Exception:
        return []
    results = []
    for line in raw.strip().split("\n"):
        if not line.strip(): continue
        try:
            parts = line.split("=")[1].strip().strip('"').split(",")
            code = line.split("_")[-1].split("=")[0]
            name = parts[0]
            if not name: continue
            current = float(parts[3]) if parts[3] else 0
            prev_close = float(parts[2]) if parts[2] else 0
            high = float(parts[4]) if parts[4] else 0
            low = float(parts[5]) if parts[5] else 0
            open_p = float(parts[1]) if parts[1] else 0
            vol = int(parts[8]) if parts[8] else 0
            amount = float(parts[9]) if parts[9] else 0
            if prev_close == 0: continue
            chg_pct = round((current - prev_close) / prev_close * 100, 2)
            amplitude = round((high - low) / prev_close * 100, 2) if prev_close else 0
            sector = SECTOR_MAP.get(code, "其他")
            results.append({"code":code,"name":name,"current":current,"prev_close":prev_close,
                "chg_pct":chg_pct,"amplitude":amplitude,"volume":vol,"amount":amount,
                "high":high,"low":low,"open":open_p,"sector":sector})
        except: continue
    return results


def fetch_kline(code):
    url = f"https://money.finance.sina.com.cn/quotes_service/api/json_v2.php/CN_MarketData.getKLineData?symbol={code}&scale=240&ma=no&datalen=30"
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0", "Referer": "https://finance.sina.com.cn/"})
    try:
        resp = urllib.request.urlopen(req, timeout=10)
        return json.loads(resp.read().decode("gbk"))
    except: return []


def calc_sma(values, period):
    r = []
    for i in range(len(values)):
        if i < period-1: r.append(None)
        else: r.append(sum(values[i-period+1:i+1])/period)
    return r


def calc_rsi(values, period=14):
    if len(values) < period+1: return [None]*len(values)
    r = [None]*period; gains, losses = 0, 0
    for i in range(1, period+1):
        d = values[i]-values[i-1]
        if d > 0: gains += d
        else: losses -= d
    ag, al = gains/period, losses/period
    rs = ag/al if al!=0 else float("inf")
    r.append(100-100/(1+rs))
    for i in range(period+1, len(values)):
        d = values[i]-values[i-1]; gain=d if d>0 else 0; loss=-d if d<0 else 0
        ag = (ag*(period-1)+gain)/period; al = (al*(period-1)+loss)/period
        rs = ag/al if al!=0 else float("inf"); r.append(100-100/(1+rs))
    return r


def calc_macd(values):
    def ema(d,p):
        m=2.0/(p+1); r=[]; e=None
        for v in d:
            if e is None: e=v; else: e=(v-e)*m+e; r.append(e)
        return r
    e12=ema(values,12); e26=ema(values,26)
    dif=[a-b for a,b in zip(e12,e26)]; dea=ema(dif,9)
    macd=[d-s for d,s in zip(dif,dea)]; return dif,dea,macd


def score_stock(stock):
    klines = fetch_kline(stock["code"])
    if len(klines) < 15: return 0, "数据不足"
    closes = [float(k.get("close",0)) for k in klines]
    if not closes or closes[-1]==0: return 0, "数据异常"
    scores=[]; reasons=[]
    yest = stock["chg_pct"]
    if -1<=yest<=5: scores.append(2); reasons.append("涨跌幅适中")
    elif yest>5 and yest<9.8: scores.append(1); reasons.append("昨日偏强")
    elif yest>=9.8: scores.append(0); reasons.append("已涨停⚠️")
    if len(klines)>=5:
        avg5 = sum(int(k.get("volume",0)) for k in klines[-5:])/5
        if avg5>0:
            vr=stock["volume"]/avg5
            if 1.0<=vr<=3.0: scores.append(2); reasons.append("量能适中(健康)")
            elif vr>3.0: scores.append(1); reasons.append("放量明显")
            else: scores.append(-1); reasons.append("缩量⚠️")
    sma5=calc_sma(closes,5); sma20=calc_sma(closes,20)
    if sma5 and sma5[-1] and sma20 and sma20[-1]:
        if sma5[-1]>sma20[-1]: scores.append(2); reasons.append("多头趋势(MA5>MA20)")
        else: scores.append(-1); reasons.append("空头趋势")
    if sma5 and sma5[-1] and sma5[-1]>0:
        dev=(stock["current"]-sma5[-1])/sma5[-1]*100
        if -2<=dev<=3: scores.append(2); reasons.append("贴近MA5(技术买点)")
        elif dev>8: scores.append(-2); reasons.append("偏离MA5过大⚠️")
        else: scores.append(0)
    amp=stock["amplitude"]
    if 1<=amp<=5: scores.append(1); reasons.append("振幅适中")
    elif amp>8: scores.append(-1); reasons.append("波动过大⚠️")
    rsi_vals=calc_rsi(closes)
    if rsi_vals and rsi_vals[-1] is not None:
        rv=rsi_vals[-1]
        if 30<=rv<=60: scores.append(2); reasons.append(f"RSI适中有空间({rv:.0f})")
        elif 60<rv<=75: scores.append(1); reasons.append(f"RSI偏强({rv:.0f})")
        elif rv>75: scores.append(-2); reasons.append(f"RSI超买({rv:.0f})⚠️")
        elif rv<30: scores.append(0); reasons.append(f"RSI超卖({rv:.0f})")
    dif,dea,macd=calc_macd(closes)
    if macd and len(macd)>=2:
        if macd[-1]>0 and macd[-1]>macd[-2]: scores.append(2); reasons.append("MACD金叉红柱放大(强势)")
        elif macd[-1]>0 and macd[-1]<=macd[-2]: scores.append(0); reasons.append("MACD红柱走平")
        elif macd[-1]>macd[-2]: scores.append(1); reasons.append("MACD绿柱缩短(拐点)")
        else: scores.append(-2); reasons.append("MACD死叉⚠️")
    return sum(scores), " | ".join(reasons[:5])


def format_report(stocks):
    today = datetime.now().strftime("%Y-%m-%d")
    rows = ""
    for i,s in enumerate(stocks,1):
        clr = "#e74c3c" if s["chg_pct"]>=0 else "#27ae60"
        rows += f"<tr><td style='padding:10px;text-align:center;font-weight:bold'>{i}</td>" \
                f"<td style='padding:10px;font-weight:bold'>{s['name']}</td>" \
                f"<td style='padding:10px;color:#666'>{s['code']}</td>" \
                f"<td style='padding:10px'>{s['sector']}</td>" \
                f"<td style='padding:10px;text-align:right;font-weight:bold'>{s['current']:.2f}</td>" \
                f"<td style='padding:10px;text-align:right;{clr};font-weight:bold'>{s['chg_pct']:+.2f}%</td>" \
                f"<td style='padding:10px;font-size:13px;color:#555'>{s.get('reason','')}</td></tr>"
    return f"""<html><head><meta charset="utf-8">
<style>body{{font-family:'Microsoft YaHei',sans-serif;background:#f5f6fa;padding:20px}}
.container{{max-width:700px;margin:0 auto;background:#fff;border-radius:12px;padding:30px}}
h1{{font-size:22px;color:#2c3e50}}th{{background:#3498db;color:#fff;padding:12px}}
tr:nth-child(even){{background:#f8f9fa}}.footer{{margin-top:20px;font-size:12px;color:#bdc3c7;text-align:center}}
</style></head><body><div class="container">
<h1>{today} 早盘选股参考</h1>
<p style="color:#95a5a6">全市场筛选 · 基于技术指标 · 仅供参考</p>
<table width="100%" cellspacing="0"><tr><th>#</th><th>股票</th><th>代码</th><th>行业</th><th>收盘价</th><th>涨跌幅</th><th>逻辑</th></tr>
{rows}</table>
<div class="footer">AI自动生成，不构成投资建议<br>股市有风险，投资需谨慎</div>
</div></body></html>"""


def send_email(subject, html):
    if not SMTP_PASS: print("ERROR: SMTP_PASS not set"); return False
    msg = MIMEText(html, "html", "utf-8")
    msg["Subject"] = Header(subject, "utf-8")
    msg["From"] = SMTP_USER; msg["To"] = MAIL_TO
    try:
        s = smtplib.SMTP_SSL(SMTP_HOST, SMTP_PORT, timeout=30)
        s.login(SMTP_USER, SMTP_PASS); s.sendmail(SMTP_USER, [MAIL_TO], msg.as_string()); s.quit()
        return True
    except: return False


def main():
    print("Fetching stocks...")
    quotes = fetch_quotes(WATCH_LIST)
    print(f"Got {len(quotes)} quotes")
    if not quotes: sys.exit(1)
    scored = []
    for q in quotes:
        score, reason = score_stock(q); q["score"]=score; q["reason"]=reason; scored.append(q)
    scored.sort(key=lambda x:x["score"], reverse=True)
    picks=[]; sec_cnt={}
    for p in scored[:8]:
        s=p.get("sector","其他")
        if sec_cnt.get(s,0)<2: picks.append(p); sec_cnt[s]=sec_cnt.get(s,0)+1
    picks=picks[:6]
    for i,p in enumerate(picks,1):
        print(f"  {i}. {p['name']}({p['code']}) {p['current']:.2f} {p['chg_pct']:+.2f}% | Score:{p['score']}")
    html=format_report(picks)
    if send_email(f"股票早报 {datetime.now().strftime('%Y-%m-%d')}", html):
        print("Email sent!")
    else:
        print("Failed to send"); sys.exit(1)

if __name__=="__main__":
    main()
