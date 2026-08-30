#!/usr/bin/env python3
"""
LedgerLens — Synthetic Financial Data Generator

Usage:
  python generate.py
  python generate.py --records 500
  python generate.py --records 1000 --amount-mismatch 0.10 --duplicate 0.05
"""
import argparse, csv, os, random, uuid
from datetime import datetime, timedelta
from decimal import Decimal, ROUND_HALF_UP

def rand_amount(lo=500.0, hi=50000.0):
    return float(Decimal(str(random.uniform(lo, hi))).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP))

def rand_date(start, end):
    return start + timedelta(seconds=random.randint(0, int((end - start).total_seconds())))

def new_id(prefix):
    return f"{prefix}-{uuid.uuid4().hex[:10].upper()}"

def rzp_fee(amount):
    fee = min(amount * 0.02, 1500.0)
    total = fee + fee * 0.18
    return float(Decimal(str(total)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP))

METHODS   = ["upi","card","netbanking","wallet"]
BANKS     = ["HDFC","ICICI","SBI","AXIS","KOTAK"]
MERCHANTS = [f"MERCH-{i:04d}" for i in range(1,6)]
S = datetime(2024,1,1); E = datetime(2024,8,1)

def _base():
    oid = new_id("ORD"); mid = random.choice(MERCHANTS); cid = new_id("CUST")
    amt = rand_amount(); dt  = rand_date(S, E)
    utr = f"UTR{random.randint(10**11,10**12-1)}"
    fee = rzp_fee(amt); net = round(amt - fee, 2)
    sdt = dt + timedelta(days=random.randint(1,3)); sid = new_id("SET"); bid = new_id("BNK")
    order = {"order_id":oid,"merchant_id":mid,"customer_id":cid,"amount":amt,"currency":"INR",
             "status":"captured","payment_method":random.choice(METHODS),"created_at":dt.isoformat(),"reference_id":utr}
    settle= {"settlement_id":sid,"order_id":oid,"merchant_id":mid,"gross_amount":amt,"fee":fee,
             "net_amount":net,"utr":utr,"status":"processed","settled_at":sdt.isoformat()}
    bank  = {"bank_txn_id":bid,"utr":utr,"credit_amount":net,"debit_amount":0.0,
             "narration":f"RAZORPAY/{utr}/{mid}","transaction_date":sdt.isoformat(),
             "value_date":(sdt+timedelta(days=1)).isoformat(),"bank":random.choice(BANKS)}
    truth = {"order_id":oid,"settlement_id":sid,"bank_txn_id":bid,
             "anomaly_type":"clean","expected_match":True,"notes":""}
    return order, settle, bank, truth

def gen_clean():               return _base()
def gen_amount_mismatch():
    o,s,b,t = _base(); d = random.choice([-1,1])*round(random.uniform(10,500),2)
    s["gross_amount"]=round(s["gross_amount"]+d,2); s["net_amount"]=round(s["net_amount"]+d,2); b["credit_amount"]=s["net_amount"]
    t.update(anomaly_type="amount_mismatch",expected_match=False,notes=f"Delta ₹{abs(d):.2f}"); return o,s,b,t
def gen_missing_settlement():
    o,_,__,t = _base(); t.update(anomaly_type="missing_settlement",expected_match=False,settlement_id=None,bank_txn_id=None,notes="No settlement"); return o,None,None,t
def gen_duplicate():
    o,s,b,t = _base()
    dup=s.copy(); dup["settlement_id"]=new_id("SET"); dup["utr"]=f"UTR{random.randint(10**11,10**12-1)}"
    dup["settled_at"]=(datetime.fromisoformat(s["settled_at"])+timedelta(hours=random.randint(1,48))).isoformat()
    t.update(anomaly_type="duplicate",expected_match=False,notes=f"Duplicate {dup['settlement_id']}"); return o,s,b,t,dup
def gen_date_mismatch():
    o,s,b,t = _base(); late=random.randint(10,30)
    ld=(datetime.fromisoformat(s["settled_at"])+timedelta(days=late)).isoformat()
    s["settled_at"]=ld; b["transaction_date"]=ld
    t.update(anomaly_type="date_mismatch",expected_match=False,notes=f"{late}d late"); return o,s,b,t
def gen_partial():
    o,s,b,t = _base(); r=random.uniform(0.4,0.85)
    s["gross_amount"]=round(s["gross_amount"]*r,2); s["net_amount"]=round(s["net_amount"]*r,2); b["credit_amount"]=s["net_amount"]
    t.update(anomaly_type="partial_settlement",expected_match=False,notes=f"{r*100:.0f}% settled"); return o,s,b,t
