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
    "sh600396":"鐢靛姏","sh600011":"鐢靛姏","sh600023":"鐢靛姏","sh600027":"鐢靛姏",
    "sh600886":"鐢靛姏","sh600795":"鐢靛姏","sh601985":"鐢靛姏","sh600900":"鐢靛姏",
    "sh600036":"閾惰","sh600016":"閾惰","sh601398":"閾惰","sh601939":"閾惰",
    "sh600030":"鍒稿晢","sh601211":"鍒稿晢","sh601318":"淇濋櫓","sh601628":"淇濋櫓",
    "sh600703":"鍗婂浣?,"sh600745":"鍗婂浣?,"sh603986":"鍗婂浣?,"sh600460":"鍗婂浣?,
    "sh600584":"鍗婂浣?,"sh600171":"鍗婂浣?,"sh688981":"鍗婂浣?,"sh688012":"鍗婂浣?,
    "sh600438":"鍏変紡","sh601012":"鍏変紡","sh600089":"鐢靛姏璁惧","sh600150":"鑸硅埗","sh601615":"椋庣數","sh600031":"鏈烘",
    "sh600519":"鐧介厭","sh600809":"鐧介厭","sh600887":"椋熷搧","sh600690":"瀹剁數",
    "sh600276":"鍖昏嵂","sh600196":"鍖昏嵂","sh600085":"涓嵂","sh600763":"鍖昏嵂",
    "sh600418":"姹借溅","sh600104":"姹借溅","sh600585":"寤烘潗","sh600019":"閽㈤搧","sh600010":"閽㈤搧",
    "sh600050":"閫氫俊","sh600941":"閫氫俊","sh601728":"閫氫俊",
    "sz000001":"閾惰","sz000002":"鍦颁骇","sz000333":"瀹剁數","sz000651":"鐢靛櫒",
    "sz000725":"娑堣垂鐢靛瓙","sz000858":"鐧介厭","sz000568":"鐧介厭","sz000625":"姹借溅",
    "sz000063":"閫氫俊","sz000100":"闈㈡澘","sz000301":"鍖栫氦","sz000338":"鏈烘",
    "sz000596":"鐧介厭","sz000547":"鍐涘伐","sz000768":"鍐涘伐","sz000661":"鍖昏嵂",
    "sz002415":"瀹夐槻","sz002594":"鏂拌兘婧愯溅","sz002475":"娑堣垂鐢靛瓙","sz002714":"鍏绘畺",
    "sz002920":"鍐涘伐","sz002230":"AI","sz002352":"蹇€?,"sz002236":"瀹夐槻",
    "sz002460":"閿傜熆","sz002709":"閿傜數","sz002812":"閿傜數","sz002821":"鍐滀笟","sz002850":"閿傜數",
    "sz300750":"閿傜數","sz300059":"鍒稿晢","sz300760":"鍖昏嵂","sz300124":"鏈烘",
    "sz300274":"鍏変紡","sz300347":"鍖昏嵂","sz300413":"VR","sz300433":"闈㈡澘",
    "sz300450":"鍖昏嵂","sz300502":"閫氫俊","sz300661":"鏉愭枡","sz300676":"鑺墖",
    "sz300699":"鍐涘伐","sz300751":"鍖昏嵂","sz300896":"鐢靛晢","sz300900":"鑸繍","sz300919":"鑺墖",
    "sz300999":"椋熷搧",
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
            sector = SECTOR_MAP.get(code, "鍏朵粬")
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
            if e is None: e=v
            else: e=(v-e)*m+e; r.append(e)
        return r
    e12=ema(values,12); e26=ema(values,26)
    dif=[a-b for a,b in zip(e12,e26)]; dea=ema(dif,9)
    macd=[d-s for d,s in zip(dif,dea)]; return dif,dea,macd


