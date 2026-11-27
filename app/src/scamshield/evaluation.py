"""Offline evaluation of the rule engine on a SYNTHETIC labelled message set constructed by the engineers.

Honest scope: the author wrote both the rules and the messages, so scores are optimistic and show
regressions, not real-world accuracy. Thresholds were tuned on the DEV split only; the TEST split is
reported separately. A real evaluation needs messages collected under consent with independent labels.
"""

from __future__ import annotations

import json
import random
from collections import Counter
from dataclasses import dataclass
from pathlib import Path

from .analysis import analyse_message

SUSPICIOUS_LABELS = ("several_warning_signs", "some_warning_signs")

NAMES = ["Wanjiku", "Otieno", "Achieng", "Kamau", "Mwangi", "Njeri", "Odhiambo", "Wafula", "Chebet", "Mutua"]
AMOUNTS = ["500", "1,200", "2,500", "7,800", "15,000", "30,000", "100,000"]
TILLS = ["000111", "000222", "000333", "000444"]

# (id, category, text). {n} name, {a} amount, {t} till/phone placeholder.
SCAM = [
    ("rev1", "reversal", "Hi {n}, I sent KES {a} to your number by mistake. Please reverse the money back to me urgently."),
    ("rev2", "reversal", "Confirmed. KES {a} sent to you wrong number. Tafadhali rudisha pesa hizo kwa namba hii sasa hivi."),
    ("rev3", "reversal", "Sorry I sent you money erroneously, kindly reverse the transaction to this number, I am stranded."),
    ("rev4", "reversal", "Tuma kwa makosa KES {a}. Naomba urudishe hizo pesa mara moja, asante."),
    ("pri1", "prize", "Congratulations {n}! You have won KES {a} in our Safaricom promo. Pay a processing fee to till {t} to claim."),
    ("pri2", "prize", "Umeshinda zawadi ya KES {a}! Tuma ada ya usajili kwa till {t} ili kupokea. Haraka."),
    ("pri3", "prize", "WINNER! You won a free gift. Click http://safaricom-rewards-ke.top/claim within 24 hours to receive your prize."),
    ("pri4", "prize", "Lottery jackpot: you have won KES {a}. Send a registration fee to claim today, offer expires."),
    ("phi1", "phishing", "Dear customer your KCB account will be suspended. Confirm your details at http://kcb-secure-login.top/verify now."),
    ("phi2", "phishing", "M-PESA: Your account has been blocked. Verify your PIN at http://mpesa-verify.xyz immediately to restore."),
    ("phi3", "phishing", "Equity Bank alert: unusual login. Confirm your identity and password at http://bit.ly/3xKq9a to avoid closure."),
    ("phi4", "phishing", "KRA: you have an unpaid tax refund. Submit your PIN and ID number at http://kra-refunds.click to receive KES {a}."),
    ("phi5", "phishing", "Thibitisha akaunti yako sasa hivi au akaunti yako itafungwa. Ingia hapa http://safaricom-portal.icu"),
    ("phi6", "phishing", "eCitizen notice: your account is deactivated. Re-activate at http://ecitizen-gov-ke.top and enter your password."),
    ("otp1", "credential", "Hello this is Safaricom support. Please send us the verification code you just received to confirm your account."),
    ("otp2", "credential", "Bank security: reply with your OTP and PIN to stop the fraudulent transaction on your account."),
    ("otp3", "credential", "Tutumie namba ya siri na OTP uliyopokea ili tuthibitishe akaunti yako ya M-Pesa leo."),
    ("inv1", "investment", "Invest KES {a} today and get guaranteed returns of 40% weekly. No risk. WhatsApp us now."),
    ("inv2", "investment", "Double your money in 7 days with our forex signals. Daily profit, deposit first, withdraw anytime."),
    ("inv3", "investment", "Crypto signals group: 25% daily returns, join now, send deposit to wallet and message me on Telegram."),
    ("inv4", "investment", "Wekeza KES {a} upate faida ya guaranteed returns kila wiki. Hakuna risk. Tuma pesa sasa."),
    ("job1", "jobs", "We are hiring! Work from home, earn KES {a} daily. Pay a registration fee of KES 500 to start. WhatsApp us."),
    ("job2", "jobs", "Job offer at an international NGO. Pay clearance fee KES {a} to release your appointment letter."),
    ("job3", "jobs", "Ajira kwa mtandao, earn KES {a} per day. Tuma ada ya usajili kwa till {t} leo."),
    ("adv1", "advance_fee", "Your parcel from abroad is held at customs. Pay a release fee of KES {a} to till {t} today to receive it."),
    ("adv2", "advance_fee", "Dear beneficiary, an inheritance of USD 2M awaits. Send a handling fee to proceed, reply urgently."),
    ("adv3", "advance_fee", "Loan approved KES {a}! Pay the processing fee first to receive funds within 1 hour."),
    ("thr1", "threat", "Final notice: legal action will follow, you will be arrested unless you pay KES {a} to till {t} within 24 hours."),
    ("thr2", "threat", "Your NSSF account has been suspended. Confirm your ID number and PIN immediately to avoid legal action."),
    ("imp1", "impersonation", "Hi mum, this is my new number. Send KES {a} urgently, I will explain later. Contact me on WhatsApp."),
    ("imp2", "impersonation", "Safaricom customer care: your SIM will be deactivated. Send your PIN and ID number to http://safaricom-care.top."),
    ("sho1", "shortener", "Free data bundles for all! Claim now http://bit.ly/free-data-ke before it expires."),
    ("sho2", "shortener", "You have been selected for the youth fund, register at http://tinyurl.com/youthfund-ke urgently."),
    ("hrd1", "hard", "I sent you money by mistake pls return"),
    ("hrd2", "hard", "Please pay a clearance fee to release the package"),
    ("hrd3", "hard", "You won a free gift, reply to claim"),
    ("hrd4", "hard", "Send your OTP to confirm your account"),
]