def gen_unknown():
    amt=rand_amount(); mid=random.choice(MERCHANTS); utr=f"UTR{random.randint(10**11,10**12-1)}"
    fee=rzp_fee(amt); net=round(amt-fee,2); sid=new_id("SET"); bid=new_id("BNK"); dt=rand_date(S,E)
    s={"settlement_id":sid,"order_id":None,"merchant_id":mid,"gross_amount":amt,"fee":fee,"net_amount":net,"utr":utr,"status":"processed","settled_at":dt.isoformat()}
    b={"bank_txn_id":bid,"utr":utr,"credit_amount":net,"debit_amount":0.0,"narration":f"RAZORPAY/{utr}/{mid}",
       "transaction_date":dt.isoformat(),"value_date":(dt+timedelta(days=1)).isoformat(),"bank":random.choice(BANKS)}
    t={"order_id":None,"settlement_id":sid,"bank_txn_id":bid,"anomaly_type":"unknown_transaction","expected_match":False,"notes":"No matching order"}
    return None,s,b,t

def generate(records=100, amount_mismatch=0.10, duplicate=0.05, missing_settlement=0.05,
             date_mismatch=0.04, partial=0.03, unknown=0.03, output_dir="data/generated", seed=None):
    if seed is not None:
        random.seed(seed)
    asum = amount_mismatch+duplicate+missing_settlement+date_mismatch+partial+unknown
    if asum>1.0: raise ValueError(f"Anomaly ratios sum {asum:.2f} > 1.0")
    counts = {"clean":int(records*(1-asum)),"amount_mismatch":int(records*amount_mismatch),
              "duplicate":int(records*duplicate),"missing_settlement":int(records*missing_settlement),
              "date_mismatch":int(records*date_mismatch),"partial_settlement":int(records*partial),
              "unknown_transaction":int(records*unknown)}
    counts["clean"] += records - sum(counts.values())
    orders,settlements,banks,truths,extras = [],[],[],[],[]
    dispatch = {"clean":gen_clean,"amount_mismatch":gen_amount_mismatch,"missing_settlement":gen_missing_settlement,
                "date_mismatch":gen_date_mismatch,"partial_settlement":gen_partial}
    for at,cnt in counts.items():
        for _ in range(cnt):
            if at=="duplicate":
                o,s,b,t,dup=gen_duplicate(); extras.append(dup)
            elif at=="unknown_transaction":
                o,s,b,t=gen_unknown()
            else:
                o,s,b,t=dispatch[at]()
            if o: orders.append(o)
            if s: settlements.append(s)
            if b: banks.append(b)
            truths.append(t)
    settlements.extend(extras)
    random.shuffle(orders); random.shuffle(settlements); random.shuffle(banks)
    os.makedirs(output_dir, exist_ok=True)
    def wcsv(name,rows):
        if not rows: return
        with open(os.path.join(output_dir,name),"w",newline="",encoding="utf-8") as f:
            w=csv.DictWriter(f,fieldnames=rows[0].keys()); w.writeheader(); w.writerows(rows)
    wcsv("orders.csv",orders); wcsv("settlements.csv",settlements)
    wcsv("bank_transactions.csv",banks); wcsv("ground_truth.csv",truths)
    summary: dict = {}
    for t in truths:
        k = t["anomaly_type"]
        summary[k] = summary.get(k, 0) + 1
    print(f"\n[ok]  LedgerLens — Synthetic Data Generator  (seed={seed})")
    print(f"   Output: {output_dir}/")
    print(f"\n   orders.csv             → {len(orders):>5} records")
    print(f"   settlements.csv        → {len(settlements):>5} records  (+{counts['duplicate']} duplicates)")
    print(f"   bank_transactions.csv  → {len(banks):>5} records")
    print(f"   ground_truth.csv       → {len(truths):>5} records")
    print("\n   Anomaly breakdown:")
    for k,v in summary.items():
        print(f"     {k:<28} {v:>4}  ({v/records*100:.1f}%)")
    print("\n   [ok]  Ready for reconciliation engine.\n")
    return {"orders":orders,"settlements":settlements,"bank_txns":banks,"truths":truths}

if __name__=="__main__":
    p=argparse.ArgumentParser(description="LedgerLens Synthetic Data Generator",formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    p.add_argument("--records",type=int,default=100); p.add_argument("--amount-mismatch",type=float,default=0.10)
    p.add_argument("--duplicate",type=float,default=0.05); p.add_argument("--missing-settlement",type=float,default=0.05)
    p.add_argument("--date-mismatch",type=float,default=0.04); p.add_argument("--partial",type=float,default=0.03)
    p.add_argument("--unknown",type=float,default=0.03); p.add_argument("--output-dir",type=str,default="data/generated")
    p.add_argument("--seed",type=int,default=42); a=p.parse_args()
    generate(a.records,a.amount_mismatch,a.duplicate,a.missing_settlement,a.date_mismatch,a.partial,a.unknown,a.output_dir,a.seed)
