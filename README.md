# CTA Automated Ticketing System

ATHE Level 4 Diploma in Computing — Unit 2: Programming and Scripting

Student: Chomanand Kokil
Institution: South London College
Version: 4.1.1 — October 2026 (resubmission following IQA feedback dated 16.10.2026)
Program file: `level4-Unit2_CTA_Automatedticketingsystem.py`

A zone-based ticketing system for the Centrala Underground, written in Python with a tkinter interface. Travellers choose a boarding and destination zone, enter the number of Adult, Child, Senior and Student travellers, and receive a travel voucher. All fares are held and shown in integer cents, as stated in the client brief.

## How to Run

**Requirements**
- Python 3.9 or higher: https://www.python.org (tkinter is included)
- ReportLab (optional, needed only for the PDF receipt)

**Install ReportLab (Windows)**

```
pip install -r requirements.txt
```

**Start the program**

```
python level4-Unit2_CTA_Automatedticketingsystem.py
```

**Run the automated self-tests (18 checks)**

```
python level4-Unit2_CTA_Automatedticketingsystem.py --selftest
```

The program creates `cta_transactions.csv` (a log of issued vouchers) next to itself, and `cta_ticketing.log` only if an error occurs.

## Scope

**Mandatory (client brief, Appendix 2):** alphabetical stations board by zone (Central 10, Midtown 12, Downtown 14); numbered boarding and destination zone menus; Adult, Child, Senior and Student counts; a voucher showing the issue date and time, both zones, zones travelled, the count, fare and total for every category (including zero counts), total travellers and total fare; and the choice to issue another voucher or end the program.

**Optional extensions (not required by the brief):** simulated Card, Cash and PayPal payment (no real payment is taken and no details are stored), printing, a PDF receipt, and seven enhancements: station finder (ENH-1), live fare preview (ENH-2), transaction log (ENH-3), staff sales summary (ENH-4), kiosk idle timeout (ENH-5), keyboard shortcuts (ENH-6) and error log (ENH-7).

## Version History

| Version | Date | Summary |
|---|---|---|
| 3.1.0 | March 2026 | First submission (tag `v3.1.0`). |
| 3.5.0 | September 2026 | Fares changed from pence/pounds to cents. Submitted to the college but not committed to this repository. |
| 4.0.0 | October 2026 | IQA amendments: station zones corrected, zero-count categories shown, full input reset, unique voucher references. Not committed separately. |
| 4.1.1 | October 2026 | Enhancements ENH-1 to ENH-7, automated self-tests, voucher display fix, payment guard (tag `v4.1.1`). |

The full change log is in the header comment of the program file.