def score_stock(stock):
    klines = fetch_kline(stock["code"])
    if len(klines) < 15: return 0, "鏁版嵁涓嶈冻"
    closes = [float(k.get("close",0)) for k in klines]
    if not closes or closes[-1]==0: return 0, "鏁版嵁寮傚父"
    scores=[]; reasons=[]
    yest = stock["chg_pct"]
    if -1<=yest<=5: scores.append(2); reasons.append("娑ㄨ穼骞呴€備腑")
    elif yest>5 and yest<9.8: scores.append(1); reasons.append("鏄ㄦ棩鍋忓己")
    elif yest>=9.8: scores.append(0); reasons.append("宸叉定鍋溾殸锔?)
    if len(klines)>=5:
        avg5 = sum(int(k.get("volume",0)) for k in klines[-5:])/5
        if avg5>0:
            vr=stock["volume"]/avg5
            if 1.0<=vr<=3.0: scores.append(2); reasons.append("閲忚兘閫備腑(鍋ュ悍)")
            elif vr>3.0: scores.append(1); reasons.append("鏀鹃噺鏄庢樉")
            else: scores.append(-1); reasons.append("缂╅噺鈿狅笍")
    sma5=calc_sma(closes,5); sma20=calc_sma(closes,20)
    if sma5 and sma5[-1] and sma20 and sma20[-1]:
        if sma5[-1]>sma20[-1]: scores.append(2); reasons.append("澶氬ご瓒嬪娍(MA5>MA20)")
        else: scores.append(-1); reasons.append("绌哄ご瓒嬪娍")
    if sma5 and sma5[-1] and sma5[-1]>0:
        dev=(stock["current"]-sma5[-1])/sma5[-1]*100
        if -2<=dev<=3: scores.append(2); reasons.append("璐磋繎MA5(鎶€鏈拱鐐?")
        elif dev>8: scores.append(-2); reasons.append("鍋忕MA5杩囧ぇ鈿狅笍")
        else: scores.append(0)
    amp=stock["amplitude"]
    if 1<=amp<=5: scores.append(1); reasons.append("鎸箙閫備腑")
    elif amp>8: scores.append(-1); reasons.append("娉㈠姩杩囧ぇ鈿狅笍")
    rsi_vals=calc_rsi(closes)
    if rsi_vals and rsi_vals[-1] is not None:
        rv=rsi_vals[-1]
        if 30<=rv<=60: scores.append(2); reasons.append(f"RSI閫備腑鏈夌┖闂?{rv:.0f})")
        elif 60<rv<=75: scores.append(1); reasons.append(f"RSI鍋忓己({rv:.0f})")
        elif rv>75: scores.append(-2); reasons.append(f"RSI瓒呬拱({rv:.0f})鈿狅笍")
        elif rv<30: scores.append(0); reasons.append(f"RSI瓒呭崠({rv:.0f})")
    dif,dea,macd=calc_macd(closes)
    if macd and len(macd)>=2:
        if macd[-1]>0 and macd[-1]>macd[-2]: scores.append(2); reasons.append("MACD閲戝弶绾㈡煴鏀惧ぇ(寮哄娍)")
        elif macd[-1]>0 and macd[-1]<=macd[-2]: scores.append(0); reasons.append("MACD绾㈡煴璧板钩")
        elif macd[-1]>macd[-2]: scores.append(1); reasons.append("MACD缁挎煴缂╃煭(鎷愮偣)")
        else: scores.append(-2); reasons.append("MACD姝诲弶鈿狅笍")
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
<h1>{today} 鏃╃洏閫夎偂鍙傝€?/h1>
<p style="color:#95a5a6">鍏ㄥ競鍦虹瓫閫?路 鍩轰簬鎶€鏈寚鏍?路 浠呬緵鍙傝€?/p>
<table width="100%" cellspacing="0"><tr><th>#</th><th>鑲＄エ</th><th>浠ｇ爜</th><th>琛屼笟</th><th>鏀剁洏浠?/th><th>娑ㄨ穼骞?/th><th>閫昏緫</th></tr>
{rows}</table>
<div class="footer">AI鑷姩鐢熸垚锛屼笉鏋勬垚鎶曡祫寤鸿<br>鑲″競鏈夐闄╋紝鎶曡祫闇€璋ㄦ厧</div>
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
        s=p.get("sector","鍏朵粬")
        if sec_cnt.get(s,0)<2: picks.append(p); sec_cnt[s]=sec_cnt.get(s,0)+1
    picks=picks[:6]
    for i,p in enumerate(picks,1):
        print(f"  {i}. {p['name']}({p['code']}) {p['current']:.2f} {p['chg_pct']:+.2f}% | Score:{p['score']}")
    html=format_report(picks)
    if send_email(f"鑲＄エ鏃╂姤 {datetime.now().strftime('%Y-%m-%d')}", html):
        print("Email sent!")
    else:
        print("Failed to send"); sys.exit(1)

if __name__=="__main__":
    main()

