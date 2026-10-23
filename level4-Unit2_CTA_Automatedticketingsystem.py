"""
=============================================================================
 CTA – CENTRALA TRANSPORT AUTHORITY - AUTOMATED TICKETING SYSTEM
=============================================================================
 Author      : Chomanand Kokil
 Unit        : ATHE Level 4 Diploma in Computing – Unit 2
               Programming and Scripting
 Assessment  : Assignment Task 3 – Implementation & Testing
 Description : A zone-based ticketing system for the Centrala Underground.
               Built with Python (tkinter) following PEP 8 style guidelines.
 Version     : 4.1.0 (IQA amendment + enhancements – October 2026)
 Date        : March 2026 (amended September and October 2026)
 File        : level4-Unit2_CTA_Automatedticketingsystem.py
=============================================================================

HOW TO RUN
----------
  python level4-Unit2_CTA_Automatedticketingsystem.py            (GUI)
  python level4-Unit2_CTA_Automatedticketingsystem.py --selftest (tests)

The --selftest option runs the automated checks in run_self_tests()
without opening the GUI. They verify the reference data against
Appendix 1, the fare arithmetic against Appendix 2, the voucher
breakdown (including zero-count categories) and reference uniqueness.
ReportLab (pip install reportlab) is needed only for the optional PDF
receipt; the rest of the program runs without it.

CHANGE LOG
----------
v4.1.0  October 2026 – enhancements (all OPTIONAL, beyond the brief).
  Each is tagged [ENH-n] in the code so it can be found with a search.
  [ENH-1] Station finder. The traveller types a station name and the
          system shows its zone and can select it as the boarding or
          destination zone. Answers the usability problem found in
          user testing: travellers know their STATION, but the brief
          asks them to choose a ZONE. Case-insensitive, with
          "did you mean" suggestions for partial or mistyped names.
  [ENH-2] Live fare preview. The traveller screen shows the running
          total and traveller count while counts are entered, so the
          cost is visible before the payment step.
  [ENH-3] Transaction log. Every issued voucher is appended to
          cta_transactions.csv (reference, time, zones, counts, total,
          payment method). Gives CTA an audit trail and a record for
          reconciling takings. No personal data is recorded.
  [ENH-4] Staff sales summary. A button on the stations board reads
          the transaction log and shows today's vouchers, travellers,
          takings and payment-method split.
  [ENH-5] Kiosk idle timeout. After 2 minutes with no activity the
          system resets and returns to the stations board, so a
          half-finished journey is not left for the next traveller.
          It never fires while a payment dialog is open.
  [ENH-6] Keyboard shortcuts. Enter = Continue, Escape = Back, on every
          screen where those actions exist. Supports users who cannot
          use a mouse or touch screen easily (accessibility).
  [ENH-7] Error log. Unexpected errors (printing, PDF, log file) are
          written to cta_ticketing.log with a timestamp, so support
          staff can diagnose problems after handover (AC 4M1).
v4.0.0  October 2026 – IQA feedback (16.10.2026)
  [AC 2.1/3.1] ZONES matches Appendix 1: Lomil to Central; Riclya,
         Sylas to Midtown (10/12/14). Checked at start-up.
  [AC 2.2/3.1] Voucher and PDF list all four categories, including
         zero counts, from one shared function.
  [AC 3.1/4.2] "New Ticket" also clears zone and traveller inputs.
  [AC 4.2] References unique even within the same second.
  [AC 4.2] Issue time and reference fixed once, at payment.
  [AC 4.2] PDF preview stays open after saving; save errors caught.
  [Fix]  Preview scrolling, card delay and payment-method crash fixed.
v3.5.0  September 2026 – fares held and shown in integer cents.
=============================================================================

SCOPE: MANDATORY BRIEF REQUIREMENTS vs OPTIONAL EXTENSIONS
-----------------------------------------------------------
Mandatory (Appendix 2): alphabetical stations board by zone; numbered
start-zone and destination-zone menus; Adult/Child/Senior/Student counts;
voucher with issue date and time, boarding zone, destination zone, zones
travelled, count / fare / total for each category, total travellers,
total fare; option to issue another voucher or end the program.

Optional extensions (NOT required by the brief): simulated Card, Cash
and PayPal payment dialogs, printing, the PDF receipt, and the seven
enhancements [ENH-1] to [ENH-7] listed above. The payments are
simulations only: no real payment is taken and no card or account
details are stored or transmitted.
=============================================================================

DESIGN OVERVIEW
---------------
The application is object-oriented (one class per screen) and
event-driven (tkinter callbacks). Pure calculation logic is kept in
module-level functions with no GUI dependency, so it can be unit-tested
on its own (modular design). Screens use a Frame-stacking technique:
all screens are created at start-up and raised as the user navigates.

Screens (in journey order):
  1. WelcomeScreen       – Station board (Central, Midtown, Downtown)
  2. ZoneSelectionScreen – Pick boarding + destination zone
  3. TravellerScreen     – Enter traveller counts
  4. PaymentScreen       – Choose payment method (Card / Cash / PayPal)
  5. VoucherScreen       – Review receipt + print / view PDF

CODING STANDARDS (PEP 8)
-------------------------
- Module-level docstring at the top of the file.
- Constants are UPPER_SNAKE_CASE.
- Classes are PascalCase.
- Functions/methods are lower_snake_case.
- Lines do not exceed 79 characters.
- Blank lines separate logical sections.
- All functions have docstrings.
- Inline comments explain non-obvious logic.
=============================================================================
"""

# ---------------------------------------------------------------------------
# STANDARD LIBRARY IMPORTS
# ---------------------------------------------------------------------------
import csv                                 # [ENH-3] Transaction log
import itertools                           # Reference sequence counter
import logging                             # [ENH-7] Error log
import os                                  # OS-level file operations
import shutil                              # Copying the saved PDF
import subprocess                          # Cross-platform process launching
import sys                                 # Command-line arguments
import tempfile                            # Temporary file creation
import tkinter as tk                       # Core GUI framework
from datetime import datetime              # Timestamp for vouchers
from tkinter import filedialog, messagebox, ttk   # Widgets & dialogs

# Third-party import – ReportLab for PDF generation
try:
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.units import mm
    from reportlab.platypus import (
        Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle
    )
    REPORTLAB_AVAILABLE = True
except ImportError:
    REPORTLAB_AVAILABLE = False


# ---------------------------------------------------------------------------
# APPLICATION-WIDE CONSTANTS
# ---------------------------------------------------------------------------

# Fare rates specified by the client in CENTS per zone.
# Values are retained exactly as stated in Appendix 2 of the client
# brief. Integer arithmetic preserves these values exactly and avoids
# floating-point rounding. No conversion to any other currency unit is
# performed at any point in the application.
ADULT_FARE_PER_ZONE = 2105   # 2105 cents per zone
CHILD_FARE_PER_ZONE = 1410   # 1410 cents per zone
SENIOR_FARE_PER_ZONE = 1025   # 1025 cents per zone
STUDENT_FARE_PER_ZONE = 1750   # 1750 cents per zone

# Colour palette – CTA brand colours (dark navy + gold accent)
COLOUR_BG = "#1B2A4A"   # Dark navy – primary background
COLOUR_PANEL = "#243860"   # Lighter navy – card backgrounds
COLOUR_ACCENT = "#F0A500"   # Gold – primary accent
COLOUR_WHITE = "#FFFFFF"   # White – primary text on dark background
COLOUR_LIGHT = "#C8D6E5"   # Light blue-grey – secondary text
COLOUR_SUCCESS = "#27AE60"   # Green – success / confirmed actions
COLOUR_DANGER = "#E74C3C"   # Red – errors / warnings
COLOUR_INPUT_BG = "#2E4070"   # Slightly lighter – input field backgrounds
COLOUR_BTN = "#F0A500"   # Gold – primary button fill
COLOUR_BTN_TEXT = "#1B2A4A"   # Navy – text on gold buttons
COLOUR_PAYPAL = "#003087"   # PayPal dark blue
COLOUR_PAYPAL2 = "#009CDE"   # PayPal light blue
COLOUR_CASH = "#1E8449"   # Green for cash
COLOUR_CARD = "#1A3A6B"   # Navy for card

# Font definitions
FONT_TITLE = ("Georgia", 22, "bold")
FONT_HEADING = ("Georgia", 14, "bold")
FONT_SUBHEADING = ("Calibri", 12, "bold")
FONT_BODY = ("Calibri", 11)
FONT_SMALL = ("Calibri", 9)
FONT_MONO = ("Courier New", 10)   # Voucher / receipt output


# ---------------------------------------------------------------------------
# DATA – CENTRALA UNDERGROUND ZONE AND STATION DEFINITIONS
# ---------------------------------------------------------------------------
# Station names and zone membership are taken directly from the
# Centrala Underground map in Appendix 1 of the client brief.
# Zone numbers map to concentric zones: 1 = Central (innermost),
# 2 = Midtown, 3 = Downtown (outermost).
# Fare formula: zones_travelled = abs(destination - start) + 1
#
# IQA October 2026 (AC 2.1 / 3.1): Lomil is inside the Central Zone
# boundary on the map, so it belongs to Central. Riclya and Sylas sit
# between the Central and Midtown boundaries, so they belong to Midtown.
# Version 3.5 had these three stations in the wrong zones (11/11/14).
# Each list is kept in alphabetical order, as Appendix 2 requires.
ZONES = {
    1: {
        "name": "Central",
        "description": "City centre hub",
        "stations": [                                    # 10 stations
            "Bylyn", "Centrala", "Frestin", "Jaund", "Lomil",
            "Ninia", "Rede", "Soth", "Tallan", "Yaen"
        ]
    },
    2: {
        "name": "Midtown",
        "description": "Inner residential & commercial",
        "stations": [                                    # 12 stations
            "Agralle", "Docia", "Garion", "Obelyn", "Oloadus",
            "Quthiel", "Ralith", "Riclya", "Riladia", "Stonyam",
            "Sylas", "Wicyt"
        ]
    },
    3: {
        "name": "Downtown",
        "description": "Outer suburbs & interchange",
        "stations": [                                    # 14 stations
            "Adohad", "Brunad", "Ederif", "Elyot", "Erean",
            "Holmer", "Keivia", "Marend", "Perinad", "Pryn",
            "Ruril", "Ryall", "Vertwall", "Zord"
        ]
    }
}

# Expected number of stations per zone, counted from the Appendix 1 map.
# Used by validate_reference_data() as an independent cross-check.
EXPECTED_STATION_COUNTS = {1: 10, 2: 12, 3: 14}

# Traveller fare configuration – drives the input form, the voucher and
# the PDF. The order of this list is the order shown on every output.
TRAVELLER_TYPES = [
    {"key": "adult",   "label": "Adults",   "fare": ADULT_FARE_PER_ZONE},
    {"key": "child",   "label": "Children", "fare": CHILD_FARE_PER_ZONE},
    {"key": "senior",  "label": "Seniors",  "fare": SENIOR_FARE_PER_ZONE},
    {"key": "student", "label": "Students", "fare": STUDENT_FARE_PER_ZONE},
]

# Upper limit on travellers of one type in a single voucher. This is a
# design assumption (not stated in the brief) that guards against
# accidental entries such as 1000 instead of 10.
MAX_TRAVELLERS_PER_TYPE = 50

# [ENH-3] / [ENH-7] Files are written next to this program so they are
# easy for CTA staff to find. os.path.abspath(__file__) makes this work
# whichever folder the program is started from.
APP_FOLDER = os.path.dirname(os.path.abspath(__file__))
TRANSACTION_LOG_FILE = os.path.join(APP_FOLDER, "cta_transactions.csv")
ERROR_LOG_FILE = os.path.join(APP_FOLDER, "cta_ticketing.log")

# [ENH-3] Column order of the transaction log. Defined once so that the
# writer and the reader can never use different column names.
TRANSACTION_FIELDS = [
    "reference", "date", "time", "boarding_zone", "destination_zone",
    "zones_travelled", "adults", "children", "seniors", "students",
    "total_travellers", "total_cents", "payment_method",
]

# [ENH-5] Kiosk idle timeout in milliseconds (2 minutes). A design
# assumption: long enough to count change or find a card, short enough
# that an abandoned journey is cleared before the next traveller.
IDLE_TIMEOUT_MS = 120_000

# [ENH-7] Module logger. Configured in configure_logging(); until then
# messages are simply discarded, so importing this file for the
# self-tests never creates a log file as a side effect.
logger = logging.getLogger("cta_ticketing")
logger.addHandler(logging.NullHandler())

# Per-session sequence used to make every voucher reference unique.
# itertools.count() never repeats, so two vouchers issued within the
# same second still receive different references (IQA AC 4.2).
_REFERENCE_SEQUENCE = itertools.count(1)


# ===========================================================================
# HELPER FUNCTIONS
# ===========================================================================

def calculate_zones_travelled(
    start_zone: int, destination_zone: int
) -> int:
    """
    Calculate the number of fare zones a journey passes through.

    Formula: |destination - start| + 1
    Example: start=1, dest=3 -> |3-1|+1 = 3 zones (Central to Downtown)
    Example: start=2, dest=2 -> |2-2|+1 = 1 zone  (same Midtown zone)

    Args:
        start_zone       (int): Zone number where the journey begins (1-3).
        destination_zone (int): Zone number where the journey ends (1-3).

    Returns:
        int: Number of zones travelled (always at least 1).
    """
    return abs(destination_zone - start_zone) + 1


def calculate_fare(
    fare_per_zone: int, zones: int, count: int
) -> int:
    """
    Calculate the total fare in CENTS for a group of travellers.

    Example: Adult, 3 zones, 1 traveller -> 2105 * 3 * 1 = 6315 cents

    Args:
        fare_per_zone (int): Rate in CENTS per zone for the traveller type.
        zones         (int): Number of zones travelled.
        count         (int): Number of travellers of this type.

    Returns:
        int: Total fare in CENTS.
    """
    return fare_per_zone * zones * count


def cents_to_display(cents: int) -> str:
    """
    Return a fare amount using the unit specified in the client brief.

    Fares are stored and calculated as integer cents. This helper
    formats the amount for display and printing WITHOUT any currency
    conversion (no division by 100 and no currency symbol), so the value
    shown is always the exact integer stated or calculated.

    Args:
        cents (int): Amount in cents.

    Returns:
        str: Formatted string, e.g. 2105 -> "2105 cents"
    """
    return f"{cents} cents"


def validate_positive_integer(
    value: str, field_name: str
) -> tuple:
    """
    Validate that a string represents a non-negative integer.

    Args:
        value      (str): Raw string value from the input widget.
        field_name (str): Human-readable name used in error messages.

    Returns:
        tuple: (bool: is_valid, int|None: parsed_value, str: error_msg)
    """
    stripped = value.strip()

    if stripped == "":
        return (
            False, None,
            f"{field_name}: Please enter a number (0 if none)."
        )

    if not stripped.isdigit():
        return (
            False, None,
            f"{field_name}: Must be a whole number (e.g. 0, 1, 2)."
        )

    number = int(stripped)
    if number > MAX_TRAVELLERS_PER_TYPE:
        return (
            False, None,
            f"{field_name}: A maximum of {MAX_TRAVELLERS_PER_TYPE} "
            f"travellers of one type can be added to one voucher."
        )

    return True, number, ""


