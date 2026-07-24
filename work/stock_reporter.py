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
    "sh600396":"power","sh600011":"power","sh600023":"power","sh600027":"power",
    "sh600886":"power","sh600795":"power","sh601985":"power","sh600900":"power",
    "sh600036":"bank","sh600016":"bank","sh601398":"bank","sh601939":"bank",
    "sh600030":"broker","sh601211":"broker","sh601318":"insurance","sh601628":"insurance",
    "sh600703":"semi","sh600745":"semi","sh603986":"semi","sh600460":"semi",
    "sh600584":"semi","sh600171":"semi","sh688981":"semi","sh688012":"semi",
    "sh600438":"solar","sh601012":"solar","sh600089":"elec_equip","sh600150":"ship","sh601615":"wind","sh600031":"mach",
    "sh600519":"baijiu","sh600809":"baijiu","sh600887":"food","sh600690":"appliance",
    "sh600276":"pharma","sh600196":"pharma","sh600085":"tcm","sh600763":"pharma",
    "sh600418":"auto","sh600104":"auto","sh600585":"material","sh600019":"steel","sh600010":"steel",
    "sh600050":"telecom","sh600941":"telecom","sh601728":"telecom",
    "sz000001":"bank","sz000002":"realestate","sz000333":"appliance","sz000651":"elec",
    "sz000725":"consumer_elec","sz000858":"baijiu","sz000568":"baijiu","sz000625":"auto",
    "sz000063":"telecom","sz000100":"panel","sz000301":"chem","sz000338":"mach",
    "sz000596":"baijiu","sz000547":"defense","sz000768":"defense","sz000661":"pharma",
    "sz002415":"security","sz002594":"nev","sz002475":"consumer_elec","sz002714":"farm",
    "sz002920":"defense","sz002230":"ai","sz002352":"logistics","sz002236":"security",
    "sz002460":"lithium","sz002709":"battery","sz002812":"battery","sz002821":"agriculture","sz002850":"battery",
    "sz300750":"battery","sz300059":"broker","sz300760":"pharma","sz300124":"mach",
    "sz300274":"solar","sz300347":"pharma","sz300413":"vr","sz300433":"panel",
    "sz300450":"pharma","sz300502":"telecom","sz300661":"material","sz300676":"chip",
    "sz300699":"defense","sz300751":"pharma","sz300896":"ecommerce","sz300900":"shipping","sz300919":"chip",
    "sz300999":"food",
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
            parts = line.split("=")[1].strip().strip("\u0022").split(",")
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
            sector = SECTOR_MAP.get(code, "other")
            results.append({"code":code,"name":name,"current":current,"prev_close":prev_close,
                "chg_pct":chg_pct,"amplitude":amplitude,"volume":vol,"amount":amount,
                "high":high,"low":low,"open":open_p,"sector":sector})
        except: continue
    return results


def fetch_kline(code):
    url_base = "https://money.finance.sina.com.cn/quotes_service/api/json_v2.php/CN_MarketData.getKLineData"
    url = url_base + "?symbol=" + code + "&scale=240&ma=no&datalen=30"
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
    r = [None]*period
    gains, losses = 0, 0
    for i in range(1, period+1):
        d = values[i]-values[i-1]
        if d > 0:
            gains += d
        else:
            losses -= d
    ag, al = gains/period, losses/period
    rs = ag/al if al!=0 else float("inf")
    r.append(100-100/(1+rs))
    for i in range(period+1, len(values)):
        d = values[i]-values[i-1]
        gain = d if d>0 else 0
        loss = -d if d<0 else 0
        ag = (ag*(period-1)+gain)/period
        al = (al*(period-1)+loss)/period
        rs = ag/al if al!=0 else float("inf")
        r.append(100-100/(1+rs))
    return r


def calc_macd(values):
    def ema(d, p):
        m = 2.0/(p+1)
        r = []
        e = None
        for v in d:
            if e is None:
                e = v
            else:
                e = (v-e)*m+e
            r.append(e)
        return r
    e12 = ema(values, 12)
    e26 = ema(values, 26)
    dif = [a-b for a,b in zip(e12, e26)]
    dea = ema(dif, 9)
    macd = [d-s for d,s in zip(dif, dea)]
    return dif, dea, macd