LEGIT = [
    ("mp1", "receipt", "SKT7XYZ123 Confirmed. KES {a}.00 sent to {n} 0700000000 on 12/3/26 at 2:14 PM. New M-PESA balance is KES 3,420.50. Transaction cost KES 7.00."),
    ("mp2", "receipt", "SKT8ABC456 Confirmed. You have received KES {a}.00 from {n} on 4/5/26 at 9:02 AM. New M-PESA balance is KES 5,120.00."),
    ("mp3", "receipt", "SLK1DEF789 Confirmed. KES {a}.00 paid to SUPERMARKET LTD on 7/6/26. New M-PESA balance is KES 810.00."),
    ("otpl1", "otp", "Your Equity Bank one-time code is 482913. It expires in 5 minutes. Do not share it with anyone, the bank will never ask for it."),
    ("otpl2", "otp", "KCB: Your verification code is 771204. Never share this code with anyone, including KCB staff."),
    ("otpl3", "otp", "Msimbo wako wa OTP ni 502911. Usishiriki na mtu yeyote. Ni halali kwa dakika 5."),
    ("bank1", "bank", "Co-op Bank: Your account ending 4521 was credited with KES {a} on 3 March. Thank you for banking with us."),
    ("bank2", "bank", "NCBA: Your statement for February is ready. Log in to your app to view it. We will never ask for your PIN."),
    ("bank3", "bank", "Absa: Your card ending 8812 was used at a shop for KES {a}. If this was not you call the number on the back of your card."),
    ("tel1", "telco", "Safaricom: You have used 80% of your data bundle. Dial *544# to check your balance. Visit https://www.safaricom.co.ke for offers."),
    ("tel2", "telco", "Airtel: Your 1GB bundle expires tomorrow. Dial *334# to renew. Details at https://www.airtel.co.ke."),
    ("gov1", "gov", "KRA: Your annual returns for 2025 were received. Reference KRA2026001. Visit https://www.kra.go.ke for more information."),
    ("gov2", "gov", "NSSF: Your contribution for March has been received. Check your member statement on https://www.nssf.go.ke."),
    ("soc1", "social", "Hi {n}, are we still meeting for lunch tomorrow at 1pm near the office?"),
    ("soc2", "social", "Happy birthday {n}! Wishing you a wonderful year ahead. Let's catch up this weekend."),
    ("soc3", "social", "Mama, nimefika salama. Nitakupigia jioni. Usijali."),
    ("soc4", "social", "Please send me the meeting notes when you have a moment, thanks."),
    ("soc5", "social", "Don't forget the school fees deadline is next Friday. I will pay through the school's paybill as usual."),
    ("work1", "work", "Reminder: team standup moved to 10am. Please update the tracker before the call."),
    ("work2", "work", "Your interview is scheduled for Monday 9am at our Westlands office. Please bring your ID and certificates. Reply to confirm."),
    ("work3", "work", "Invoice 2041 for KES {a} is attached. Payment terms are 30 days to the account on the invoice."),
    ("del1", "delivery", "Your order #55821 has been dispatched and will arrive tomorrow between 9am and 1pm. Track at https://www.jumia.co.ke."),
    ("del2", "delivery", "Your parcel is ready for pickup at the Nairobi CBD counter. Please carry your ID."),
    ("hlt1", "health", "Reminder: your clinic appointment is on Thursday at 3pm. Reply YES to confirm or call the clinic to reschedule."),
    ("utl1", "utility", "KPLC: Your token purchase of KES {a} was successful. Units: 24.5. Meter 0123456789."),
    ("utl2", "utility", "Nairobi Water: Your bill for February is KES {a}. Pay via the official paybill listed on your statement."),
    ("edu1", "education", "School notice: Term 2 opens on Monday. Fees structure was sent home in the term circular."),
    ("nws1", "news", "Weather alert: heavy rain expected in Nairobi this evening. Drive carefully."),
    ("hrdl1", "hard", "I sent you the money for the tickets, please confirm you received it."),
    ("hrdl2", "hard", "Your Safaricom bundle was activated successfully. Thank you for choosing Safaricom."),
    ("hrdl3", "hard", "Reminder from KCB: please do not share your PIN with anyone. We will never ask for it by SMS."),
    ("hrdl4", "hard", "Congratulations on your graduation, we are so proud of you!"),
    ("hrdl5", "hard", "Equity Bank: Your loan repayment of KES {a} is due on 5th. Please pay through the app or branch."),
]