def build_fare_breakdown(travellers: dict, zones: int) -> dict:
    """
    Build the complete fare breakdown for one voucher.

    This is the SINGLE source of fare figures for the on-screen voucher,
    the printed text and the PDF receipt, so the three can never
    disagree. Every traveller category is ALWAYS included, even when its
    count is 0, because Appendix 2 requires the voucher to display the
    number of travellers and the fare for each category
    (IQA October 2026, AC 2.2 / 3.1).

    Example: 1 traveller of each type over 3 zones
             (2105 + 1410 + 1025 + 1750) * 3 = 18870 cents

    Args:
        travellers (dict): Counts keyed by 'adult', 'child', 'senior',
                           'student'. Missing keys are treated as 0.
        zones      (int) : Number of zones travelled.

    Returns:
        dict: {
            "rows":        list of dicts, one per category, in
                           TRAVELLER_TYPES order, each with
                           key, label, count, rate, zones, total,
            "total_pax":   int, total number of travellers,
            "total_cents": int, total fare in cents
        }
    """
    rows = []
    for t_type in TRAVELLER_TYPES:
        count = travellers.get(t_type["key"], 0)
        rows.append({
            "key":   t_type["key"],
            "label": t_type["label"],
            "count": count,
            "rate":  t_type["fare"],
            "zones": zones,
            "total": calculate_fare(t_type["fare"], zones, count),
        })

    return {
        "rows":        rows,
        "total_pax":   sum(row["count"] for row in rows),
        "total_cents": sum(row["total"] for row in rows),
    }


def generate_reference(issue_time: datetime) -> str:
    """
    Create a unique voucher reference number.

    Format: CTA-YYYYMMDD-HHMMSS-NNNN
    The date and time identify when the voucher was issued; NNNN is a
    sequence number that increases by one for every voucher in the
    session. Version 3.5 used the time to the second only, so two
    vouchers issued within the same second shared a reference
    (IQA October 2026, AC 4.2).

    Limitation: the sequence restarts when the program is restarted.
    The timestamp keeps references unique between sessions on one
    machine. A multi-kiosk deployment would need a central sequence.

    Args:
        issue_time (datetime): Time the voucher was issued.

    Returns:
        str: e.g. "CTA-20261023-143005-0001"
    """
    sequence = next(_REFERENCE_SEQUENCE)
    return f"CTA-{issue_time.strftime('%Y%m%d-%H%M%S')}-{sequence:04d}"


def validate_reference_data() -> list:
    """
    Check the ZONES reference data against Appendix 1.

    Checks that each zone has the expected number of stations, that
    each list is alphabetical, and that no station appears twice.
    Called at start-up and by the self-tests, so a data-entry error
    of the kind found at IQA is detected before travellers see it.

    Returns:
        list: Error messages. An empty list means the data is valid.
    """
    errors = []
    seen = set()

    for zone_num, zone in ZONES.items():
        stations = zone["stations"]
        expected = EXPECTED_STATION_COUNTS[zone_num]

        if len(stations) != expected:
            errors.append(
                f"{zone['name']}: {len(stations)} stations, "
                f"expected {expected} (Appendix 1)."
            )
        if stations != sorted(stations):
            errors.append(f"{zone['name']}: stations not alphabetical.")

        for station in stations:
            if station in seen:
                errors.append(f"{station} appears in more than one zone.")
            seen.add(station)

    return errors


# ===========================================================================
# ENHANCEMENT HELPERS (no GUI code, so each can be unit-tested)
# ===========================================================================

def find_station(name: str):
    """
    [ENH-1] Look up which zone a station is in.

    The search ignores capital letters and surrounding spaces, so
    "lomil", "LOMIL" and " Lomil " all find Lomil.

    Args:
        name (str): Station name typed by the traveller.

    Returns:
        tuple | None: (zone_number, station_name_as_on_map), or None if
                      no station has exactly that name.
    """
    wanted = name.strip().lower()
    for zone_num, zone in ZONES.items():
        for station in zone["stations"]:
            if station.lower() == wanted:
                return zone_num, station
    return None


def suggest_stations(text: str, limit: int = 5) -> list:
    """
    [ENH-1] Suggest station names for a partial or mistyped entry.

    Names that START with the text are listed first, then names that
    CONTAIN it anywhere. Example: "ri" gives Riclya and Riladia first
    (they start with "ri"), then Ederif, Garion and Perinad (they
    contain "ri"), stopping at the limit of five. Starting matches
    come first because travellers usually type the start of a name.

    Args:
        text  (str): What the traveller has typed so far.
        limit (int): Maximum number of suggestions to return.

    Returns:
        list: Station names in alphabetical order within each group.
    """
    wanted = text.strip().lower()
    if not wanted:
        return []

    all_stations = sorted(
        station for zone in ZONES.values() for station in zone["stations"]
    )
    starts = [s for s in all_stations if s.lower().startswith(wanted)]
    contains = [
        s for s in all_stations
        if wanted in s.lower() and s not in starts
    ]
    return (starts + contains)[:limit]


def configure_logging(log_path: str = ERROR_LOG_FILE):
    """
    [ENH-7] Send warnings and errors to a log file.

    Only WARNING and above are recorded, so normal use does not fill the
    disk. If the log file cannot be opened (for example a read-only
    folder) the program carries on without it rather than failing.

    Args:
        log_path (str): Full path of the log file.
    """
    try:
        handler = logging.FileHandler(log_path, encoding="utf-8")
    except OSError:
        return                      # Logging is helpful, not essential
    handler.setFormatter(
        logging.Formatter("%(asctime)s  %(levelname)-8s  %(message)s")
    )
    logger.addHandler(handler)
    logger.setLevel(logging.WARNING)


def record_transaction(details: dict,
                       log_path: str = TRANSACTION_LOG_FILE):
    """
    [ENH-3] Append one issued voucher to the CSV transaction log.

    CSV was chosen over a database because it needs no extra software,
    opens directly in Excel for CTA finance staff, and is easy to back
    up. The trade-off is that it is not designed for many kiosks
    writing at once; a shared database would be needed for that.

    The header row is written only when the file is new or empty.
    Opening in append mode ("a") means earlier records are never
    overwritten.

    Args:
        details  (dict): Output of VoucherScreen.transaction_details()
                         (or the same keys built by a test).
        log_path (str) : Full path of the CSV file.

    Raises:
        OSError: If the file cannot be written. The caller decides how
                 to tell the user; the voucher is still valid.
    """
    rows = details["breakdown"]["rows"]
    counts = {row["key"]: row["count"] for row in rows}
    issue_time = details["issue_time"]

    record = {
        "reference":        details["reference"],
        "date":             issue_time.strftime("%Y-%m-%d"),
        "time":             issue_time.strftime("%H:%M:%S"),
        "boarding_zone":    details["start_name"],
        "destination_zone": details["dest_name"],
        "zones_travelled":  details["zones"],
        "adults":           counts["adult"],
        "children":         counts["child"],
        "seniors":          counts["senior"],
        "students":         counts["student"],
        "total_travellers": details["breakdown"]["total_pax"],
        "total_cents":      details["breakdown"]["total_cents"],
        "payment_method":   details["payment"],
    }

    is_new = (not os.path.exists(log_path)
              or os.path.getsize(log_path) == 0)

    # newline="" stops the csv module adding blank lines on Windows
    with open(log_path, "a", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=TRANSACTION_FIELDS)
        if is_new:
            writer.writeheader()
        writer.writerow(record)


def summarise_sales(log_path: str = TRANSACTION_LOG_FILE,
                    on_date: str = None) -> dict:
    """
    [ENH-4] Summarise the transaction log for one day.

    Rows that cannot be read (for example after someone edits the file
    by hand) are counted as skipped rather than stopping the summary.

    Args:
        log_path (str): Full path of the CSV file.
        on_date  (str): Date as "YYYY-MM-DD". Defaults to today.

    Returns:
        dict: vouchers, travellers, total_cents, by_payment (dict of
              method -> number of vouchers) and skipped (int).
    """
    on_date = on_date or datetime.now().strftime("%Y-%m-%d")
    summary = {
        "date": on_date, "vouchers": 0, "travellers": 0,
        "total_cents": 0, "by_payment": {}, "skipped": 0,
    }

    if not os.path.exists(log_path):
        return summary

    with open(log_path, newline="", encoding="utf-8") as handle:
        for row in csv.DictReader(handle):
            if row.get("date") != on_date:
                continue
            try:
                travellers = int(row["total_travellers"])
                cents = int(row["total_cents"])
            except (KeyError, TypeError, ValueError):
                summary["skipped"] += 1
                continue

            summary["vouchers"] += 1
            summary["travellers"] += travellers
            summary["total_cents"] += cents
            method = row.get("payment_method") or "UNKNOWN"
            summary["by_payment"][method] = (
                summary["by_payment"].get(method, 0) + 1
            )

    return summary


# ===========================================================================
# MAIN APPLICATION CLASS (Controller)
# ===========================================================================

class CTATicketingApp(tk.Tk):
    """
    Root application window for the CTA Automated Ticketing System.

    Inherits from tk.Tk; acts as the central controller using the
    Frame-stacking navigation pattern. A shared 'state' dictionary
    carries user selections (zones, travellers, payment) between screens.

    Programming Paradigm: Event-driven + OOP.
    """

    def __init__(self):
        """Initialise the main window, shared state, and all screens."""
        super().__init__()

        self.title(
            "CTA \u2013 Centrala Transport Authority | Ticketing System"
        )
        self.geometry("900x680")
        self.resizable(True, True)
        self.configure(bg=COLOUR_BG)
        self.minsize(800, 600)

        # Shared state carried across all screens
        self.state = {
            "start_zone":       None,   # Integer zone number (1-3)
            "destination_zone": None,   # Integer zone number (1-3)
            "travellers": {
                "adult":   0,
                "child":   0,
                "senior":  0,
                "student": 0,
            },
            "payment_method":   None,   # "card" | "cash" | "paypal"
            "issue_time":       None,   # datetime, fixed on payment
            "reference":        None,   # unique voucher reference
        }

        # Container – all frames are stacked here
        container = tk.Frame(self, bg=COLOUR_BG)
        container.pack(fill="both", expand=True)
        container.grid_rowconfigure(0, weight=1)
        container.grid_columnconfigure(0, weight=1)

        # Instantiate all screens once at startup
        self.frames = {}
        for FrameClass in (
            WelcomeScreen,
            ZoneSelectionScreen,
            TravellerScreen,
            PaymentScreen,
            VoucherScreen,
        ):
            frame = FrameClass(container, self)
            self.frames[FrameClass.__name__] = frame
            frame.grid(row=0, column=0, sticky="nsew")

        # Defensive start-up check of the reference data (Appendix 1).
        # If a station has been typed into the wrong zone, the operator
        # is warned before any traveller relies on the stations board.
        data_errors = validate_reference_data()
        if data_errors:
            messagebox.showerror(
                "Station Data Error",
                "The station reference data does not match the "
                "Centrala Underground map:\n\n" + "\n".join(data_errors)
            )

        # [ENH-6] Keyboard shortcuts. Bound on the main window only, so
        # Enter and Escape inside a payment dialog are not affected.
        # Each screen decides what the key does via on_return() and
        # on_escape(); a screen without the method ignores the key.
        self.current_frame = None
        self.bind("<Return>", lambda event: self._dispatch_key("on_return"))
        self.bind("<Escape>", lambda event: self._dispatch_key("on_escape"))

        # [ENH-5] Kiosk idle timeout. Any key press, click or mouse
        # movement restarts the countdown.
        self._idle_job = None
        for sequence in ("<Any-KeyPress>", "<Any-ButtonPress>", "<Motion>"):
            self.bind_all(sequence, self._restart_idle_timer, add="+")
        self._restart_idle_timer()

        self.show_frame("WelcomeScreen")

    # -----------------------------------------------------------------------
    # [ENH-6] Keyboard shortcut dispatch
    # -----------------------------------------------------------------------

    def _dispatch_key(self, method_name: str):
        """
        Pass Enter / Escape to the screen currently on display.

        Args:
            method_name (str): "on_return" or "on_escape".
        """
        frame = self.frames.get(self.current_frame)
        handler = getattr(frame, method_name, None)
        if handler is not None:
            handler()

    # -----------------------------------------------------------------------
    # [ENH-5] Kiosk idle timeout
    # -----------------------------------------------------------------------

    def _restart_idle_timer(self, _event=None):
        """Cancel the pending timeout (if any) and start a new one."""
        if self._idle_job is not None:
            self.after_cancel(self._idle_job)
        self._idle_job = self.after(IDLE_TIMEOUT_MS, self._on_idle_timeout)

    def _payment_dialog_open(self) -> bool:
        """
        Return True if a payment dialog (or any pop-up window) is open.

        The timeout must not reset the journey underneath an open
        dialog, because the traveller may be part-way through paying.
        """
        return any(
            isinstance(widget, tk.Toplevel)
            for frame in self.frames.values()
            for widget in frame.winfo_children()
        )

    def _on_idle_timeout(self):
        """
        Return to the stations board after a period of inactivity.

        Nothing happens if the board is already showing or a dialog is
        open; the timer simply starts again. A completed voucher has
        already been recorded in the transaction log, so returning from
        the voucher screen loses no data.
        """
        self._idle_job = None
        if (self.current_frame == "WelcomeScreen"
                or self._payment_dialog_open()):
            self._restart_idle_timer()
            return

        self.reset_state()
        self.show_frame("WelcomeScreen")
        self._restart_idle_timer()

    def complete_payment(self, method: str):
        """
        Record a confirmed payment and open the voucher.

        Called by every payment dialog. The issue time and reference
        are fixed HERE, once per transaction, so the on-screen voucher,
        the printed text and the PDF all show identical values
        (IQA October 2026, AC 4.2).

        Args:
            method (str): "card", "cash" or "paypal".
        """
        # Defensive check: a voucher must never be issued without both
        # zones. (Found during automated testing: if the journey has
        # been cleared, e.g. by the idle timeout, the payment is
        # refused and the traveller is returned to the stations board.)
        if not (self.state["start_zone"]
                and self.state["destination_zone"]):
            logger.error("Payment refused: journey zones missing.")
            messagebox.showerror(
                "Journey Expired",
                "Your journey details were cleared, so no voucher was "
                "issued. Please start again."
            )
            self.reset_state()
            self.show_frame("WelcomeScreen")
            return

        issue_time = datetime.now()
        self.state["payment_method"] = method
        self.state["issue_time"] = issue_time
        self.state["reference"] = generate_reference(issue_time)
        self.show_frame("VoucherScreen")

        # [ENH-3] Record the voucher in the transaction log. A failure
        # here (for example the CSV is open in Excel and locked) must
        # not stop the traveller getting their voucher, so the error is
        # logged and shown as a warning instead.
        details = self.frames["VoucherScreen"].transaction_details()
        try:
            record_transaction(details)
        except OSError as exc:
            logger.error("Could not write transaction %s: %s",
                         details["reference"], exc)
            messagebox.showwarning(
                "Transaction Log",
                "Your voucher is valid, but it could not be saved to "
                "the transaction log. Please tell a member of staff."
            )

    def show_frame(self, frame_name: str):
        """
        Bring the named frame to the foreground.

        Args:
            frame_name (str): Key in self.frames dict (class name).
        """
        frame = self.frames[frame_name]
        self.current_frame = frame_name   # [ENH-5] / [ENH-6]
        if hasattr(frame, "on_show"):
            frame.on_show()
        frame.tkraise()

    def reset_state(self):
        """
        Reset everything for a new ticket purchase.

        Two things are reset (IQA October 2026, AC 3.1 / 4.2):
          1. The shared state dictionary (zones, travellers, payment,
             issue time and reference).
          2. The INPUT VARIABLES held by each screen: the zone radio
             buttons and the traveller entry fields.

        Version 3.5 reset only (1). The radio buttons and entry fields
        kept their old values, and pressing Continue copied them back
        into the state, so the previous journey leaked into the next
        transaction. Each screen now exposes reset_inputs(), and this
        method calls it on every screen that has one.
        """
        self.state["start_zone"] = None
        self.state["destination_zone"] = None
        self.state["payment_method"] = None
        self.state["issue_time"] = None
        self.state["reference"] = None
        # A new dictionary is assigned rather than editing the old one,
        # so no screen can still hold a reference to the old counts.
        self.state["travellers"] = {
            t_type["key"]: 0 for t_type in TRAVELLER_TYPES
        }

        for frame in self.frames.values():
            if hasattr(frame, "reset_inputs"):
                frame.reset_inputs()