def score_stock(stock):
    klines = fetch_kline(stock["code"])
    if len(klines) < 15: return 0, "no data"
    closes = [float(k.get("close",0)) for k in klines]
    if not closes or closes[-1]==0: return 0, "bad data"
    scores = []
    reasons = []
    yest = stock["chg_pct"]
    if -1<=yest<=5:
        scores.append(2)
        reasons.append("moderate change")
    elif yest>5 and yest<9.8:
        scores.append(1)
        reasons.append("yesterday strong")
    elif yest>=9.8:
        scores.append(0)
        reasons.append("limit up")
    if len(klines)>=5:
        total = 0
        for k in klines[-5:]:
            total += int(k.get("volume",0))
        avg5 = total/5
        if avg5>0:
            vr = stock["volume"]/avg5
            if 1.0<=vr<=3.0:
                scores.append(2)
                reasons.append("healthy volume")
            elif vr>3.0:
                scores.append(1)
                reasons.append("increased volume")
            else:
                scores.append(-1)
                reasons.append("low volume")
    sma5 = calc_sma(closes, 5)
    sma20 = calc_sma(closes, 20)
    if sma5 and sma5[-1] and sma20 and sma20[-1]:
        if sma5[-1]>sma20[-1]:
            scores.append(2)
            reasons.append("bullish MA5>MA20")
        else:
            scores.append(-1)
            reasons.append("bearish")
    if sma5 and sma5[-1] and sma5[-1]>0:
        dev = (stock["current"]-sma5[-1])/sma5[-1]*100
        if -2<=dev<=3:
            scores.append(2)
            reasons.append("near MA5")
        elif dev>8:
            scores.append(-2)
            reasons.append("far from MA5")
        else:
            scores.append(0)
    amp = stock["amplitude"]
    if 1<=amp<=5:
        scores.append(1)
        reasons.append("normal range")
    elif amp>8:
        scores.append(-1)
        reasons.append("high volatility")
    rsi_vals = calc_rsi(closes)
    if rsi_vals and rsi_vals[-1] is not None:
        rv = rsi_vals[-1]
        if 30<=rv<=60:
            scores.append(2)
            reasons.append("RSI moderate")
        elif 60<rv<=75:
            scores.append(1)
            reasons.append("RSI strong")
        elif rv>75:
            scores.append(-2)
            reasons.append("RSI overbought")
        elif rv<30:
            scores.append(0)
            reasons.append("RSI oversold")
    dif, dea, macd = calc_macd(closes)
    if macd and len(macd)>=2:
        if macd[-1]>0 and macd[-1]>macd[-2]:
            scores.append(2)
            reasons.append("MACD golden cross")
        elif macd[-1]>0 and macd[-1]<=macd[-2]:
            scores.append(0)
            reasons.append("MACD flat")
        elif macd[-1]>macd[-2]:
            scores.append(1)
            reasons.append("MACD green shortening")
        else:
            scores.append(-2)
            reasons.append("MACD death cross")
    return sum(scores), " | ".join(reasons[:5])


def format_report(stocks):
    from datetime import datetime
    today = datetime.now().strftime("%Y-%m-%d")
    rows = ""
    for i, s in enumerate(stocks, 1):
        clr = "#e74c3c" if s["chg_pct"]>=0 else "#27ae60"
        row = "<tr>"
        row += "<td style='padding:10px;text-align:center;font-weight:bold'>" + str(i) + "</td>"
        row += "<td style='padding:10px;font-weight:bold'>" + s["name"] + "</td>"
        row += "<td style='padding:10px;color:#666'>" + s["code"] + "</td>"
        row += "<td style='padding:10px'>" + s["sector"] + "</td>"
        row += "<td style='padding:10px;text-align:right;font-weight:bold'>" + "{:.2f}".format(s["current"]) + "</td>"
        clr_attr = "style='padding:10px;text-align:right;" + clr + ";font-weight:bold'"
        row += "<td " + clr_attr + ">" + "{:+.2f}%".format(s["chg_pct"]) + "</td>"
        row += "<td style='padding:10px;font-size:13px;color:#555'>" + s.get("reason","") + "</td>"
        row += "</tr>"
        rows += row
    return "<html><head><meta charset='utf-8'><style>body{font-family:sans-serif;background:#f5f6fa;padding:20px}.container{max-width:700px;margin:0 auto;background:#fff;border-radius:12px;padding:30px}h1{font-size:22px;color:#2c3e50}th{background:#3498db;color:#fff;padding:12px}tr:nth-child(even){background:#f8f9fa}.footer{margin-top:20px;font-size:12px;color:#bdc3c7;text-align:center}</style></head><body><div class='container'><h1>" + today + " Morning Stock Picks</h1><p style='color:#95a5a6'>Technical analysis for reference only</p><table width='100%' cellspacing='0'><tr><th>#</th><th>Stock</th><th>Code</th><th>Sector</th><th>Price</th><th>Chg</th><th>Logic</th></tr>" + rows + "</table><div class='footer'>AI generated, not investment advice<br>Invest at your own risk</div></div></body></html>"


def send_email(subject, html):
    if not SMTP_PASS:
        print("ERROR: SMTP_PASS not set")
        return False
    msg = MIMEText(html, "html", "utf-8")
    msg["Subject"] = Header(subject, "utf-8")
    msg["From"] = SMTP_USER
    msg["To"] = MAIL_TO
    try:
        s = smtplib.SMTP_SSL(SMTP_HOST, SMTP_PORT, timeout=30)
        s.login(SMTP_USER, SMTP_PASS)
        s.sendmail(SMTP_USER, [MAIL_TO], msg.as_string())
        s.quit()
        return True
    except:
        return False


def main():
    print("Fetching stocks...")
    quotes = fetch_quotes(WATCH_LIST)
    print("Got " + str(len(quotes)) + " quotes")
    if not quotes:
        sys.exit(1)
    scored = []
    for q in quotes:
        score, reason = score_stock(q)
        q["score"] = score
        q["reason"] = reason
        scored.append(q)
    scored.sort(key=lambda x: x["score"], reverse=True)
    picks = []
    sec_cnt = {}
    for p in scored[:8]:
        s = p.get("sector", "other")
        if sec_cnt.get(s, 0) < 2:
            picks.append(p)
            sec_cnt[s] = sec_cnt.get(s, 0) + 1
    picks = picks[:6]
    for i, p in enumerate(picks, 1):
        print("  " + str(i) + ". " + p["name"] + "(" + p["code"] + ") " + "{:.2f}".format(p["current"]) + " " + "{:+.2f}%".format(p["chg_pct"]) + " | Score:" + str(p["score"]))
    html = format_report(picks)
    subj = "Stock Report " + datetime.now().strftime("%Y-%m-%d")
    if send_email(subj, html):
        print("Email sent!")
    else:
        print("Failed to send")
        sys.exit(1)


if __name__ == "__main__":
    main()