@dataclass
class Item:
    id: str
    text: str
    label: str  # "suspicious" | "benign"
    group: str
    split: str


def build_dataset(seed: int = 2026, variants: int = 5) -> list[Item]:
    rnd = random.Random(seed)  # noqa: S311 - deterministic data generation, not security
    items: list[Item] = []
    for label, bank in (("suspicious", SCAM), ("benign", LEGIT)):
        for base_id, group, tpl in bank:
            n_var = 1 if "{" not in tpl else variants
            seen: set[str] = set()
            tries = 0
            while len(seen) < n_var and tries < 20:
                tries += 1
                text = tpl.format(n=rnd.choice(NAMES), a=rnd.choice(AMOUNTS), t=rnd.choice(TILLS))
                seen.add(text)
            for k, text in enumerate(sorted(seen)):
                iid = f"{base_id}-{k}"
                items.append(Item(iid, text, label, group, "dev" if rnd.random() < 0.5 else "test"))
    return items



# Blind hold-out: written AFTER the rules and thresholds were frozen, run once, never used for tuning.
HOLDOUT = [
    ("suspicious", "Habari, nimekutumia pesa kimakosa tafadhali nirudishie ASAP nimeshikwa."),
    ("suspicious", "Dear customer, your M-Pesa will expire today. Update now at http://m-pesa-update.top to continue using the service."),
    ("suspicious", "Hello, I am Dr. Grace, I am lonely and want a serious partner. Please send KES 3,000 for my airtime so we can talk on WhatsApp."),
    ("suspicious", "Your ATM card is blocked. Call 0700000000 and give your card PIN to unblock."),
    ("suspicious", "Earn money online! Invest KES 5,000 and receive KES 50,000 in 3 days. Guaranteed returns, no risk."),
    ("suspicious", "URGENT: Your electricity token purchase failed. Re-enter your M-Pesa PIN at http://kplc-tokens.click to get your units."),
    ("suspicious", "Uber driver job open, pay a registration fee of KES 1,000 to till 000555 and start today. Contact us on WhatsApp."),
    ("suspicious", "You have been selected to receive a government grant of KES 80,000. Confirm your ID number and send KES 600 processing fee."),
    ("suspicious", "Hi, sorry I used the wrong number to send you money erroneously, kindly reverse KES 4,500 now."),
    ("suspicious", "Safaricom: Your line is flagged. Confirm your account password at http://safaricom-kyc.xyz within 2 hours."),
    ("suspicious", "Congratulations, jackpot winner! Claim your KES 1,000,000 by paying a clearance fee today."),
    ("suspicious", "Pesa yako imezuiliwa. Tuma namba ya siri ili tuifungue mara moja."),
    ("suspicious", "Final warning from the court: pay KES 10,000 to till 000666 or you will be arrested."),
    ("suspicious", "Bitcoin mining pool: daily profit 15%, send USDT now, message me on Telegram to join."),
    ("suspicious", "Click http://bit.ly/ke-loan to get an instant loan, no documents, pay a small activation fee."),
    ("suspicious", "I am the manager at your bank. We detected fraud. Share the verification code sent to your phone to cancel it."),
    ("suspicious", "Your parcel delivery failed. Pay a handling fee at http://ke-post-parcel.top within 24 hours or it will be returned."),
    ("suspicious", "Free airtime for all Safaricom users, register here http://free-airtime-ke.icu urgently."),
    ("suspicious", "Hello sir, I have a business proposal, you will earn big. Just a small registration fee needed."),
    ("suspicious", "Wanna make quick cash? DM me, forex signals guarantee profit."),
    ("benign", "Hi, can you send me the report before 5pm please? The client is waiting."),
    ("benign", "Your Equity Bank statement is ready. For help visit https://equitygroupholdings.com or call the number on your card."),
    ("benign", "M-PESA reminder: your Fuliza limit was updated. For details dial *234#."),
    ("benign", "Urgent: the road to Thika is closed because of an accident, please use the bypass."),
    ("benign", "SLM3QWE890 Confirmed. KES 1,000.00 paid to KPLC PREPAID on 2/9/26. New M-PESA balance is KES 2,000.00."),
    ("benign", "Safaricom: Your new SIM registration was successful. Visit https://www.safaricom.co.ke for more."),
    ("benign", "Hey, sorry I sent you the wrong file earlier, here is the correct one."),
    ("benign", "Your child's school bus will be 20 minutes late today due to traffic."),
    ("benign", "Job opening: Accountant at a Nairobi firm. Apply by email with your CV before the 30th. No fees apply."),
    ("benign", "NCBA: Your loan application was received. A relationship manager will call you from the bank's official number."),
    ("benign", "Kindly confirm attendance for the chama meeting on Saturday, contribution is KES 2,000 as agreed."),
    ("benign", "Your KRA iTax return acknowledgment is attached. Keep it for your records."),
    ("benign", "Don't share your password with anyone, even people who say they work for us. Stay safe online."),
    ("benign", "Thanks for the payment, I have sent the receipt to your email."),
    ("benign", "Lunch at 1? I'll pay this time."),
    ("benign", "Weka alarm, kesho tunaamka mapema kwa safari ya Mombasa."),
    ("benign", "Airtel: You have received KES 500 from a friend. Your new balance is KES 800."),
    ("benign", "Your parcel from the online store has been delivered to your gate. Thank you for shopping with us."),
    ("benign", "Please confirm your account details by visiting the nearest branch with your ID; we do not collect details by SMS."),
    ("benign", "Hongera kwa kuhitimu! Tunajivunia sana."),
]