# ===========================================================================
# SCREEN 1 – WELCOME / STATION BOARD
# ===========================================================================

class WelcomeScreen(tk.Frame):
    """
    Screen 1 – Centrala Underground Station Board.

    Displays all zones and their stations in a table (Appendix 2
    requirement) and provides the entry button to begin ticket purchase.
    """

    def __init__(self, parent, controller):
        super().__init__(parent, bg=COLOUR_BG)
        self.controller = controller
        self._build_header()
        self._build_station_board()
        self._build_footer()

    def _build_header(self):
        """Construct the top banner with CTA branding."""
        header = tk.Frame(self, bg=COLOUR_ACCENT, pady=12)
        header.pack(fill="x")

        tk.Label(
            header,
            text="\U0001f687  CENTRALA TRANSPORT AUTHORITY",
            font=FONT_TITLE, bg=COLOUR_ACCENT, fg=COLOUR_BG
        ).pack()

        tk.Label(
            header,
            text="Centrala Underground – Automated Ticketing System",
            font=FONT_SUBHEADING, bg=COLOUR_ACCENT, fg=COLOUR_BG
        ).pack()

    def _build_station_board(self):
        """
        Construct the station board table.

        Uses ttk.Treeview to display zones as column headers with
        stations listed alphabetically beneath (Appendix 2 requirement).
        """
        tk.Label(
            self,
            text="\U0001f4cb  STATIONS BOARD \u2013 "
                 "CENTRALA UNDERGROUND",
            font=FONT_HEADING, bg=COLOUR_BG, fg=COLOUR_ACCENT
        ).pack(pady=(16, 6))

        table_frame = tk.Frame(
            self, bg=COLOUR_PANEL, bd=2, relief="ridge"
        )
        table_frame.pack(padx=30, pady=6, fill="both", expand=True)

        # Column names derived from zone names, with the station count
        # shown so the traveller (and the tester) can see at a glance
        # that the board matches Appendix 1 (10 / 12 / 14).
        columns = [
            f"Zone {z} \u2013 {ZONES[z]['name']} "
            f"({len(ZONES[z]['stations'])})"
            for z in sorted(ZONES.keys())
        ]

        style = ttk.Style()
        style.theme_use("default")
        style.configure(
            "Board.Treeview",
            background=COLOUR_PANEL,
            foreground=COLOUR_WHITE,
            fieldbackground=COLOUR_PANEL,
            font=FONT_BODY,
            rowheight=24,
        )
        style.configure(
            "Board.Treeview.Heading",
            background=COLOUR_BG,
            foreground=COLOUR_ACCENT,
            font=FONT_SUBHEADING,
        )
        style.map(
            "Board.Treeview",
            background=[("selected", COLOUR_ACCENT)]
        )

        tree = ttk.Treeview(
            table_frame,
            columns=columns,
            show="headings",
            style="Board.Treeview",
            height=16,
        )

        col_width = 240
        for col in columns:
            tree.heading(col, text=col)
            tree.column(col, width=col_width, anchor="center")

        # sorted() guarantees the alphabetical order Appendix 2 asks for,
        # even if the ZONES lists are edited later.
        board = {z: sorted(ZONES[z]["stations"]) for z in ZONES}

        # Pad shorter zone station lists with empty strings
        max_rows = max(len(stations) for stations in board.values())
        for row_idx in range(max_rows):
            row_data = [
                (board[z][row_idx] if row_idx < len(board[z]) else "")
                for z in sorted(board.keys())
            ]
            tag = "even" if row_idx % 2 == 0 else "odd"
            tree.insert("", "end", values=row_data, tags=(tag,))

        tree.tag_configure("even", background=COLOUR_PANEL)
        tree.tag_configure("odd",  background=COLOUR_BG)

        scrollbar = ttk.Scrollbar(
            table_frame, orient="vertical", command=tree.yview
        )
        tree.configure(yscrollcommand=scrollbar.set)
        tree.pack(side="left", fill="both", expand=True, padx=8, pady=8)
        scrollbar.pack(side="right", fill="y", pady=8)

    def _build_footer(self):
        """Construct the footer with the 'Purchase Ticket' button."""
        footer = tk.Frame(self, bg=COLOUR_BG, pady=12)
        footer.pack(fill="x")

        tk.Button(
            footer,
            text="\U0001f3ab  Purchase a Ticket  \u2192",
            font=FONT_HEADING,
            bg=COLOUR_BTN, fg=COLOUR_BTN_TEXT,
            activebackground=COLOUR_ACCENT,
            relief="flat", padx=20, pady=10, cursor="hand2",
            command=lambda: self.controller.show_frame(
                "ZoneSelectionScreen"
            )
        ).pack()

        tk.Label(
            footer,
            text="Select your journey zones on the next screen  "
                 "(or press Enter)",
            font=FONT_SMALL, bg=COLOUR_BG, fg=COLOUR_LIGHT
        ).pack(pady=2)

        # [ENH-4] Small, low-contrast staff button in the corner, so
        # travellers are not distracted by it. place() positions it
        # without changing the layout of the main button above.
        tk.Button(
            footer, text="Staff: today's sales",
            font=FONT_SMALL, bg=COLOUR_BG, fg=COLOUR_LIGHT,
            relief="flat", cursor="hand2",
            command=self._show_sales_summary
        ).place(relx=1.0, rely=1.0, anchor="se", x=-10)

    def on_return(self):
        """[ENH-6] Enter on the stations board starts a purchase."""
        self.controller.show_frame("ZoneSelectionScreen")

    def _show_sales_summary(self):
        """
        [ENH-4] Show today's totals from the transaction log.

        Reads the CSV each time, so the figures include every voucher
        issued today, even in earlier sessions of the program.
        """
        try:
            summary = summarise_sales()
        except OSError as exc:
            logger.error("Could not read transaction log: %s", exc)
            messagebox.showerror(
                "Sales Summary", f"The transaction log could not be "
                f"read:\n{exc}"
            )
            return

        if summary["vouchers"] == 0:
            messagebox.showinfo(
                "Sales Summary",
                f"No vouchers have been issued today ({summary['date']})."
            )
            return

        methods = "\n".join(
            f"    {method.title():<8} {count} voucher(s)"
            for method, count in sorted(summary["by_payment"].items())
        )
        text = (
            f"Date:        {summary['date']}\n"
            f"Vouchers:    {summary['vouchers']}\n"
            f"Travellers:  {summary['travellers']}\n"
            f"Takings:     {cents_to_display(summary['total_cents'])}\n\n"
            f"By payment method:\n{methods}"
        )
        if summary["skipped"]:
            text += (
                f"\n\n{summary['skipped']} unreadable row(s) were "
                f"skipped. Check the log file."
            )
        messagebox.showinfo("Sales Summary", text)


# ===========================================================================
# SCREEN 2 – ZONE SELECTION
# ===========================================================================

class ZoneSelectionScreen(tk.Frame):
    """
    Screen 2 – Journey Zone Selection.

    Travellers select start zone and destination zone using radio buttons
    (Appendix 2: 1 = Central, 2 = Midtown, 3 = Downtown).
    """

    def __init__(self, parent, controller):
        super().__init__(parent, bg=COLOUR_BG)
        self.controller = controller
        self.start_var = tk.IntVar(value=0)   # 0 = not selected
        self.destination_var = tk.IntVar(value=0)   # 0 = not selected
        self._build_ui()

    def reset_inputs(self):
        """
        Clear both zone selections for a new ticket.

        Called by CTATicketingApp.reset_state(). Setting the variables
        back to 0 deselects every radio button, so the traveller must
        choose the zones again (IQA October 2026, AC 3.1).
        """
        self.start_var.set(0)
        self.destination_var.set(0)
        self._update_info()
        # [ENH-1] Clear the station finder as well
        self.finder_var.set("")
        self._found_zone = None
        self.finder_result.config(text="", fg=COLOUR_LIGHT)
        self._set_finder_buttons("disabled")

    # -----------------------------------------------------------------------
    # [ENH-6] Keyboard shortcuts
    # -----------------------------------------------------------------------

    def on_return(self):
        """
        Enter = Continue, except while typing in the station finder,
        where Enter runs the search instead.
        """
        if self.focus_get() is self.finder_entry:
            self._find_station()
        else:
            self._on_continue()

    def on_escape(self):
        """Escape = Back to the stations board."""
        self.controller.show_frame("WelcomeScreen")

    # -----------------------------------------------------------------------
    # [ENH-1] Station finder
    # -----------------------------------------------------------------------

    def _build_station_finder(self):
        """
        Build the 'Find your station' bar.

        The brief requires travellers to choose a ZONE, not a station,
        and the zone menus below still work exactly as specified. The
        finder is an aid for travellers who know only their station
        name: it tells them the zone and can tick the zone for them.
        """
        bar = tk.Frame(self, bg=COLOUR_PANEL, padx=12, pady=6)
        bar.pack(padx=40, fill="x", pady=(0, 8))

        tk.Label(
            bar, text="\U0001f50d  Don't know your zone? Find your station:",
            font=FONT_SMALL, bg=COLOUR_PANEL, fg=COLOUR_WHITE
        ).pack(side="left")

        self.finder_var = tk.StringVar()
        self.finder_entry = tk.Entry(
            bar, textvariable=self.finder_var, width=14,
            font=FONT_BODY, bg=COLOUR_INPUT_BG, fg=COLOUR_WHITE,
            insertbackground=COLOUR_WHITE, relief="flat"
        )
        self.finder_entry.pack(side="left", padx=6)

        tk.Button(
            bar, text="Find", font=FONT_SMALL,
            bg=COLOUR_BTN, fg=COLOUR_BTN_TEXT, relief="flat",
            cursor="hand2", command=self._find_station
        ).pack(side="left")

        # The two "use" buttons stay disabled until a station is found,
        # so they can never select a zone from an unknown name.
        self.use_dest_btn = tk.Button(
            bar, text="Set as destination", font=FONT_SMALL,
            bg=COLOUR_BG, fg=COLOUR_WHITE, relief="flat",
            state="disabled", cursor="hand2",
            command=lambda: self._use_found_zone(self.destination_var)
        )
        self.use_dest_btn.pack(side="right", padx=(4, 0))

        self.use_start_btn = tk.Button(
            bar, text="Set as boarding", font=FONT_SMALL,
            bg=COLOUR_BG, fg=COLOUR_WHITE, relief="flat",
            state="disabled", cursor="hand2",
            command=lambda: self._use_found_zone(self.start_var)
        )
        self.use_start_btn.pack(side="right", padx=4)

        self.finder_result = tk.Label(
            self, text="", font=FONT_SMALL,
            bg=COLOUR_BG, fg=COLOUR_LIGHT
        )
        self.finder_result.pack()

        self._found_zone = None   # Zone number of the last match

    def _set_finder_buttons(self, state: str):
        """Enable or disable both 'Set as …' buttons together."""
        self.use_start_btn.config(state=state)
        self.use_dest_btn.config(state=state)

    def _find_station(self):
        """
        Search for the typed station and report its zone.

        Three outcomes:
          - exact match   : show the zone and enable the 'Set as' buttons
          - partial match : show up to five suggestions ("did you mean")
          - no match      : explain that the name was not found
        """
        typed = self.finder_var.get()
        match = find_station(typed)

        if match:
            zone_num, station = match
            self._found_zone = zone_num
            self.finder_result.config(
                text=(f"{station} is in Zone {zone_num} – "
                      f"{ZONES[zone_num]['name']}."),
                fg=COLOUR_SUCCESS
            )
            self._set_finder_buttons("normal")
            return

        self._found_zone = None
        self._set_finder_buttons("disabled")

        if not typed.strip():
            self.finder_result.config(
                text="Type a station name, e.g. Lomil.", fg=COLOUR_LIGHT
            )
            return

        suggestions = suggest_stations(typed)
        if suggestions:
            self.finder_result.config(
                text="Did you mean: " + ", ".join(suggestions) + "?",
                fg=COLOUR_ACCENT
            )
        else:
            self.finder_result.config(
                text=(f"No station called '{typed.strip()}'. Check the "
                      f"stations board."),
                fg=COLOUR_DANGER
            )

    def _use_found_zone(self, variable: tk.IntVar):
        """
        Tick the zone of the station found, as boarding or destination.

        Args:
            variable (tk.IntVar): start_var or destination_var.
        """
        if self._found_zone is not None:
            variable.set(self._found_zone)
            self._update_info()

    def _build_ui(self):
        """Construct the full zone selection UI."""
        self._add_header(
            "\U0001f689  Step 1 of 4  \u2013  "
            "Select Your Journey Zones"
        )

        tk.Label(
            self,
            text=(
                "Select your boarding zone and destination zone.\n"
                "Fares are calculated per zone crossed."
            ),
            font=FONT_BODY, bg=COLOUR_BG, fg=COLOUR_LIGHT,
            justify="center"
        ).pack(pady=(0, 6))

        self._build_station_finder()      # [ENH-1]

        # Two-column layout
        selector_row = tk.Frame(self, bg=COLOUR_BG)
        selector_row.pack(padx=40, fill="x", expand=False)

        self._build_zone_picker(
            parent=selector_row,
            title="\U0001f689  BOARDING ZONE",
            subtitle="Where are you starting?",
            variable=self.start_var,
        )

        tk.Label(
            selector_row, text="\u2192",
            font=("Georgia", 32, "bold"),
            bg=COLOUR_BG, fg=COLOUR_ACCENT
        ).pack(side="left", padx=20, pady=60)

        self._build_zone_picker(
            parent=selector_row,
            title="\U0001f3c1  DESTINATION ZONE",
            subtitle="Where are you going?",
            variable=self.destination_var,
        )

        self.info_label = tk.Label(
            self, text="",
            font=FONT_SUBHEADING, bg=COLOUR_BG, fg=COLOUR_ACCENT
        )
        self.info_label.pack(pady=10)

        self._add_nav_buttons()

    def _build_zone_picker(
        self, parent, title: str, subtitle: str,
        variable: tk.IntVar
    ):
        """
        Build a labelled radio-button panel for zone selection.

        Args:
            parent   : Parent widget to pack into.
            title    : Bold section title.
            subtitle : Muted descriptive text below the title.
            variable : tk.IntVar bound to the radio button group.
        """
        card = tk.Frame(
            parent, bg=COLOUR_PANEL, bd=1, relief="ridge",
            padx=20, pady=16
        )
        card.pack(side="left", fill="both", expand=True)

        tk.Label(
            card, text=title,
            font=FONT_HEADING, bg=COLOUR_PANEL, fg=COLOUR_WHITE
        ).pack(anchor="w")

        tk.Label(
            card, text=subtitle,
            font=FONT_SMALL, bg=COLOUR_PANEL, fg=COLOUR_LIGHT
        ).pack(anchor="w", pady=(0, 10))

        for zone_num in sorted(ZONES.keys()):
            zone = ZONES[zone_num]

            tk.Radiobutton(
                card,
                text=f"  {zone_num}  \u2013  {zone['name']} Zone",
                variable=variable,
                value=zone_num,
                font=FONT_SUBHEADING,
                bg=COLOUR_PANEL, fg=COLOUR_WHITE,
                selectcolor=COLOUR_BG,
                activebackground=COLOUR_PANEL,
                activeforeground=COLOUR_ACCENT,
                cursor="hand2",
                command=self._update_info
            ).pack(anchor="w", pady=4)

            # Station preview under each zone option. It reads the same
            # ZONES data as the stations board, so both screens always
            # show identical allocations (IQA October 2026, AC 2.2).
            station_list = ", ".join(sorted(zone["stations"]))
            tk.Label(
                card,
                text=f"       Stations: {station_list}",
                font=FONT_SMALL, bg=COLOUR_PANEL, fg=COLOUR_LIGHT,
                wraplength=300, justify="left"
            ).pack(anchor="w", padx=8, pady=(0, 6))

    def _update_info(self):
        """Update the dynamic zones info label on any selection."""
        start = self.start_var.get()
        dest = self.destination_var.get()

        if start != 0 and dest != 0:
            zones = calculate_zones_travelled(start, dest)
            s_name = ZONES[start]["name"]
            d_name = ZONES[dest]["name"]
            self.info_label.config(
                text=(
                    f"Journey: {s_name} Zone  \u2192  {d_name} Zone"
                    f"  |  Zones Travelled: {zones}"
                )
            )
        else:
            self.info_label.config(text="")

    def _add_header(self, title: str):
        """Add a styled gold header bar."""
        header = tk.Frame(self, bg=COLOUR_ACCENT, pady=10)
        header.pack(fill="x")
        tk.Label(
            header, text=title,
            font=FONT_HEADING, bg=COLOUR_ACCENT, fg=COLOUR_BG
        ).pack()

    def _add_nav_buttons(self):
        """Add Back and Continue navigation buttons."""
        nav = tk.Frame(self, bg=COLOUR_BG, pady=16)
        nav.pack(fill="x")

        tk.Button(
            nav, text="\u2190 Back",
            font=FONT_BODY, bg=COLOUR_PANEL, fg=COLOUR_LIGHT,
            relief="flat", padx=14, pady=8, cursor="hand2",
            command=lambda: self.controller.show_frame("WelcomeScreen")
        ).pack(side="left", padx=30)

        tk.Button(
            nav, text="Continue \u2192",
            font=FONT_HEADING, bg=COLOUR_BTN, fg=COLOUR_BTN_TEXT,
            relief="flat", padx=20, pady=8, cursor="hand2",
            command=self._on_continue
        ).pack(side="right", padx=30)

    def _on_continue(self):
        """Validate zone selections and navigate to traveller screen."""
        start = self.start_var.get()
        dest = self.destination_var.get()

        if start == 0:
            messagebox.showwarning(
                "Missing Selection",
                "Please select a BOARDING zone before continuing."
            )
            return

        if dest == 0:
            messagebox.showwarning(
                "Missing Selection",
                "Please select a DESTINATION zone before continuing."
            )
            return

        self.controller.state["start_zone"] = start
        self.controller.state["destination_zone"] = dest
        self.controller.show_frame("TravellerScreen")


