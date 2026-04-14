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
 Version     : 3.0.0
 Date        : March 2026
=============================================================================

DESIGN OVERVIEW
---------------
The application follows an event-driven programming paradigm using tkinter.
It uses a Frame-stacking technique: all screens are created at startup and
raised to the top as the user navigates. This avoids screen flickering and
provides a smooth, professional user experience.

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
import os                                  # OS-level file operations
import subprocess                          # Cross-platform process launching
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

# Fare rates expressed in PENCE per zone (integer arithmetic avoids
# floating-point rounding errors). Original spec: 2105 / 1410 / 1025 /
# 1750 CENTS – mapped directly to pence and displayed as pound sterling.
ADULT_FARE_PER_ZONE   = 2105   # £21.05 per zone
CHILD_FARE_PER_ZONE   = 1410   # £14.10 per zone
SENIOR_FARE_PER_ZONE  = 1025   # £10.25 per zone
STUDENT_FARE_PER_ZONE = 1750   # £17.50 per zone

# Colour palette – CTA brand colours (dark navy + gold accent)
COLOUR_BG       = "#1B2A4A"   # Dark navy – primary background
COLOUR_PANEL    = "#243860"   # Lighter navy – card backgrounds
COLOUR_ACCENT   = "#F0A500"   # Gold – primary accent
COLOUR_WHITE    = "#FFFFFF"   # White – primary text on dark background
COLOUR_LIGHT    = "#C8D6E5"   # Light blue-grey – secondary text
COLOUR_SUCCESS  = "#27AE60"   # Green – success / confirmed actions
COLOUR_DANGER   = "#E74C3C"   # Red – errors / warnings
COLOUR_INPUT_BG = "#2E4070"   # Slightly lighter – input field backgrounds
COLOUR_BTN      = "#F0A500"   # Gold – primary button fill
COLOUR_BTN_TEXT = "#1B2A4A"   # Navy – text on gold buttons
COLOUR_PAYPAL   = "#003087"   # PayPal dark blue
COLOUR_PAYPAL2  = "#009CDE"   # PayPal light blue
COLOUR_CASH     = "#1E8449"   # Green for cash
COLOUR_CARD     = "#1A3A6B"   # Navy for card

# Font definitions
FONT_TITLE      = ("Georgia", 22, "bold")
FONT_HEADING    = ("Georgia", 14, "bold")
FONT_SUBHEADING = ("Calibri", 12, "bold")
FONT_BODY       = ("Calibri", 11)
FONT_SMALL      = ("Calibri", 9)
FONT_MONO       = ("Courier New", 10)   # Voucher / receipt output


# ---------------------------------------------------------------------------
# DATA – CENTRALA UNDERGROUND ZONE AND STATION DEFINITIONS
# ---------------------------------------------------------------------------
# Station names taken directly from the assignment brief (Appendix 1).
# Zone numbers map to concentric zones: 1 = Central (innermost),
# 2 = Midtown, 3 = Downtown (outermost).
# Fare formula: zones_travelled = abs(destination - start) + 1
ZONES = {
    1: {
        "name": "Central",
        "description": "City centre hub",
        "stations": [
            "Centrala", "Frestin", "Jaund", "Rede", "Soth"
        ]
    },
    2: {
        "name": "Midtown",
        "description": "Inner residential & commercial",
        "stations": [
            "Agralle", "Bylyn", "Docia", "Garion", "Lomil",
            "Ninia", "Obelyn", "Quthiel", "Ralith", "Riclya",
            "Riladia", "Stonyam", "Sylas", "Tallan", "Wicyt", "Yaen"
        ]
    },
    3: {
        "name": "Downtown",
        "description": "Outer suburbs & interchange",
        "stations": [
            "Adohad", "Brunad", "Ederif", "Elyot", "Erean",
            "Holmer", "Keivia", "Marend", "Oloadus", "Perinad",
            "Pryn", "Ruril", "Ryall", "Vertwall", "Zord"
        ]
    }
}