def holdout_items() -> list[Item]:
    return [Item(f"hold-{i}", t, lab, "holdout", "holdout") for i, (lab, t) in enumerate(HOLDOUT)]


@dataclass
class Metrics:
    tp: int
    fp: int
    fn: int
    tn: int

    @property
    def precision(self) -> float:
        return self.tp / (self.tp + self.fp) if self.tp + self.fp else 0.0

    @property
    def recall(self) -> float:
        return self.tp / (self.tp + self.fn) if self.tp + self.fn else 0.0

    @property
    def f1(self) -> float:
        p, r = self.precision, self.recall
        return 2 * p * r / (p + r) if p + r else 0.0

    @property
    def accuracy(self) -> float:
        n = self.tp + self.fp + self.fn + self.tn
        return (self.tp + self.tn) / n if n else 0.0


def evaluate(items: list[Item]) -> tuple[Metrics, list[tuple[Item, str]], Counter[tuple[str, str]]]:
    tp = fp = fn = tn = 0
    errors: list[tuple[Item, str]] = []
    confusion: Counter[tuple[str, str]] = Counter()
    for it in items:
        label = analyse_message(it.text).label
        pred = "suspicious" if label in SUSPICIOUS_LABELS else "benign"
        confusion[(it.label, label)] += 1
        if it.label == "suspicious" and pred == "suspicious":
            tp += 1
        elif it.label == "benign" and pred == "suspicious":
            fp += 1
            errors.append((it, label))
        elif it.label == "suspicious":
            fn += 1
            errors.append((it, label))
        else:
            tn += 1
    return Metrics(tp, fp, fn, tn), errors, confusion


def run_evaluation(write: bool = False) -> int:
    items = build_dataset()
    out_dir = Path(__file__).resolve().parents[2] / "evaluation"
    lines = []
    items = items + holdout_items()
    for split in ("dev", "test", "holdout", "all"):
        subset = items if split == "all" else [i for i in items if i.split == split]
        m, errors, conf = evaluate(subset)
        lines.append(f"{split}: n={len(subset)} precision={m.precision:.3f} recall={m.recall:.3f} f1={m.f1:.3f} accuracy={m.accuracy:.3f} tp={m.tp} fp={m.fp} fn={m.fn} tn={m.tn}")
        if split in ("test", "holdout"):
            for it, lab in errors:
                lines.append(f"  {split} error: {it.id} true={it.label} predicted_label={lab}: {it.text[:80]}")
            lines.append(f"  {split} confusion (true, engine label): " + json.dumps({f"{a}|{b}": c for (a, b), c in sorted(conf.items())}))
    print("\n".join(lines))
    if write:
        out_dir.mkdir(exist_ok=True)
        with (out_dir / "dataset.jsonl").open("w", encoding="utf-8") as fh:
            for it in items:
                fh.write(json.dumps({"id": it.id, "text": it.text, "label": it.label, "group": it.group, "split": it.split, "origin": "synthetic test data"}, ensure_ascii=False) + "\n")
        (out_dir / "results.txt").write_text("\n".join(lines) + "\n", encoding="utf-8")
    return 0