# ===========================================================================
# SCREEN 3 – TRAVELLER COUNT INPUT
# ===========================================================================

class TravellerScreen(tk.Frame):
    """
    Screen 3 – Traveller Count Entry.

    Users enter the number of Adults, Children, Seniors, and Students.
    At least one traveller must be entered (business rule validation).
    """

    def __init__(self, parent, controller):
        super().__init__(parent, bg=COLOUR_BG)
        self.controller = controller
        self.inputs = {}   # StringVars keyed by traveller type
        self._build_ui()

    def reset_inputs(self):
        """
        Set every traveller entry field back to "0" for a new ticket.

        Called by CTATicketingApp.reset_state(). Without this the
        previous counts stayed in the fields and were submitted again
        with the next ticket (IQA October 2026, AC 3.1 / TC20).
        """
        for var in self.inputs.values():
            var.set("0")
        self.journey_label.config(text="")
        self.live_total_label.config(text="")     # [ENH-2]

    def on_show(self):
        """Refresh the journey summary when this screen is revisited."""
        state = self.controller.state
        self._update_live_total()                 # [ENH-2]
        if state["start_zone"] and state["destination_zone"]:
            s = ZONES[state["start_zone"]]["name"]
            d = ZONES[state["destination_zone"]]["name"]
            zones = calculate_zones_travelled(
                state["start_zone"], state["destination_zone"]
            )
            self.journey_label.config(
                text=(
                    f"Journey: {s} Zone  \u2192  {d} Zone  "
                    f"({zones} zone{'s' if zones > 1 else ''} "
                    f"travelled)"
                )
            )

    def _build_ui(self):
        """Construct the traveller count entry form."""
        header = tk.Frame(self, bg=COLOUR_ACCENT, pady=10)
        header.pack(fill="x")
        tk.Label(
            header,
            text="\U0001f465  Step 2 of 4  \u2013  "
                 "Enter Number of Travellers",
            font=FONT_HEADING, bg=COLOUR_ACCENT, fg=COLOUR_BG
        ).pack()

        self.journey_label = tk.Label(
            self, text="",
            font=FONT_SUBHEADING, bg=COLOUR_BG, fg=COLOUR_ACCENT
        )
        self.journey_label.pack(pady=(10, 4))

        tk.Label(
            self,
            text=(
                "Enter 0 if there are no travellers of a particular "
                "type.\nAt least one traveller must be entered "
                f"(maximum {MAX_TRAVELLERS_PER_TYPE} per type)."
            ),
            font=FONT_BODY, bg=COLOUR_BG, fg=COLOUR_LIGHT,
            justify="center"
        ).pack(pady=(0, 12))

        cards_frame = tk.Frame(self, bg=COLOUR_BG)
        cards_frame.pack(padx=60, fill="x")

        for t_type in TRAVELLER_TYPES:
            self._build_input_card(cards_frame, t_type)

        self._build_rate_table()
        self._add_nav_buttons()

    def _build_input_card(self, parent, t_type: dict):
        """
        Build a single traveller count row with +/- stepper buttons.

        Args:
            parent : Parent frame to pack into.
            t_type : Dict with 'key', 'label', 'fare' keys.
        """
        key = t_type["key"]
        label = t_type["label"]
        fare = t_type["fare"]

        var = tk.StringVar(value="0")
        self.inputs[key] = var

        card = tk.Frame(
            parent, bg=COLOUR_PANEL, pady=10, padx=16,
            bd=1, relief="ridge"
        )
        card.pack(fill="x", pady=4)

        left = tk.Frame(card, bg=COLOUR_PANEL)
        left.pack(side="left", fill="x", expand=True)

        tk.Label(
            left, text=label,
            font=FONT_SUBHEADING, bg=COLOUR_PANEL, fg=COLOUR_WHITE
        ).pack(anchor="w")

        tk.Label(
            left,
            text=f"Rate: {cents_to_display(fare)} per zone",
            font=FONT_SMALL, bg=COLOUR_PANEL, fg=COLOUR_LIGHT
        ).pack(anchor="w")

        right = tk.Frame(card, bg=COLOUR_PANEL)
        right.pack(side="right")

        tk.Button(
            right, text="\u2212",
            font=("Georgia", 14, "bold"),
            bg=COLOUR_DANGER, fg=COLOUR_WHITE,
            width=2, relief="flat", cursor="hand2",
            command=lambda v=var: self._adjust_count(v, -1)
        ).pack(side="left", padx=4)

        tk.Entry(
            right, textvariable=var,
            font=FONT_HEADING, width=4,
            justify="center",
            bg=COLOUR_INPUT_BG, fg=COLOUR_WHITE,
            insertbackground=COLOUR_WHITE,
            relief="flat"
        ).pack(side="left")

        tk.Button(
            right, text="+",
            font=("Georgia", 14, "bold"),
            bg=COLOUR_SUCCESS, fg=COLOUR_WHITE,
            width=2, relief="flat", cursor="hand2",
            command=lambda v=var: self._adjust_count(v, +1)
        ).pack(side="left", padx=4)

    def _adjust_count(self, var: tk.StringVar, delta: int):
        """
        Increment or decrement a traveller count by 'delta'.

        Clamps the value between 0 and MAX_TRAVELLERS_PER_TYPE so the
        stepper buttons can never produce an invalid count.

        Args:
            var   (tk.StringVar): Variable bound to the entry field.
            delta (int)         : +1 to increment, -1 to decrement.
        """
        current = var.get().strip()
        if not current.isdigit():
            var.set("0")
            return
        new_value = int(current) + delta
        var.set(str(min(MAX_TRAVELLERS_PER_TYPE, max(0, new_value))))

    def _build_rate_table(self):
        """Build a compact fare rate reference summary."""
        frame = tk.Frame(self, bg=COLOUR_BG, pady=8)
        frame.pack(padx=60, fill="x")

        tk.Label(
            frame, text="Fare Rate Summary",
            font=FONT_SUBHEADING, bg=COLOUR_BG, fg=COLOUR_ACCENT
        ).pack(anchor="w")

        rates_text = "  |  ".join(
            f"{t['label']}: {cents_to_display(t['fare'])}/zone"
            for t in TRAVELLER_TYPES
        )
        tk.Label(
            frame, text=rates_text,
            font=FONT_SMALL, bg=COLOUR_BG, fg=COLOUR_LIGHT
        ).pack(anchor="w")

        # [ENH-2] Live fare preview, updated on every change to a count
        self.live_total_label = tk.Label(
            frame, text="", font=FONT_SUBHEADING,
            bg=COLOUR_BG, fg=COLOUR_WHITE
        )
        self.live_total_label.pack(anchor="w", pady=(6, 0))

        # trace_add("write") calls the function whenever a value changes,
        # whether by typing or by the +/- buttons.
        for var in self.inputs.values():
            var.trace_add("write", lambda *_args: self._update_live_total())

    def _update_live_total(self):
        """
        [ENH-2] Recalculate and show the running total.

        Uses build_fare_breakdown(), the same function as the payment
        screen and the voucher, so the preview always matches the
        amount charged. While any field holds an invalid value the
        preview explains that instead of showing a wrong figure.
        """
        state = self.controller.state
        if not (state["start_zone"] and state["destination_zone"]):
            self.live_total_label.config(text="")
            return

        counts = {}
        for key, var in self.inputs.items():
            valid, value, _error = validate_positive_integer(var.get(), key)
            if not valid:
                self.live_total_label.config(
                    text="Running total: enter whole numbers from 0 to "
                         f"{MAX_TRAVELLERS_PER_TYPE} to see the fare.",
                    fg=COLOUR_DANGER
                )
                return
            counts[key] = value

        zones = calculate_zones_travelled(
            state["start_zone"], state["destination_zone"]
        )
        breakdown = build_fare_breakdown(counts, zones)
        total = cents_to_display(breakdown["total_cents"])
        pax = breakdown["total_pax"]
        self.live_total_label.config(
            text=(f"Running total: {total}  for {pax} "
                  f"traveller{'' if pax == 1 else 's'}"),
            fg=COLOUR_ACCENT if breakdown["total_pax"] else COLOUR_LIGHT
        )

    # -----------------------------------------------------------------------
    # [ENH-6] Keyboard shortcuts
    # -----------------------------------------------------------------------

    def on_return(self):
        """Enter = Proceed to Payment (the same validation applies)."""
        self._on_continue()

    def on_escape(self):
        """Escape = Back to zone selection."""
        self.controller.show_frame("ZoneSelectionScreen")

    def _add_nav_buttons(self):
        """Add Back and Proceed to Payment buttons."""
        nav = tk.Frame(self, bg=COLOUR_BG, pady=14)
        nav.pack(fill="x")

        tk.Button(
            nav, text="\u2190 Back",
            font=FONT_BODY, bg=COLOUR_PANEL, fg=COLOUR_LIGHT,
            relief="flat", padx=14, pady=8, cursor="hand2",
            command=lambda: self.controller.show_frame(
                "ZoneSelectionScreen"
            )
        ).pack(side="left", padx=30)

        tk.Button(
            nav,
            text="\U0001f4b3  Proceed to Payment \u2192",
            font=FONT_HEADING, bg=COLOUR_BTN, fg=COLOUR_BTN_TEXT,
            relief="flat", padx=20, pady=8, cursor="hand2",
            command=self._on_continue
        ).pack(side="right", padx=30)

    def _on_continue(self):
        """
        Validate inputs and navigate to the payment screen.

        Validation:
          1. Each field must be a non-negative integer.
          2. Total traveller count must be at least 1.
        """
        counts = {}
        total = 0

        for t_type in TRAVELLER_TYPES:
            key = t_type["key"]
            label = t_type["label"]
            raw = self.inputs[key].get()

            valid, value, error = validate_positive_integer(raw, label)
            if not valid:
                messagebox.showerror("Input Error", error)
                return

            counts[key] = value
            total += value

        if total == 0:
            messagebox.showwarning(
                "No Travellers",
                "Please enter at least one traveller to proceed."
            )
            return

        self.controller.state["travellers"] = counts
        self.controller.show_frame("PaymentScreen")


# ===========================================================================
# SCREEN 4 – PAYMENT METHOD SELECTION
# ===========================================================================