# Traveller fare configuration – drives the dynamic input form
TRAVELLER_TYPES = [
    {"key": "adult",   "label": "Adults",   "fare": ADULT_FARE_PER_ZONE},
    {"key": "child",   "label": "Children", "fare": CHILD_FARE_PER_ZONE},
    {"key": "senior",  "label": "Seniors",  "fare": SENIOR_FARE_PER_ZONE},
    {"key": "student", "label": "Students", "fare": STUDENT_FARE_PER_ZONE},
]


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
    Calculate the total fare in PENCE for a group of travellers.

    Args:
        fare_per_zone (int): Rate in PENCE per zone for the traveller type.
        zones         (int): Number of zones travelled.
        count         (int): Number of travellers of this type.

    Returns:
        int: Total fare in PENCE.
    """
    return fare_per_zone * zones * count


def pence_to_display(pence: int) -> str:
    """
    Convert a PENCE amount to a formatted pound sterling string.

    Stores fares as integers to avoid floating-point rounding errors;
    converts here purely for human-readable display and printing.

    Args:
        pence (int): Amount in pence.

    Returns:
        str: Formatted string, e.g. 2105 -> "£21.05"
    """
    return f"\u00a3{pence / 100:.2f}"


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

    return True, int(stripped), ""


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

        self.show_frame("WelcomeScreen")

    def show_frame(self, frame_name: str):
        """
        Bring the named frame to the foreground.

        Args:
            frame_name (str): Key in self.frames dict (class name).
        """
        frame = self.frames[frame_name]
        if hasattr(frame, "on_show"):
            frame.on_show()
        frame.tkraise()

    def reset_state(self):
        """Reset all shared journey state for a new ticket purchase."""
        self.state["start_zone"]       = None
        self.state["destination_zone"] = None
        self.state["payment_method"]   = None
        for key in self.state["travellers"]:
            self.state["travellers"][key] = 0


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

        # Column names derived from zone names and descriptions
        columns = [
            f"Zone {z} \u2013 {ZONES[z]['name']}"
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

        # Pad shorter zone station lists with empty strings
        max_rows = max(len(ZONES[z]["stations"]) for z in ZONES)
        for row_idx in range(max_rows):
            row_data = [
                (ZONES[z]["stations"][row_idx]
                 if row_idx < len(ZONES[z]["stations"]) else "")
                for z in sorted(ZONES.keys())
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
            text="Select your journey zones on the next screen",
            font=FONT_SMALL, bg=COLOUR_BG, fg=COLOUR_LIGHT
        ).pack(pady=2)


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
        self.controller      = controller
        self.start_var       = tk.IntVar(value=0)
        self.destination_var = tk.IntVar(value=0)
        self._build_ui()

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
        ).pack(pady=(0, 14))

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

            # Station preview under each zone option
            station_list = ", ".join(zone["stations"])
            tk.Label(
                card,
                text=f"       Stations: {station_list}",
                font=FONT_SMALL, bg=COLOUR_PANEL, fg=COLOUR_LIGHT,
                wraplength=300, justify="left"
            ).pack(anchor="w", padx=8, pady=(0, 6))

    def _update_info(self):
        """Update the dynamic zones info label on any selection."""
        start = self.start_var.get()
        dest  = self.destination_var.get()

        if start != 0 and dest != 0:
            zones  = calculate_zones_travelled(start, dest)
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
        dest  = self.destination_var.get()

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

        self.controller.state["start_zone"]       = start
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
        self.inputs     = {}   # StringVars keyed by traveller type
        self._build_ui()

    def on_show(self):
        """Refresh the journey summary when this screen is revisited."""
        state = self.controller.state
        if state["start_zone"] and state["destination_zone"]:
            s     = ZONES[state["start_zone"]]["name"]
            d     = ZONES[state["destination_zone"]]["name"]
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
                "type.\nAt least one traveller must be entered."
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
        key   = t_type["key"]
        label = t_type["label"]
        fare  = t_type["fare"]

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
            text=f"Rate: {pence_to_display(fare)} per zone",
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

        Clamps minimum value at 0 to prevent negative counts.

        Args:
            var   (tk.StringVar): Variable bound to the entry field.
            delta (int)         : +1 to increment, -1 to decrement.
        """
        current = var.get().strip()
        if not current.isdigit():
            var.set("0")
            return
        var.set(str(max(0, int(current) + delta)))

    def _build_rate_table(self):
        """Build a compact fare rate reference summary."""
        frame = tk.Frame(self, bg=COLOUR_BG, pady=8)
        frame.pack(padx=60, fill="x")

        tk.Label(
            frame, text="Fare Rate Summary",
            font=FONT_SUBHEADING, bg=COLOUR_BG, fg=COLOUR_ACCENT
        ).pack(anchor="w")

        rates_text = "  |  ".join(
            f"{t['label']}: {pence_to_display(t['fare'])}/zone"
            for t in TRAVELLER_TYPES
        )
        tk.Label(
            frame, text=rates_text,
            font=FONT_SMALL, bg=COLOUR_BG, fg=COLOUR_LIGHT
        ).pack(anchor="w")

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
        total  = 0

        for t_type in TRAVELLER_TYPES:
            key   = t_type["key"]
            label = t_type["label"]
            raw   = self.inputs[key].get()

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

    Presents three payment options as large clickable tiles:
      - Card   : Card-reader simulation dialog
      - Cash   : Cash-insertion simulation dialog (with change calc)
      - PayPal : PayPal login/payment simulation dialog
    """

    def __init__(self, parent, controller):
        super().__init__(parent, bg=COLOUR_BG)
        self.controller   = controller
        self._total_pence = 0
        self._build_ui()

    def on_show(self):
        """Recompute and display the fare total each time screen appears."""
        self._update_total_label()

    def _update_total_label(self):
        """Compute and display the current journey grand total."""
        state = self.controller.state
        start = state["start_zone"]
        dest  = state["destination_zone"]
        travs = state["travellers"]

        if not start or not dest:
            return

        zones       = calculate_zones_travelled(start, dest)
        total_pence = sum(
            calculate_fare(t["fare"], zones, travs.get(t["key"], 0))
            for t in TRAVELLER_TYPES
        )

        self.total_label.config(
            text=(
                f"Journey Total:  {pence_to_display(total_pence)}"
                f"   ({zones} zone"
                f"{'s' if zones > 1 else ''} travelled)"
            )
        )
        self._total_pence = total_pence

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
            sub="Insert coins and notes",
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
        CardPaymentDialog(self, self.controller, self._total_pence)

    def _open_cash_dialog(self):
        """Open the cash insertion simulation dialog."""
        CashPaymentDialog(self, self.controller, self._total_pence)

    def _open_paypal_dialog(self):
        """Open the PayPal payment simulation dialog."""
        PayPalPaymentDialog(self, self.controller, self._total_pence)


# ===========================================================================
# PAYMENT DIALOG – CARD
# ===========================================================================

class CardPaymentDialog(tk.Toplevel):
    """
    Modal dialog simulating a card-reader terminal.

    Shows a canvas card-reader graphic and runs a progress animation
    before confirming payment and navigating to the receipt screen.
    """

    def __init__(self, parent, controller, total_pence: int):
        super().__init__(parent)
        self.controller  = controller
        self.total_pence = total_pence

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
            text=f"Amount Due:  {pence_to_display(self.total_pence)}",
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
            self.controller.state["payment_method"] = "card"
            self.after(15000, self._go_to_voucher)

    def _go_to_voucher(self):
        """Close dialog and navigate to the receipt screen."""
        self.destroy()
        self.controller.show_frame("VoucherScreen")


# ===========================================================================
# PAYMENT DIALOG – CASH
# ===========================================================================

class CashPaymentDialog(tk.Toplevel):
    """
    Modal dialog simulating a cash-insertion vending terminal.

    Denomination buttons let the user click to insert coins/notes.
    A live Inserted / Remaining display updates on each click.
    The Confirm button enables once the inserted total covers the fare.
    """

    DENOMINATIONS = [
        ("1p",    1),   ("2p",    2),   ("5p",    5),   ("10p",  10),
        ("20p",  20),   ("50p",  50),
        ("\u00a31",  100),  ("\u00a32",  200),
        ("\u00a35",  500),  ("\u00a310", 1000),
        ("\u00a320", 2000), ("\u00a350", 5000),
    ]

    def __init__(self, parent, controller, total_pence: int):
        super().__init__(parent)
        self.controller  = controller
        self.total_pence = total_pence
        self._inserted   = 0

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
            text=f"Amount Due:  {pence_to_display(self.total_pence)}",
            font=("Georgia", 17, "bold"),
            bg=COLOUR_BG, fg=COLOUR_ACCENT
        ).pack(pady=(14, 4))

        # Live inserted / remaining display
        info_frame = tk.Frame(self, bg=COLOUR_PANEL, padx=20, pady=10)
        info_frame.pack(padx=30, fill="x", pady=4)

        self.inserted_label = tk.Label(
            info_frame,
            text=f"Inserted: {pence_to_display(self._inserted)}",
            font=FONT_SUBHEADING, bg=COLOUR_PANEL, fg=COLOUR_WHITE
        )
        self.inserted_label.pack(side="left", expand=True)

        self.remaining_label = tk.Label(
            info_frame,
            text=f"Remaining: {pence_to_display(self.total_pence)}",
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
            self, text="Tap denominations to insert:",
            font=FONT_BODY, bg=COLOUR_BG, fg=COLOUR_LIGHT
        ).pack(pady=(4, 2))

        # Denomination buttons grid (6 columns)
        denom_frame = tk.Frame(self, bg=COLOUR_BG)
        denom_frame.pack(padx=30)

        for idx, (label, value) in enumerate(self.DENOMINATIONS):
            tk.Button(
                denom_frame, text=label,
                font=FONT_SUBHEADING, width=5,
                bg=COLOUR_CASH, fg=COLOUR_WHITE,
                relief="flat", cursor="hand2",
                command=lambda v=value: self._insert(v)
            ).grid(row=idx // 6, column=idx % 6, padx=4, pady=4)

        self.status_label = tk.Label(
            self,
            text="Insert cash using the buttons above.",
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

    def _insert(self, value_pence: int):
        """
        Add a denomination to the running inserted total.

        Args:
            value_pence (int): Denomination value in pence.
        """
        self._inserted += value_pence
        remaining = self.total_pence - self._inserted

        self.inserted_label.config(
            text=f"Inserted: {pence_to_display(self._inserted)}"
        )

        if remaining <= 0:
            change = abs(remaining)
            self.remaining_label.config(
                text=f"Change: {pence_to_display(change)}",
                fg=COLOUR_SUCCESS
            )
            self.status_label.config(
                text=(
                    f"\u2705  Covered!  "
                    f"Change due: {pence_to_display(change)}"
                ),
                fg=COLOUR_SUCCESS
            )
            self.confirm_btn.config(state="normal")
        else:
            self.remaining_label.config(
                text=f"Remaining: {pence_to_display(remaining)}",
                fg=COLOUR_DANGER
            )
            self.status_label.config(
                text=f"Still required: {pence_to_display(remaining)}",
                fg=COLOUR_LIGHT
            )

    def _confirm_payment(self):
        """Confirm cash payment and navigate to receipt screen."""
        self.controller.state["payment_method"] = "cash"
        self.destroy()
        self.controller.show_frame("VoucherScreen")


# ===========================================================================
# PAYMENT DIALOG – PAYPAL
# ===========================================================================

class PayPalPaymentDialog(tk.Toplevel):
    """
    Modal dialog simulating a PayPal secure-checkout flow.

    Renders a PayPal-branded login form. After clicking 'Log In & Pay',
    a progress animation confirms the transaction.
    """

    def __init__(self, parent, controller, total_pence: int):
        super().__init__(parent)
        self.controller  = controller
        self.total_pence = total_pence

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
            text=f"Amount:  {pence_to_display(self.total_pence)}",
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
            text="\U0001f512  Secured by TLS encryption",
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
            self.controller.state["payment_method"] = "paypal"
            self.after(800, self._go_to_voucher)

    def _go_to_voucher(self):
        """Close dialog and navigate to the receipt screen."""
        self.destroy()
        self.controller.show_frame("VoucherScreen")


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
        self.controller    = controller
        self._voucher_text = ""      # Cached text for print / PDF
        self._last_pdf     = None    # Path to last generated PDF file
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

        Regenerates the voucher text so the timestamp is always current.
        """
        self._generate_voucher_text()
        self._display_voucher_text()

    # -----------------------------------------------------------------------
    # Voucher text generation
    # -----------------------------------------------------------------------

    def _generate_voucher_text(self):
        """
        Compute all fares and build the formatted receipt string.

        Caches the result in self._voucher_text for reuse by the
        print and PDF functions.
        """
        state      = self.controller.state
        start_z    = state["start_zone"]
        dest_z     = state["destination_zone"]
        travellers = state["travellers"]
        payment    = state.get("payment_method", "unknown").upper()

        issue_time  = datetime.now()
        zones_count = calculate_zones_travelled(start_z, dest_z)
        start_name  = ZONES[start_z]["name"]
        dest_name   = ZONES[dest_z]["name"]

        width = 60
        line  = "=" * width
        thin  = "-" * width

        def centre(text: str) -> str:
            return text.center(width)

        lines = [
            line,
            centre("CENTRALA TRANSPORT AUTHORITY"),
            centre("OFFICIAL TRAVEL VOUCHER"),
            line,
            f"  Issued  : {issue_time.strftime('%A, %d %B %Y')}",
            f"  Time    : {issue_time.strftime('%H:%M:%S')}",
            f"  Ref     : CTA-"
            f"{issue_time.strftime('%Y%m%d-%H%M%S')}",
            thin,
            f"  Boarding    : {start_name} Zone (Zone {start_z})",
            f"  Destination : {dest_name} Zone (Zone {dest_z})",
            f"  Zones       : {zones_count} "
            f"zone{'s' if zones_count > 1 else ''} travelled",
            thin,
            centre("FARE BREAKDOWN"),
            thin,
            f"  {'Category':<12} {'Qty':>4}  "
            f"{'Rate/Zone':>10}  {'Zones':>5}  {'Total':>9}",
            thin,
        ]

        grand_pence = 0
        grand_pax   = 0

        for t in TRAVELLER_TYPES:
            count = travellers.get(t["key"], 0)
            if count == 0:
                continue

            total_p     = calculate_fare(t["fare"], zones_count, count)
            grand_pence += total_p
            grand_pax   += count

            lines.append(
                f"  {t['label']:<12} {count:>4}  "
                f"{pence_to_display(t['fare']):>10}  "
                f"{zones_count:>5}  "
                f"{pence_to_display(total_p):>9}"
            )

        lines += [
            thin,
            f"  {'TOTAL TRAVELLERS':<28} {grand_pax:>4}",
            f"  {'AMOUNT PAID':<28} "
            f"{pence_to_display(grand_pence):>10}",
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

        state      = self.controller.state
        start_z    = state["start_zone"]
        dest_z     = state["destination_zone"]
        travellers = state["travellers"]
        payment    = state.get("payment_method", "unknown").upper()

        issue_time  = datetime.now()
        zones_count = calculate_zones_travelled(start_z, dest_z)

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
        _navy   = colors.HexColor("#1B2A4A")
        _gold   = colors.HexColor("#F0A500")
        _white  = colors.white
        _green  = colors.HexColor("#27AE60")
        _light  = colors.HexColor("#C8D6E5")

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
        body_style = ParagraphStyle(
            "CTABody",
            parent=styles["Normal"],
            fontName="Helvetica",
            fontSize=10,
            textColor=_navy,
            spaceAfter=4,
        )
        label_style = ParagraphStyle(
            "CTALabel",
            parent=styles["Normal"],
            fontName="Helvetica-Bold",
            fontSize=10,
            textColor=_navy,
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
            ["Ref:",    f"CTA-{issue_time.strftime('%Y%m%d-%H%M%S')}"],
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

        fare_header = ["Category", "Qty", "Rate/Zone", "Zones", "Total"]
        fare_rows   = [fare_header]

        grand_pence = 0
        grand_pax   = 0

        for t in TRAVELLER_TYPES:
            count = travellers.get(t["key"], 0)
            if count == 0:
                continue
            total_p     = calculate_fare(t["fare"], zones_count, count)
            grand_pence += total_p
            grand_pax   += count
            fare_rows.append([
                t["label"],
                str(count),
                pence_to_display(t["fare"]),
                str(zones_count),
                pence_to_display(total_p),
            ])

        # Totals row
        fare_rows.append([
            "TOTAL", str(grand_pax), "", "", pence_to_display(grand_pence)
        ])

        col_w = [45 * mm, 15 * mm, 30 * mm, 20 * mm, 30 * mm]
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
        PDFPreviewWindow(self, pdf_path, self._voucher_text)

        # Also launch the OS default PDF viewer
        try:
            if os.name == "nt":
                os.startfile(pdf_path)
            elif os.uname().sysname == "Darwin":
                subprocess.Popen(["open", pdf_path])
            else:
                subprocess.Popen(["xdg-open", pdf_path])
        except Exception:
            pass   # Preview window already open; viewer launch is optional

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

    def __init__(self, parent, pdf_path: str, voucher_text: str):
        super().__init__(parent)
        self._pdf_path    = pdf_path
        self._voucher_txt = voucher_text

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
        margin         = 20   # canvas border around the page

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

        # Bind mouse-wheel scrolling
        canvas.bind_all("<MouseWheel>",
                        lambda e: canvas.yview_scroll(
                            -1 * (e.delta // 120), "units"
                        ))
        canvas.bind_all("<Button-4>",
                        lambda e: canvas.yview_scroll(-1, "units"))
        canvas.bind_all("<Button-5>",
                        lambda e: canvas.yview_scroll(1, "units"))

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
        _navy  = "#1B2A4A"
        _gold  = "#F0A500"
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

        y       = margin + 84   # Start y below header band
        lh      = 15            # Line height in pixels
        pad_x   = x0 + 28      # Left text margin
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
                canvas.create_text(
                    cx, y, text=stripped,
                    font=bold_fn, fill=_gold, anchor="w",
                    width=page_w - 40
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
        """Save the PDF file to a user-chosen location."""
        dest = filedialog.asksaveasfilename(
            defaultextension=".pdf",
            filetypes=[("PDF files", "*.pdf"), ("All files", "*.*")],
            initialfile="CTA_Voucher.pdf",
            title="Save PDF Receipt"
        )
        if dest:
            import shutil
            shutil.copy2(self._pdf_path, dest)
            messagebox.showinfo("Saved", f"PDF saved to:\n{dest}")

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
            messagebox.showerror(
                "Print Error",
                f"Could not print the PDF:\n{exc}"
            )


# ===========================================================================
# ENTRY POINT
# ===========================================================================

def main():
    """
    Application entry point.

    Creates the root CTATicketingApp instance and starts the Tkinter
    event loop. The loop runs indefinitely, processing GUI events
    until the user closes the window or clicks Exit.
    """
    app = CTATicketingApp()
    app.mainloop()


if __name__ == "__main__":
    main()