class PaymentScreen(tk.Frame):
    """
    Screen 4 – Payment Method Selection.

    OPTIONAL EXTENSION: payment is not required by the client brief.
    All three methods are simulations; no money is taken and no card,
    cash or account details are stored or sent anywhere.

    Presents three payment options as large clickable tiles:
      - Card   : Card-reader simulation dialog
      - Cash   : Cash-insertion simulation dialog (with change calc)
      - PayPal : PayPal login/payment simulation dialog
    """

    def __init__(self, parent, controller):
        super().__init__(parent, bg=COLOUR_BG)
        self.controller = controller
        self._total_cents = 0
        self._build_ui()

    def on_escape(self):
        """
        [ENH-6] Escape = Back to the traveller screen.

        There is deliberately no Enter shortcut here: the traveller must
        actively choose a payment method rather than pay by accident.
        """
        self.controller.show_frame("TravellerScreen")

    def on_show(self):
        """Recompute and display the fare total each time screen appears."""
        self._update_total_label()

    def _update_total_label(self):
        """Compute and display the current journey grand total."""
        state = self.controller.state
        start = state["start_zone"]
        dest = state["destination_zone"]
        travs = state["travellers"]

        if not start or not dest:
            return

        zones = calculate_zones_travelled(start, dest)
        # Same function as the voucher, so the amount charged here is
        # always the amount printed on the voucher.
        total_cents = build_fare_breakdown(travs, zones)["total_cents"]

        self.total_label.config(
            text=(
                f"Journey Total:  {cents_to_display(total_cents)}"
                f"   ({zones} zone"
                f"{'s' if zones > 1 else ''} travelled)"
            )
        )
        self._total_cents = total_cents

    def _build_ui(self):
        """Construct the payment screen layout."""
        # Header
        header = tk.Frame(self, bg=COLOUR_ACCENT, pady=10)
        header.pack(fill="x")
        tk.Label(
            header,
            text="\U0001f4b3  Step 3 of 4  \u2013  "
                 "Choose Payment Method",
            font=FONT_HEADING, bg=COLOUR_ACCENT, fg=COLOUR_BG
        ).pack()

        # Total display
        self.total_label = tk.Label(
            self, text="",
            font=("Georgia", 15, "bold"), bg=COLOUR_BG, fg=COLOUR_ACCENT
        )
        self.total_label.pack(pady=(20, 8))

        tk.Label(
            self,
            text="Please select how you would like to pay:",
            font=FONT_BODY, bg=COLOUR_BG, fg=COLOUR_LIGHT
        ).pack(pady=(0, 20))

        # Payment tiles
        btn_row = tk.Frame(self, bg=COLOUR_BG)
        btn_row.pack(padx=40, pady=10)

        self._make_tile(
            parent=btn_row,
            icon="\U0001f4b3",
            label="Pay by Card",
            sub="Insert your debit or credit card",
            bg_col=COLOUR_CARD,
            border_col=COLOUR_ACCENT,
            command=self._open_card_dialog
        )

        self._make_tile(
            parent=btn_row,
            icon="\U0001f4b5",
            label="Pay with Cash",
            sub="Insert cash (amounts in cents)",
            bg_col=COLOUR_CASH,
            border_col="#0F5C30",
            command=self._open_cash_dialog
        )

        self._make_tile(
            parent=btn_row,
            icon="\U0001f170",
            label="Pay via PayPal",
            sub="Use your PayPal account",
            bg_col=COLOUR_PAYPAL,
            border_col=COLOUR_PAYPAL2,
            command=self._open_paypal_dialog
        )

        # Back button
        nav = tk.Frame(self, bg=COLOUR_BG, pady=20)
        nav.pack(fill="x")
        tk.Button(
            nav, text="\u2190 Back",
            font=FONT_BODY, bg=COLOUR_PANEL, fg=COLOUR_LIGHT,
            relief="flat", padx=14, pady=8, cursor="hand2",
            command=lambda: self.controller.show_frame("TravellerScreen")
        ).pack(side="left", padx=30)

    def _make_tile(
        self, parent, icon, label, sub,
        bg_col, border_col, command
    ):
        """
        Create a large clickable payment method tile.

        Args:
            parent     : Parent widget.
            icon       : Emoji string for the payment method.
            label      : Primary tile label.
            sub        : Descriptive sub-text.
            bg_col     : Tile background colour.
            border_col : Accent border colour.
            command    : Callback invoked when tile is clicked.
        """
        outer = tk.Frame(parent, bg=border_col, cursor="hand2")
        outer.pack(side="left", padx=16, pady=6, ipadx=3, ipady=3)

        inner = tk.Frame(outer, bg=bg_col, padx=26, pady=22,
                         cursor="hand2")
        inner.pack()

        lbl_icon = tk.Label(
            inner, text=icon,
            font=("Calibri", 36), bg=bg_col, fg=COLOUR_WHITE
        )
        lbl_icon.pack()

        lbl_main = tk.Label(
            inner, text=label,
            font=("Georgia", 13, "bold"),
            bg=bg_col, fg=COLOUR_WHITE
        )
        lbl_main.pack(pady=(6, 2))

        lbl_sub = tk.Label(
            inner, text=sub,
            font=FONT_SMALL, bg=bg_col, fg="#CCCCCC"
        )
        lbl_sub.pack()

        # Bind click to every widget so the whole tile is clickable
        for widget in (outer, inner, lbl_icon, lbl_main, lbl_sub):
            widget.bind("<Button-1>", lambda e, cmd=command: cmd())

    # -----------------------------------------------------------------------
    # Dialog launchers
    # -----------------------------------------------------------------------

    def _open_card_dialog(self):
        """Open the card payment simulation dialog."""
        CardPaymentDialog(self, self.controller, self._total_cents)

    def _open_cash_dialog(self):
        """Open the cash insertion simulation dialog."""
        CashPaymentDialog(self, self.controller, self._total_cents)

    def _open_paypal_dialog(self):
        """Open the PayPal payment simulation dialog."""
        PayPalPaymentDialog(self, self.controller, self._total_cents)


# ===========================================================================
# PAYMENT DIALOG – CARD
# ===========================================================================

class CardPaymentDialog(tk.Toplevel):
    """
    Modal dialog simulating a card-reader terminal.

    Shows a canvas card-reader graphic and runs a progress animation
    before confirming payment and navigating to the receipt screen.
    """

    def __init__(self, parent, controller, total_cents: int):
        super().__init__(parent)
        self.controller = controller
        self.total_cents = total_cents

        self.title("Card Payment \u2013 CTA Ticketing")
        self.geometry("440x500")
        self.resizable(False, False)
        self.configure(bg=COLOUR_BG)
        self.grab_set()
        self._build_ui()

    def _build_ui(self):
        """Construct the card payment dialog layout."""
        header = tk.Frame(self, bg=COLOUR_CARD, pady=14)
        header.pack(fill="x")
        tk.Label(
            header, text="\U0001f4b3  Card Payment",
            font=FONT_HEADING, bg=COLOUR_CARD, fg=COLOUR_WHITE
        ).pack()

        tk.Label(
            self,
            text=f"Amount Due:  {cents_to_display(self.total_cents)}",
            font=("Georgia", 18, "bold"),
            bg=COLOUR_BG, fg=COLOUR_ACCENT
        ).pack(pady=(22, 6))

        # Canvas card-reader graphic
        canvas = tk.Canvas(
            self, width=260, height=160,
            bg=COLOUR_BG, highlightthickness=0
        )
        canvas.pack(pady=8)
        canvas.create_rectangle(
            30, 10, 230, 140,
            fill="#2C3E50", outline=COLOUR_ACCENT, width=2
        )
        canvas.create_rectangle(
            50, 25, 210, 78,
            fill="#1ABC9C", outline="#148F77", width=1
        )
        canvas.create_text(
            130, 51, text="INSERT CARD",
            font=("Courier New", 11, "bold"), fill=COLOUR_WHITE
        )
        canvas.create_rectangle(
            50, 108, 210, 122,
            fill="#1A252F", outline=COLOUR_ACCENT, width=2
        )
        canvas.create_text(
            130, 133, text="\u25b2  Insert card here  \u25b2",
            font=("Calibri", 8), fill=COLOUR_LIGHT
        )
        canvas.create_text(
            242, 74, text="))))",
            font=("Calibri", 17, "bold"), fill=COLOUR_ACCENT
        )

        self.status_label = tk.Label(
            self,
            text="Please insert or tap your card on the reader.",
            font=FONT_BODY, bg=COLOUR_BG, fg=COLOUR_LIGHT,
            wraplength=380, justify="center"
        )
        self.status_label.pack(pady=(4, 10))

        self.progress = ttk.Progressbar(
            self, orient="horizontal", length=300, mode="determinate"
        )
        self.progress.pack(pady=4)

        btn_frame = tk.Frame(self, bg=COLOUR_BG)
        btn_frame.pack(pady=14)

        self.pay_btn = tk.Button(
            btn_frame,
            text="\u2705  Confirm Card Payment",
            font=FONT_SUBHEADING,
            bg=COLOUR_SUCCESS, fg=COLOUR_WHITE,
            relief="flat", padx=16, pady=8, cursor="hand2",
            command=self._process_payment
        )
        self.pay_btn.pack(side="left", padx=8)

        tk.Button(
            btn_frame, text="\u2716  Cancel",
            font=FONT_SMALL,
            bg=COLOUR_DANGER, fg=COLOUR_WHITE,
            relief="flat", padx=12, pady=8, cursor="hand2",
            command=self.destroy
        ).pack(side="left", padx=8)

    def _process_payment(self):
        """Start the animated card processing sequence."""
        self.pay_btn.config(state="disabled")
        self.status_label.config(
            text="Processing\u2026 please do not remove your card.",
            fg=COLOUR_ACCENT
        )
        self._animate(0)

    def _animate(self, step: int):
        """Advance the progress bar then confirm payment."""
        self.progress["value"] = step * 10
        if step < 10:
            self.after(120, lambda: self._animate(step + 1))
        else:
            self.status_label.config(
                text="\u2705  Payment approved!",
                fg=COLOUR_SUCCESS
            )
            # 1.5 s pause so the "approved" message can be read.
            # (v3.5 used 15000 ms by mistake, a 15-second wait.)
            self.after(1500, self._go_to_voucher)

    def _go_to_voucher(self):
        """Close the dialog and record the payment as 'card'."""
        self.destroy()
        self.controller.complete_payment("card")


# ===========================================================================
# PAYMENT DIALOG – CASH
# ===========================================================================

class CashPaymentDialog(tk.Toplevel):
    """
    Modal dialog simulating a cash-insertion vending terminal.

    NOTE: Cash payment is an implementation EXTENSION beyond the client's
    minimum brief. It does not reinterpret the fare specification: every
    amount inserted, remaining and returned as change is an integer number
    of CENTS, the unit stated in Appendix 2. The denomination values below
    are neutral cent amounts and do not represent any national currency.

    Denomination buttons let the user click to insert cash in cents.
    A live Inserted / Remaining display updates on each click.
    The Confirm button enables once the inserted total covers the fare.
    """

    # Neutral cent denominations (implementation extension – see above)
    DENOMINATIONS = [
        ("5",      5),    ("10",     10),   ("25",     25),
        ("50",     50),   ("100",    100),  ("500",    500),
        ("1000",   1000), ("2000",   2000), ("5000",   5000),
        ("10000",  10000),
    ]

    def __init__(self, parent, controller, total_cents: int):
        super().__init__(parent)
        self.controller = controller
        self.total_cents = total_cents
        self._inserted = 0

        self.title("Cash Payment \u2013 CTA Ticketing")
        self.geometry("520x580")
        self.resizable(False, False)
        self.configure(bg=COLOUR_BG)
        self.grab_set()
        self._build_ui()

    def _build_ui(self):
        """Construct the cash insertion dialog layout."""
        header = tk.Frame(self, bg=COLOUR_CASH, pady=12)
        header.pack(fill="x")
        tk.Label(
            header, text="\U0001f4b5  Cash Payment",
            font=FONT_HEADING, bg=COLOUR_CASH, fg=COLOUR_WHITE
        ).pack()

        tk.Label(
            self,
            text=f"Amount Due:  {cents_to_display(self.total_cents)}",
            font=("Georgia", 17, "bold"),
            bg=COLOUR_BG, fg=COLOUR_ACCENT
        ).pack(pady=(14, 4))

        # Live inserted / remaining display
        info_frame = tk.Frame(self, bg=COLOUR_PANEL, padx=20, pady=10)
        info_frame.pack(padx=30, fill="x", pady=4)

        self.inserted_label = tk.Label(
            info_frame,
            text=f"Inserted: {cents_to_display(self._inserted)}",
            font=FONT_SUBHEADING, bg=COLOUR_PANEL, fg=COLOUR_WHITE
        )
        self.inserted_label.pack(side="left", expand=True)

        self.remaining_label = tk.Label(
            info_frame,
            text=f"Remaining: {cents_to_display(self.total_cents)}",
            font=FONT_SUBHEADING, bg=COLOUR_PANEL, fg=COLOUR_DANGER
        )
        self.remaining_label.pack(side="right", expand=True)

        # Cash machine graphic
        canvas = tk.Canvas(
            self, width=200, height=78,
            bg=COLOUR_BG, highlightthickness=0
        )
        canvas.pack(pady=4)
        canvas.create_rectangle(
            20, 8, 180, 66,
            fill="#2C3E50", outline=COLOUR_CASH, width=2
        )
        canvas.create_rectangle(
            40, 34, 160, 48,
            fill="#1A252F", outline=COLOUR_CASH, width=2
        )
        canvas.create_text(
            100, 22, text="INSERT MONEY",
            font=("Courier New", 9, "bold"), fill=COLOUR_WHITE
        )
        canvas.create_text(
            100, 58, text="\u25b2  Cash slot  \u25b2",
            font=("Calibri", 8), fill=COLOUR_LIGHT
        )

        tk.Label(
            self, text="Tap a denomination (in cents) to insert:",
            font=FONT_BODY, bg=COLOUR_BG, fg=COLOUR_LIGHT
        ).pack(pady=(4, 2))

        # Denomination buttons grid (6 columns)
        denom_frame = tk.Frame(self, bg=COLOUR_BG)
        denom_frame.pack(padx=30)

        for idx, (label, value) in enumerate(self.DENOMINATIONS):
            tk.Button(
                denom_frame, text=label,
                font=FONT_SUBHEADING, width=6,
                bg=COLOUR_CASH, fg=COLOUR_WHITE,
                relief="flat", cursor="hand2",
                command=lambda v=value: self._insert(v)
            ).grid(row=idx // 5, column=idx % 5, padx=4, pady=4)

        self.status_label = tk.Label(
            self,
            text="Insert cash (in cents) using the buttons above.",
            font=FONT_BODY, bg=COLOUR_BG, fg=COLOUR_LIGHT,
            wraplength=420
        )
        self.status_label.pack(pady=(8, 4))

        btn_frame = tk.Frame(self, bg=COLOUR_BG)
        btn_frame.pack(pady=8)

        self.confirm_btn = tk.Button(
            btn_frame, text="\u2705  Confirm Payment",
            font=FONT_SUBHEADING,
            bg=COLOUR_SUCCESS, fg=COLOUR_WHITE,
            relief="flat", padx=16, pady=8, cursor="hand2",
            state="disabled",
            command=self._confirm_payment
        )
        self.confirm_btn.pack(side="left", padx=8)

        tk.Button(
            btn_frame, text="\u2716  Cancel",
            font=FONT_SMALL,
            bg=COLOUR_DANGER, fg=COLOUR_WHITE,
            relief="flat", padx=12, pady=8, cursor="hand2",
            command=self.destroy
        ).pack(side="left", padx=8)

    def _insert(self, value_cents: int):
        """
        Add a denomination to the running inserted total.

        Args:
            value_cents (int): Denomination value in cents.
        """
        self._inserted += value_cents
        remaining = self.total_cents - self._inserted

        self.inserted_label.config(
            text=f"Inserted: {cents_to_display(self._inserted)}"
        )

        if remaining <= 0:
            change = abs(remaining)
            self.remaining_label.config(
                text=f"Change: {cents_to_display(change)}",
                fg=COLOUR_SUCCESS
            )
            self.status_label.config(
                text=(
                    f"\u2705  Covered!  "
                    f"Change due: {cents_to_display(change)}"
                ),
                fg=COLOUR_SUCCESS
            )
            self.confirm_btn.config(state="normal")
        else:
            self.remaining_label.config(
                text=f"Remaining: {cents_to_display(remaining)}",
                fg=COLOUR_DANGER
            )
            self.status_label.config(
                text=f"Still required: {cents_to_display(remaining)}",
                fg=COLOUR_LIGHT
            )

    def _confirm_payment(self):
        """Close the dialog and record the payment as 'cash'."""
        self.destroy()
        self.controller.complete_payment("cash")


# ===========================================================================
# PAYMENT DIALOG – PAYPAL
# ===========================================================================

class PayPalPaymentDialog(tk.Toplevel):
    """
    Modal dialog simulating a PayPal secure-checkout flow.

    Renders a PayPal-style login form. After clicking 'Log In & Pay',
    a progress animation confirms the transaction.

    SIMULATION ONLY: the email and password fields are placeholders.
    Nothing typed into them is validated, stored or transmitted, and
    the dialog tells the user not to enter real details.
    """

    def __init__(self, parent, controller, total_cents: int):
        super().__init__(parent)
        self.controller = controller
        self.total_cents = total_cents

        self.title("PayPal \u2013 Secure Checkout")
        self.geometry("420x560")
        self.resizable(False, False)
        self.configure(bg="#FFFFFF")
        self.grab_set()
        self._build_ui()

    def _build_ui(self):
        """Construct the PayPal-branded checkout dialog."""
        # Header
        header = tk.Frame(self, bg=COLOUR_PAYPAL, pady=16)
        header.pack(fill="x")
        tk.Label(
            header, text="PayPal",
            font=("Arial", 24, "bold"),
            bg=COLOUR_PAYPAL, fg=COLOUR_WHITE
        ).pack()
        tk.Label(
            header, text="Secure Checkout",
            font=("Arial", 11),
            bg=COLOUR_PAYPAL, fg=COLOUR_PAYPAL2
        ).pack()

        # Merchant / amount block
        amt = tk.Frame(self, bg="#F5F5F5", pady=14)
        amt.pack(fill="x")
        tk.Label(
            amt, text="Centrala Transport Authority",
            font=("Arial", 13, "bold"),
            bg="#F5F5F5", fg="#333333"
        ).pack()
        tk.Label(
            amt,
            text=f"Amount:  {cents_to_display(self.total_cents)}",
            font=("Arial", 16, "bold"),
            bg="#F5F5F5", fg=COLOUR_PAYPAL
        ).pack(pady=4)
        tk.Label(
            amt, text="Centrala Underground Zone Ticket",
            font=("Arial", 9), bg="#F5F5F5", fg="#888888"
        ).pack()

        # Login form
        form = tk.Frame(self, bg=COLOUR_WHITE, pady=12)
        form.pack(fill="x", padx=30)

        tk.Label(
            form, text="Email or mobile number",
            font=("Arial", 10), bg=COLOUR_WHITE, fg="#555555",
            anchor="w"
        ).pack(fill="x", pady=(8, 2))

        self.email_var = tk.StringVar(value="you@example.com")
        tk.Entry(
            form, textvariable=self.email_var,
            font=("Arial", 11), relief="solid", bd=1, fg="#333333"
        ).pack(fill="x", ipady=6)

        tk.Label(
            form, text="Password",
            font=("Arial", 10), bg=COLOUR_WHITE, fg="#555555",
            anchor="w"
        ).pack(fill="x", pady=(12, 2))

        self.pass_var = tk.StringVar(value="password")
        tk.Entry(
            form, textvariable=self.pass_var,
            show="\u2022", font=("Arial", 11), relief="solid", bd=1,
            fg="#333333"
        ).pack(fill="x", ipady=6)

        self.status_label = tk.Label(
            self, text="",
            font=("Arial", 10), bg=COLOUR_WHITE, fg=COLOUR_SUCCESS,
            wraplength=360
        )
        self.status_label.pack(pady=6)

        self.progress = ttk.Progressbar(
            self, orient="horizontal",
            length=340, mode="determinate"
        )
        self.progress.pack(pady=4)

        self.pay_btn = tk.Button(
            self, text="Log In & Pay Now",
            font=("Arial", 13, "bold"),
            bg=COLOUR_PAYPAL2, fg=COLOUR_WHITE,
            relief="flat", pady=12, cursor="hand2",
            command=self._process_payment
        )
        self.pay_btn.pack(fill="x", padx=30, pady=10)

        tk.Button(
            self, text="Cancel and return to merchant",
            font=("Arial", 9), bg=COLOUR_WHITE, fg=COLOUR_PAYPAL2,
            relief="flat", cursor="hand2",
            command=self.destroy
        ).pack()

        tk.Label(
            self,
            text="Simulation only – do not enter real account details.",
            font=("Arial", 8), bg=COLOUR_WHITE, fg="#AAAAAA"
        ).pack(pady=10)

    def _process_payment(self):
        """Start the PayPal authentication animation."""
        self.pay_btn.config(state="disabled")
        self.status_label.config(
            text="Authenticating with PayPal\u2026",
            fg="#F0A500"
        )
        self._animate(0)

    def _animate(self, step: int):
        """Advance the progress bar then confirm payment."""
        self.progress["value"] = step * 10
        if step < 10:
            self.after(110, lambda: self._animate(step + 1))
        else:
            self.status_label.config(
                text="\u2705  Payment successful!",
                fg=COLOUR_SUCCESS
            )
            self.after(800, self._go_to_voucher)

    def _go_to_voucher(self):
        """Close the dialog and record the payment as 'paypal'."""
        self.destroy()
        self.controller.complete_payment("paypal")


# ===========================================================================
# SCREEN 5 – TRAVEL VOUCHER / RECEIPT
# ===========================================================================

class VoucherScreen(tk.Frame):
    """
    Screen 5 – Travel Voucher Display and Receipt Actions.

    Generates and displays a formatted receipt. Provides:
      - 'Print Receipt' : sends to system printer
      - 'View PDF'      : generates a PDF and opens a preview window
                          plus the OS default PDF viewer
      - 'New Ticket'    : resets state for another purchase
      - 'Exit'          : closes the application
    """

    def __init__(self, parent, controller):
        super().__init__(parent, bg=COLOUR_BG)
        self.controller = controller
        self._voucher_text = ""      # Cached text for print / PDF
        self._last_pdf = None    # Path to last generated PDF file
        self._build_static_layout()

    def _build_static_layout(self):
        """Build the static parts of the voucher screen layout."""
        # Header
        header = tk.Frame(self, bg=COLOUR_SUCCESS, pady=10)
        header.pack(fill="x")
        tk.Label(
            header,
            text="\u2705  Step 4 of 4  \u2013  Your Travel Voucher",
            font=FONT_HEADING, bg=COLOUR_SUCCESS, fg=COLOUR_WHITE
        ).pack()

        # Scrollable receipt text area
        voucher_frame = tk.Frame(
            self, bg=COLOUR_PANEL, bd=2, relief="ridge"
        )
        voucher_frame.pack(padx=30, pady=12, fill="both", expand=True)

        self.voucher_text_widget = tk.Text(
            voucher_frame,
            font=FONT_MONO,
            bg=COLOUR_BG, fg=COLOUR_WHITE,
            relief="flat",
            state="disabled",   # Read-only; briefly enabled to insert
            padx=16, pady=14,
            wrap="none"
        )
        self.voucher_text_widget.pack(fill="both", expand=True)

        sb = ttk.Scrollbar(
            voucher_frame, orient="vertical",
            command=self.voucher_text_widget.yview
        )
        self.voucher_text_widget.configure(yscrollcommand=sb.set)
        sb.pack(side="right", fill="y")

        # --- Action button row ---
        btn_frame = tk.Frame(self, bg=COLOUR_BG, pady=12)
        btn_frame.pack(fill="x")

        # Print Receipt
        tk.Button(
            btn_frame, text="\U0001f5a8  Print Receipt",
            font=FONT_SUBHEADING, bg=COLOUR_ACCENT, fg=COLOUR_BG,
            relief="flat", padx=14, pady=8, cursor="hand2",
            command=self._print_receipt
        ).pack(side="left", padx=18)

        # View / Save PDF
        tk.Button(
            btn_frame, text="\U0001f4c4  View PDF",
            font=FONT_SUBHEADING, bg=COLOUR_CARD, fg=COLOUR_WHITE,
            relief="flat", padx=14, pady=8, cursor="hand2",
            command=self._view_pdf
        ).pack(side="left", padx=6)

        # New Ticket
        tk.Button(
            btn_frame, text="\U0001f504  New Ticket",
            font=FONT_SUBHEADING, bg=COLOUR_PANEL, fg=COLOUR_WHITE,
            relief="flat", padx=14, pady=8, cursor="hand2",
            command=self._new_voucher
        ).pack(side="left", padx=6)

        # Exit
        tk.Button(
            btn_frame, text="\u274c  Exit",
            font=FONT_SUBHEADING, bg=COLOUR_DANGER, fg=COLOUR_WHITE,
            relief="flat", padx=14, pady=8, cursor="hand2",
            command=self._exit_program
        ).pack(side="right", padx=18)

    def on_show(self):
        """
        Called each time this frame is raised.

        Builds the voucher from the transaction recorded by
        CTATicketingApp.complete_payment(). The issue time and reference
        are read from the state, not generated here, so they stay the
        same however many times the voucher is viewed, printed or saved.
        """
        self._last_pdf = None    # A new transaction needs a new PDF
        self._generate_voucher_text()
        self._display_voucher_text()

    # -----------------------------------------------------------------------
    # Voucher text generation
    # -----------------------------------------------------------------------

    def transaction_details(self) -> dict:
        """
        Collect everything the voucher and the PDF need in one place.

        Returns:
            dict: start/destination zone numbers and names, zones
                  travelled, the fare breakdown from
                  build_fare_breakdown(), payment method, issue time
                  and reference.
        """
        state = self.controller.state
        start_z = state["start_zone"]
        dest_z = state["destination_zone"]
        zones = calculate_zones_travelled(start_z, dest_z)

        # Fallbacks only apply if the voucher is opened without going
        # through a payment dialog; normal use always sets these.
        issue_time = state.get("issue_time") or datetime.now()
        reference = state.get("reference") or generate_reference(
            issue_time
        )
        state["issue_time"] = issue_time
        state["reference"] = reference

        return {
            "start_z":    start_z,
            "dest_z":     dest_z,
            "start_name": ZONES[start_z]["name"],
            "dest_name":  ZONES[dest_z]["name"],
            "zones":      zones,
            "breakdown":  build_fare_breakdown(state["travellers"], zones),
            # "or" guards against a None value, which .get() would
            # return as-is and which has no .upper() method.
            "payment":    (state.get("payment_method") or "unknown").upper(),
            "issue_time": issue_time,
            "reference":  reference,
        }

    def _generate_voucher_text(self):
        """
        Build the formatted voucher text from the transaction details.

        All four traveller categories are listed, including any with a
        count of 0, as Appendix 2 requires (IQA October 2026, AC 3.1).
        The result is cached in self._voucher_text for printing and for
        the PDF preview window.
        """
        details = self.transaction_details()
        start_z = details["start_z"]
        dest_z = details["dest_z"]
        start_name = details["start_name"]
        dest_name = details["dest_name"]
        zones_count = details["zones"]
        breakdown = details["breakdown"]
        payment = details["payment"]
        issue_time = details["issue_time"]

        width = 60
        line = "=" * width
        thin = "-" * width

        def centre(text: str) -> str:
            return text.center(width)

        lines = [
            line,
            centre("CENTRALA TRANSPORT AUTHORITY"),
            centre("OFFICIAL TRAVEL VOUCHER"),
            line,
            f"  Issued  : {issue_time.strftime('%A, %d %B %Y')}",
            f"  Time    : {issue_time.strftime('%H:%M:%S')}",
            f"  Ref     : {details['reference']}",
            thin,
            f"  Boarding    : {start_name} Zone (Zone {start_z})",
            f"  Destination : {dest_name} Zone (Zone {dest_z})",
            f"  Zones       : {zones_count} "
            f"zone{'s' if zones_count > 1 else ''} travelled",
            thin,
            centre("FARE BREAKDOWN"),
            thin,
            f"  {'Category':<10} {'Qty':>4}  "
            f"{'Rate/Zone':>11}  {'Zones':>5}  {'Total':>13}",
            thin,
        ]

        # One row per category, ALWAYS including zero-count categories.
        # (v3.5 skipped them with "if count == 0: continue".)
        for row in breakdown["rows"]:
            lines.append(
                f"  {row['label']:<10} {row['count']:>4}  "
                f"{cents_to_display(row['rate']):>11}  "
                f"{row['zones']:>5}  "
                f"{cents_to_display(row['total']):>13}"
            )

        lines += [
            thin,
            f"  {'TOTAL TRAVELLERS':<28} {breakdown['total_pax']:>13}",
            f"  {'AMOUNT PAID':<28} "
            f"{cents_to_display(breakdown['total_cents']):>13}",
            thin,
            f"  Payment Method : {payment}",
            line,
            centre("Thank you for travelling with CTA!"),
            centre("Please retain this voucher for inspection."),
            line,
        ]

        self._voucher_text = "\n".join(lines)

    def _display_voucher_text(self):
        """Insert the cached voucher text into the read-only Text widget."""
        self.voucher_text_widget.config(state="normal")
        self.voucher_text_widget.delete("1.0", "end")
        self.voucher_text_widget.insert("1.0", self._voucher_text)
        self.voucher_text_widget.config(state="disabled")

    # -----------------------------------------------------------------------
    # PDF generation and preview
    # -----------------------------------------------------------------------

    def _build_pdf(self):
        """
        Generate a PDF receipt using ReportLab.

        Returns:
            str  : Path to the generated PDF file, or None on failure.
        """
        if not REPORTLAB_AVAILABLE:
            return None

        # Same transaction details as the on-screen voucher: same issue
        # time, same reference and same fare breakdown (AC 4.2).
        details = self.transaction_details()
        start_z = details["start_z"]
        dest_z = details["dest_z"]
        zones_count = details["zones"]
        breakdown = details["breakdown"]
        payment = details["payment"]
        issue_time = details["issue_time"]

        # Create a temp file for the PDF
        tmp = tempfile.NamedTemporaryFile(
            suffix=".pdf", delete=False
        )
        pdf_path = tmp.name
        tmp.close()

        doc = SimpleDocTemplate(
            pdf_path,
            pagesize=A4,
            rightMargin=25 * mm,
            leftMargin=25 * mm,
            topMargin=20 * mm,
            bottomMargin=20 * mm,
        )

        styles = getSampleStyleSheet()

        # Custom paragraph styles
        _navy = colors.HexColor("#1B2A4A")
        _gold = colors.HexColor("#F0A500")
        _white = colors.white
        _light = colors.HexColor("#C8D6E5")

        title_style = ParagraphStyle(
            "CTATitle",
            parent=styles["Title"],
            fontName="Helvetica-Bold",
            fontSize=18,
            textColor=_white,
            spaceAfter=4,
            alignment=1,
        )
        sub_style = ParagraphStyle(
            "CTASub",
            parent=styles["Normal"],
            fontName="Helvetica",
            fontSize=10,
            textColor=_white,
            alignment=1,
            spaceAfter=0,
        )
        section_style = ParagraphStyle(
            "CTASection",
            parent=styles["Normal"],
            fontName="Helvetica-Bold",
            fontSize=11,
            textColor=_gold,
            alignment=1,
            spaceAfter=4,
        )
        footer_style = ParagraphStyle(
            "CTAFooter",
            parent=styles["Normal"],
            fontName="Helvetica-Oblique",
            fontSize=9,
            textColor=_navy,
            alignment=1,
        )

        page_w = A4[0] - 50 * mm   # usable width

        content = []

        # ---- Title header block ----
        header_data = [[
            Paragraph("CENTRALA TRANSPORT AUTHORITY", title_style),
        ]]
        sub_data = [[
            Paragraph("OFFICIAL TRAVEL VOUCHER", sub_style),
        ]]
        header_table = Table(
            header_data + sub_data,
            colWidths=[page_w]
        )
        header_table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, -1), _navy),
            ("TOPPADDING",    (0, 0), (-1, -1), 10),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 10),
            ("LEFTPADDING",   (0, 0), (-1, -1), 8),
            ("RIGHTPADDING",  (0, 0), (-1, -1), 8),
        ]))
        content.append(header_table)
        content.append(Spacer(1, 6 * mm))

        # ---- Issue info ----
        issue_data = [
            ["Issued:", issue_time.strftime("%A, %d %B %Y")],
            ["Time:",   issue_time.strftime("%H:%M:%S")],
            ["Ref:",    details["reference"]],
        ]
        issue_table = Table(issue_data, colWidths=[35 * mm, page_w - 35 * mm])
        issue_table.setStyle(TableStyle([
            ("FONTNAME",  (0, 0), (0, -1), "Helvetica-Bold"),
            ("FONTNAME",  (1, 0), (1, -1), "Helvetica"),
            ("FONTSIZE",  (0, 0), (-1, -1), 10),
            ("TEXTCOLOR", (0, 0), (-1, -1), _navy),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
            ("TOPPADDING",    (0, 0), (-1, -1), 3),
        ]))
        content.append(issue_table)
        content.append(Spacer(1, 4 * mm))

        # ---- Journey details ----
        content.append(Paragraph("JOURNEY DETAILS", section_style))
        journey_data = [
            ["Boarding:",    f"{ZONES[start_z]['name']} Zone "
                             f"(Zone {start_z})"],
            ["Destination:", f"{ZONES[dest_z]['name']} Zone "
                             f"(Zone {dest_z})"],
            ["Zones:",       f"{zones_count} zone"
                             f"{'s' if zones_count > 1 else ''} "
                             f"travelled"],
        ]
        journey_table = Table(
            journey_data,
            colWidths=[35 * mm, page_w - 35 * mm]
        )
        journey_table.setStyle(TableStyle([
            ("FONTNAME",  (0, 0), (0, -1), "Helvetica-Bold"),
            ("FONTNAME",  (1, 0), (1, -1), "Helvetica"),
            ("FONTSIZE",  (0, 0), (-1, -1), 10),
            ("TEXTCOLOR", (0, 0), (-1, -1), _navy),
            ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#EAF2F8")),
            ("ROWBACKGROUNDS", (0, 0), (-1, -1),
             [colors.HexColor("#EAF2F8"), colors.white]),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
            ("TOPPADDING",    (0, 0), (-1, -1), 4),
            ("LEFTPADDING",   (0, 0), (-1, -1), 6),
            ("LINEBELOW", (0, -1), (-1, -1), 0.5, _light),
        ]))
        content.append(journey_table)
        content.append(Spacer(1, 4 * mm))

        # ---- Fare breakdown table ----
        content.append(Paragraph("FARE BREAKDOWN", section_style))

        fare_header = [
            "Category", "Qty", "Rate/Zone", "Zones", "Total (cents)"
        ]
        fare_rows = [fare_header]

        # All four categories, including zero counts (AC 2.2 / 3.1)
        for row in breakdown["rows"]:
            fare_rows.append([
                row["label"],
                str(row["count"]),
                cents_to_display(row["rate"]),
                str(row["zones"]),
                cents_to_display(row["total"]),
            ])

        # Totals row
        fare_rows.append([
            "TOTAL", str(breakdown["total_pax"]), "", "",
            cents_to_display(breakdown["total_cents"])
        ])

        col_w = [40 * mm, 15 * mm, 32 * mm, 18 * mm, 35 * mm]
        fare_table = Table(fare_rows, colWidths=col_w)
        fare_table.setStyle(TableStyle([
            # Header row
            ("BACKGROUND",  (0, 0), (-1, 0), _navy),
            ("TEXTCOLOR",   (0, 0), (-1, 0), _white),
            ("FONTNAME",    (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTSIZE",    (0, 0), (-1, -1), 10),
            ("ALIGN",       (1, 0), (-1, -1), "CENTER"),
            ("ALIGN",       (0, 0), (0, -1), "LEFT"),
            # Data rows
            ("ROWBACKGROUNDS", (0, 1), (-1, -2),
             [colors.white, colors.HexColor("#EAF2F8")]),
            ("FONTNAME",    (0, -1), (-1, -1), "Helvetica-Bold"),
            ("BACKGROUND",  (0, -1), (-1, -1), _gold),
            ("TEXTCOLOR",   (0, -1), (-1, -1), _navy),
            # Borders
            ("GRID",        (0, 0), (-1, -1), 0.4, _light),
            ("LINEABOVE",   (0, 0), (-1, 0), 1.5, _navy),
            ("LINEBELOW",   (0, -1), (-1, -1), 1.5, _navy),
            ("TOPPADDING",  (0, 0), (-1, -1), 5),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
            ("LEFTPADDING", (0, 0), (0, -1), 6),
        ]))
        content.append(fare_table)
        content.append(Spacer(1, 4 * mm))

        # ---- Payment info ----
        pay_data = [["Payment Method:", payment]]
        pay_table = Table(pay_data, colWidths=[45 * mm, page_w - 45 * mm])
        pay_table.setStyle(TableStyle([
            ("FONTNAME",  (0, 0), (0, -1), "Helvetica-Bold"),
            ("FONTNAME",  (1, 0), (1, -1), "Helvetica"),
            ("FONTSIZE",  (0, 0), (-1, -1), 10),
            ("TEXTCOLOR", (0, 0), (-1, -1), _navy),
            ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#EAF2F8")),
            ("TOPPADDING", (0, 0), (-1, -1), 5),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
            ("LEFTPADDING", (0, 0), (-1, -1), 6),
        ]))
        content.append(pay_table)
        content.append(Spacer(1, 6 * mm))

        # ---- Footer ----
        footer_bar_data = [[
            Paragraph(
                "Thank you for travelling with CTA!<br/>"
                "Please retain this voucher for inspection.",
                footer_style
            )
        ]]
        footer_table = Table(footer_bar_data, colWidths=[page_w])
        footer_table.setStyle(TableStyle([
            ("BACKGROUND",    (0, 0), (-1, -1), _navy),
            ("TEXTCOLOR",     (0, 0), (-1, -1), _white),
            ("TOPPADDING",    (0, 0), (-1, -1), 10),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 10),
        ]))
        content.append(footer_table)

        doc.build(content)
        return pdf_path

    def _view_pdf(self):
        """
        Generate the PDF receipt, open a preview window, and launch
        the OS default PDF viewer.
        """
        if not self._voucher_text:
            messagebox.showwarning(
                "Nothing to View",
                "Please generate a voucher before viewing the PDF."
            )
            return

        if not REPORTLAB_AVAILABLE:
            messagebox.showwarning(
                "ReportLab Not Available",
                "PDF generation requires ReportLab.\n"
                "Install it with: pip install reportlab"
            )
            return

        # Build the PDF
        pdf_path = self._build_pdf()
        if not pdf_path:
            messagebox.showerror(
                "PDF Error",
                "Could not generate the PDF receipt."
            )
            return

        self._last_pdf = pdf_path

        # Open the in-app PDF preview window
        PDFPreviewWindow(
            self, pdf_path, self._voucher_text,
            reference=self.controller.state["reference"]
        )

        # Also launch the OS default PDF viewer
        try:
            if os.name == "nt":
                os.startfile(pdf_path)
            elif os.uname().sysname == "Darwin":
                subprocess.Popen(["open", pdf_path])
            else:
                subprocess.Popen(["xdg-open", pdf_path])
        except Exception as exc:   # Viewer launch is optional
            # [ENH-7] The in-app preview is already open, so the user is
            # not interrupted; the cause is recorded for support staff.
            logger.warning("Could not open external PDF viewer: %s", exc)

    def _print_receipt(self):
        """
        Send the receipt text to the system's default printer.

        Windows : Notepad /p (silent print)
        macOS   : lpr
        Linux   : lpr (CUPS)
        Fallback: Save-as dialog
        """
        if not self._voucher_text:
            messagebox.showwarning(
                "Nothing to Print",
                "Please generate a voucher before printing."
            )
            return

        try:
            with tempfile.NamedTemporaryFile(
                mode="w", suffix=".txt",
                delete=False, encoding="utf-8"
            ) as tmp:
                tmp.write(self._voucher_text)
                tmp_path = tmp.name

            if os.name == "nt":
                subprocess.Popen(
                    ["notepad.exe", "/p", tmp_path], shell=False
                )
                messagebox.showinfo(
                    "Printing",
                    "Receipt sent to printer via Notepad."
                )
            else:
                result = subprocess.run(
                    ["lpr", tmp_path],
                    capture_output=True, text=True, timeout=10
                )
                if result.returncode == 0:
                    messagebox.showinfo(
                        "Printing",
                        "Receipt sent to the default printer."
                    )
                else:
                    raise RuntimeError(result.stderr)

        except Exception as exc:
            logger.warning("Printing failed: %s", exc)       # [ENH-7]
            self._save_receipt_fallback(str(exc))

    def _save_receipt_fallback(self, error_msg: str):
        """
        Offer a file-save dialog when printing fails.

        Args:
            error_msg (str): Description of the print error.
        """
        if messagebox.askyesno(
            "Printer Unavailable",
            f"Could not send to printer ({error_msg}).\n\n"
            "Would you like to save the receipt as a text file?"
        ):
            path = filedialog.asksaveasfilename(
                defaultextension=".txt",
                filetypes=[
                    ("Text files", "*.txt"),
                    ("All files", "*.*")
                ],
                initialfile="CTA_Voucher.txt",
                title="Save Receipt"
            )
            if path:
                with open(path, "w", encoding="utf-8") as f:
                    f.write(self._voucher_text)
                messagebox.showinfo("Saved", f"Receipt saved to:\n{path}")

    def _new_voucher(self):
        """Confirm and reset state for a new ticket purchase."""
        if messagebox.askyesno(
            "New Ticket",
            "Start a new ticket purchase?\n"
            "Your current voucher will be cleared."
        ):
            self.controller.reset_state()
            self.controller.show_frame("WelcomeScreen")

    def _exit_program(self):
        """Prompt for confirmation and exit the application."""
        if messagebox.askyesno(
            "Exit",
            "Are you sure you want to exit the CTA Ticketing System?"
        ):
            self.controller.destroy()


# ===========================================================================
# PDF PREVIEW WINDOW
# ===========================================================================

class PDFPreviewWindow(tk.Toplevel):
    """
    In-app PDF preview window.

    Renders the receipt content on a white A4-style canvas inside a
    scrollable Toplevel window, simulating a PDF page view. Also provides
    a 'Save PDF' button to save the file to a user-chosen location.
    """

    def __init__(
        self, parent, pdf_path: str, voucher_text: str,
        reference: str = "CTA_Voucher"
    ):
        super().__init__(parent)
        self._pdf_path = pdf_path
        self._voucher_txt = voucher_text
        self._reference = reference   # Used as the default file name

        self.title("\U0001f4c4  CTA Receipt \u2013 PDF Preview")
        self.geometry("660x820")
        self.resizable(True, True)
        self.configure(bg="#555555")   # Dark grey page-viewer background
        self.minsize(500, 600)

        self._build_ui()

    def _build_ui(self):
        """Construct the PDF preview layout."""
        # Top toolbar
        toolbar = tk.Frame(self, bg="#333333", pady=8)
        toolbar.pack(fill="x")

        tk.Label(
            toolbar,
            text="\U0001f4c4  PDF Receipt Preview",
            font=("Calibri", 12, "bold"),
            bg="#333333", fg="#FFFFFF"
        ).pack(side="left", padx=16)

        tk.Button(
            toolbar, text="\U0001f4be  Save PDF As\u2026",
            font=("Calibri", 10, "bold"),
            bg=COLOUR_ACCENT, fg=COLOUR_BG,
            relief="flat", padx=10, pady=5, cursor="hand2",
            command=self._save_pdf
        ).pack(side="right", padx=10)

        tk.Button(
            toolbar, text="\U0001f5a8  Print",
            font=("Calibri", 10, "bold"),
            bg=COLOUR_CARD, fg=COLOUR_WHITE,
            relief="flat", padx=10, pady=5, cursor="hand2",
            command=self._print_pdf
        ).pack(side="right", padx=4)

        # Scrollable canvas area
        scroll_frame = tk.Frame(self, bg="#555555")
        scroll_frame.pack(fill="both", expand=True, padx=10, pady=10)

        canvas = tk.Canvas(
            scroll_frame, bg="#555555",
            highlightthickness=0
        )
        v_sb = ttk.Scrollbar(
            scroll_frame, orient="vertical", command=canvas.yview
        )
        h_sb = ttk.Scrollbar(
            scroll_frame, orient="horizontal", command=canvas.xview
        )
        canvas.configure(
            yscrollcommand=v_sb.set,
            xscrollcommand=h_sb.set
        )

        h_sb.pack(side="bottom", fill="x")
        v_sb.pack(side="right",  fill="y")
        canvas.pack(side="left", fill="both", expand=True)

        # A4-like white page rendered on the canvas
        # A4 aspect ratio ≈ 210 : 297 → use 580 × 820 px
        page_w, page_h = 580, 820
        margin = 20   # canvas border around the page

        canvas.config(
            scrollregion=(0, 0, page_w + 2 * margin, page_h + 2 * margin)
        )

        # White page shadow
        canvas.create_rectangle(
            margin + 4, margin + 4,
            margin + page_w + 4, margin + page_h + 4,
            fill="#999999", outline=""
        )
        # White page body
        canvas.create_rectangle(
            margin, margin,
            margin + page_w, margin + page_h,
            fill="white", outline="#CCCCCC", width=1
        )

        self._draw_receipt_on_canvas(canvas, margin, page_w, page_h)

        # Mouse-wheel scrolling. The wheel is bound only while the
        # pointer is over the page and is released when it leaves, so
        # no global binding survives after this window is closed.
        # (v3.5 used bind_all permanently; scrolling in the main window
        # after closing the preview then raised a TclError.)
        def _on_wheel(event):
            canvas.yview_scroll(-1 * (event.delta // 120), "units")

        def _bind_wheel(_event):
            canvas.bind_all("<MouseWheel>", _on_wheel)
            canvas.bind_all(
                "<Button-4>", lambda e: canvas.yview_scroll(-1, "units")
            )
            canvas.bind_all(
                "<Button-5>", lambda e: canvas.yview_scroll(1, "units")
            )

        def _unbind_wheel(_event=None):
            for sequence in ("<MouseWheel>", "<Button-4>", "<Button-5>"):
                canvas.unbind_all(sequence)

        canvas.bind("<Enter>", _bind_wheel)
        canvas.bind("<Leave>", _unbind_wheel)
        self.protocol(
            "WM_DELETE_WINDOW", lambda: (_unbind_wheel(), self.destroy())
        )

    def _draw_receipt_on_canvas(
        self, canvas: tk.Canvas, margin: int,
        page_w: int, page_h: int
    ):
        """
        Draw the receipt content onto the white page canvas.

        Args:
            canvas  : The tk.Canvas to draw on.
            margin  : Pixel margin around the page on the canvas.
            page_w  : Width of the A4-page area in pixels.
            page_h  : Height of the A4-page area in pixels.
        """
        _navy = "#1B2A4A"
        _gold = "#F0A500"
        _light = "#DDEEFF"
        _white = "#FFFFFF"

        x0 = margin         # Left edge of the page
        x1 = margin + page_w   # Right edge of the page
        cx = margin + page_w // 2   # Centre x

        # ---- Header band ----
        canvas.create_rectangle(
            x0, margin, x1, margin + 68,
            fill=_navy, outline=""
        )
        canvas.create_text(
            cx, margin + 22,
            text="CENTRALA TRANSPORT AUTHORITY",
            font=("Helvetica", 14, "bold"),
            fill=_white, anchor="center"
        )
        canvas.create_text(
            cx, margin + 46,
            text="OFFICIAL TRAVEL VOUCHER",
            font=("Helvetica", 10),
            fill=_gold, anchor="center"
        )

        # ---- Parse and render receipt lines ----
        lines = self._voucher_txt.split("\n")

        y = margin + 84   # Start y below header band
        lh = 15            # Line height in pixels
        pad_x = x0 + 28      # Left text margin
        mono_fn = ("Courier New", 9)
        bold_fn = ("Courier New", 9, "bold")

        for raw_line in lines:
            # Skip the plain separator lines – draw as canvas rules
            stripped = raw_line.strip()

            if stripped.startswith("===="):
                canvas.create_line(
                    x0 + 16, y + lh // 2,
                    x1 - 16, y + lh // 2,
                    fill=_navy, width=2
                )
                y += lh
                continue

            if stripped.startswith("----"):
                canvas.create_line(
                    x0 + 16, y + lh // 2,
                    x1 - 16, y + lh // 2,
                    fill=_light, width=1
                )
                y += lh
                continue

            # Colour-code special rows
            if stripped in (
                "FARE BREAKDOWN",
                "CENTRALA TRANSPORT AUTHORITY",
                "OFFICIAL TRAVEL VOUCHER",
            ):
                # anchor="n" centres the heading on cx (v3.5 used "w",
                # which started the text at the centre line instead)
                canvas.create_text(
                    cx, y + 2, text=stripped,
                    font=bold_fn, fill=_gold, anchor="n"
                )
                y += lh
                continue

            if stripped.startswith(
                ("Thank you", "Please retain")
            ):
                canvas.create_text(
                    cx, y, text=stripped,
                    font=("Helvetica", 9, "italic"),
                    fill=_navy, anchor="center"
                )
                y += lh
                continue

            if "TOTAL TRAVELLERS" in stripped or "AMOUNT PAID" in stripped:
                # Highlight total rows
                canvas.create_rectangle(
                    x0 + 16, y, x1 - 16, y + lh,
                    fill=_gold, outline=""
                )
                canvas.create_text(
                    pad_x, y + 2, text=raw_line,
                    font=bold_fn, fill=_navy, anchor="nw"
                )
                y += lh
                continue

            # Default line rendering
            canvas.create_text(
                pad_x, y + 2, text=raw_line,
                font=mono_fn, fill=_navy, anchor="nw"
            )
            y += lh

        # ---- Footer band ----
        footer_y = max(y + 10, margin + page_h - 40)
        canvas.create_rectangle(
            x0, footer_y, x1, margin + page_h,
            fill=_navy, outline=""
        )
        canvas.create_text(
            cx, footer_y + 14,
            text="CTA – Centrala Transport Authority",
            font=("Helvetica", 8),
            fill=_gold, anchor="center"
        )

    def _save_pdf(self):
        """
        Save a copy of the PDF receipt to a location chosen by the user.

        Behaviour (corrected description, IQA October 2026, AC 4.2):
        the preview window deliberately STAYS OPEN after saving, so the
        user can still print or check the receipt. This method does not
        close the window; the v3.5 test record claiming that it did was
        inaccurate and has been withdrawn.

        If the copy fails (for example the destination file is open in
        another program, or the folder is read-only) the error is shown
        to the user instead of crashing the program.
        """
        dest = filedialog.asksaveasfilename(
            parent=self,
            defaultextension=".pdf",
            filetypes=[("PDF files", "*.pdf"), ("All files", "*.*")],
            initialfile=f"{self._reference}.pdf",
            title="Save PDF Receipt"
        )
        if not dest:            # User pressed Cancel
            return

        try:
            shutil.copy2(self._pdf_path, dest)
        except OSError as exc:
            logger.error("Saving PDF to %s failed: %s", dest, exc)  # ENH-7
            messagebox.showerror(
                "Save Failed",
                f"The PDF could not be saved:\n{exc}",
                parent=self
            )
            return

        messagebox.showinfo(
            "Saved", f"PDF saved to:\n{dest}", parent=self
        )

    def _print_pdf(self):
        """Send the PDF file to the system printer."""
        try:
            if os.name == "nt":
                os.startfile(self._pdf_path, "print")
            else:
                subprocess.run(
                    ["lpr", self._pdf_path],
                    check=True, timeout=10
                )
            messagebox.showinfo(
                "Printing", "PDF sent to the default printer."
            )
        except Exception as exc:
            logger.warning("PDF printing failed: %s", exc)    # [ENH-7]
            messagebox.showerror(
                "Print Error",
                f"Could not print the PDF:\n{exc}"
            )


# ===========================================================================
# AUTOMATED SELF-TESTS  (run with:  python <this file> --selftest)
# ===========================================================================

def run_self_tests() -> bool:
    """
    Run automated checks that support the test plan (AC 4.1 / 4.2).

    Each check prints PASS or FAIL with the expected and actual values,
    so the output can be pasted into the test log as evidence. The
    calculation tests need no GUI. The GUI tests (AT15 to AT18) open
    a hidden window and are skipped if no display is available.

    Returns:
        bool: True if every check passed.
    """
    results = []

    def check(test_id: str, description: str, expected, actual):
        """Record and print one test result."""
        passed = expected == actual
        results.append(passed)
        status = "PASS" if passed else "FAIL"
        print(f"[{status}] {test_id}  {description}")
        if not passed:
            print(f"         expected: {expected!r}")
            print(f"         actual  : {actual!r}")

    print("CTA Automated Ticketing System - self-tests")
    print("=" * 60)

    # AT1 - reference data matches Appendix 1
    check("AT1", "Station data passes validate_reference_data()",
          [], validate_reference_data())
    check("AT2", "Station counts per zone are 10 / 12 / 14",
          [10, 12, 14], [len(ZONES[z]["stations"]) for z in (1, 2, 3)])
    check("AT3", "Lomil is Central; Riclya and Sylas are Midtown",
          (True, True, True),
          ("Lomil" in ZONES[1]["stations"],
           "Riclya" in ZONES[2]["stations"],
           "Sylas" in ZONES[2]["stations"]))

    # AT4 - zones travelled (|dest - start| + 1)
    check("AT4", "Zones travelled: 1->3 = 3, 2->2 = 1, 3->1 = 3",
          [3, 1, 3],
          [calculate_zones_travelled(1, 3),
           calculate_zones_travelled(2, 2),
           calculate_zones_travelled(3, 1)])

    # AT5 - fare arithmetic from Appendix 2
    one_each = {"adult": 1, "child": 1, "senior": 1, "student": 1}
    check("AT5", "One of each category over 3 zones = 18870 cents",
          18870, build_fare_breakdown(one_each, 3)["total_cents"])

    # AT6 - zero-count categories are still listed on the voucher
    partial = {"adult": 2, "child": 1, "senior": 0, "student": 0}
    rows = build_fare_breakdown(partial, 2)["rows"]
    check("AT6", "Voucher lists all 4 categories when some are 0",
          ["adult", "child", "senior", "student"],
          [row["key"] for row in rows])
    check("AT7", "Zero-count rows show count 0 and total 0",
          [(0, 0), (0, 0)],
          [(row["count"], row["total"]) for row in rows[2:]])

    # AT8 - references are unique within the same second
    same_second = datetime(2026, 10, 23, 14, 30, 5)
    refs = [generate_reference(same_second) for _ in range(5)]
    check("AT8", "5 references issued in the same second are unique",
          5, len(set(refs)))

    # AT9 - validation boundaries
    check("AT9", "Validation: '', 'abc', '-1', '51' rejected; "
          "'0' and '50' accepted",
          [False, False, False, False, True, True],
          [validate_positive_integer(v, "Adults")[0]
           for v in ("", "abc", "-1", "51", "0", "50")])

    # AT10-AT12 - [ENH-1] station finder
    check("AT10", "find_station ignores case and spaces (' lomil ')",
          (1, "Lomil"), find_station(" lomil "))
    check("AT11", "find_station returns None for an unknown name",
          None, find_station("Paris"))
    check("AT12", "suggest_stations('ri') lists starts, then contains",
          ["Riclya", "Riladia", "Ederif", "Garion", "Perinad"],
          suggest_stations("ri"))

    # AT13-AT14 - [ENH-3] / [ENH-4] transaction log and sales summary.
    # A temporary folder is used so the real log is never touched.
    with tempfile.TemporaryDirectory() as folder:
        test_log = os.path.join(folder, "test_transactions.csv")
        day = datetime(2026, 10, 23, 9, 0, 0)
        for counts, method in (
            ({"adult": 2, "child": 1, "senior": 0, "student": 0}, "CARD"),
            ({"adult": 0, "child": 0, "senior": 1, "student": 2}, "CASH"),
        ):
            record_transaction({
                "reference": generate_reference(day),
                "issue_time": day, "start_name": "Central",
                "dest_name": "Downtown", "zones": 3,
                "breakdown": build_fare_breakdown(counts, 3),
                "payment": method,
            }, log_path=test_log)

        summary = summarise_sales(test_log, "2026-10-23")
        # 2*2105*3 + 1410*3 = 16860 ; 1025*3 + 2*1750*3 = 13575
        check("AT13", "Log 2 vouchers -> summary 2 vouchers, 6 "
              "travellers, 30435 cents",
              (2, 6, 30435, {"CARD": 1, "CASH": 1}),
              (summary["vouchers"], summary["travellers"],
               summary["total_cents"], summary["by_payment"]))

        with open(test_log, "a", encoding="utf-8") as handle:
            handle.write("BAD-ROW,2026-10-23,,,,,,,,,,not-a-number,\n")
        check("AT14", "A damaged row is skipped, not counted",
              (2, 1), (summarise_sales(test_log, "2026-10-23")["vouchers"],
                       summarise_sales(test_log, "2026-10-23")["skipped"]))

    # AT15 - New Ticket clears the screen inputs (needs a display)
    try:
        app = CTATicketingApp()
        app.withdraw()
        zone_screen = app.frames["ZoneSelectionScreen"]
        trav_screen = app.frames["TravellerScreen"]
        zone_screen.start_var.set(1)
        zone_screen.destination_var.set(3)
        trav_screen.inputs["adult"].set("4")
        app.reset_state()
        check("AT15", "reset_state() clears zone and traveller inputs",
              (0, 0, ["0", "0", "0", "0"]),
              (zone_screen.start_var.get(),
               zone_screen.destination_var.get(),
               [var.get() for var in trav_screen.inputs.values()]))

        # AT16 - [ENH-2] live preview: Central -> Downtown, 2 adults
        app.state["start_zone"], app.state["destination_zone"] = 1, 3
        trav_screen.inputs["adult"].set("2")
        check("AT16", "Live preview shows 12630 cents for 2 adults, "
              "3 zones",
              True, "12630 cents" in trav_screen.live_total_label["text"])

        # AT17 - [ENH-6] Escape on the traveller screen goes back
        app.show_frame("TravellerScreen")
        app._dispatch_key("on_escape")
        check("AT17", "Escape on traveller screen returns to zones",
              "ZoneSelectionScreen", app.current_frame)

        # AT18 - [ENH-5] idle timeout returns to the board and resets
        app._on_idle_timeout()
        check("AT18", "Idle timeout returns to board and clears zones",
              ("WelcomeScreen", None),
              (app.current_frame, app.state["start_zone"]))
        app.destroy()
    except tk.TclError:
        print("[SKIP] AT15-AT18  GUI tests need a display")

    print("=" * 60)
    print(f"{sum(results)} of {len(results)} checks passed.")
    return all(results)


# ===========================================================================
# ENTRY POINT
# ===========================================================================

def main():
    """
    Application entry point.

    With --selftest, runs the automated checks and exits with code 0
    (all passed) or 1 (a check failed). Otherwise creates the root
    CTATicketingApp window and starts the tkinter event loop, which
    runs until the user clicks Exit or closes the window.
    """
    if "--selftest" in sys.argv:
        sys.exit(0 if run_self_tests() else 1)

    configure_logging()             # [ENH-7] GUI runs only
    app = CTATicketingApp()
    app.mainloop()


if __name__ == "__main__":
    main()
