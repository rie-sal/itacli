"""Terminal rendering. Horizontal, minimal rules, roomy, shifted right,
fully justified within a fixed measure (SPECS §6). Pure stdlib.

Layout contract:
  - INDENT shifts the whole block right (a left margin).
  - WIDTH is the measure; NOTHING prints past it (a hard right margin).
  - Data rows are fully justified: a fixed label column on the left, then the
    row's items distributed so the last item lands flush on the right margin.
"""
import os

INDENT = "     "   # left margin
WIDTH = 72         # the measure (also the length of every rule)
LABEL_W = 12       # label column; row content starts here
BAR_WIDTH = 30     # proficiency thermometer length


def clear():
    os.system("cls" if os.name == "nt" else "clear")


def rule():
    print(INDENT + "-" * WIDTH)


def line(text=""):
    print(INDENT + text)


def blank():
    print()


def two_sided(left, right):
    """Label flush left, value flush right, filling the measure."""
    pad = WIDTH - len(left) - len(right)
    print(INDENT + left + " " * max(1, pad) + right)


def justify_row(label, items):
    """Fixed label column, then items distributed to fill to the right margin."""
    head = label.ljust(LABEL_W)
    area = WIDTH - LABEL_W
    if len(items) <= 1:
        print(INDENT + head + (items[0] if items else ""))
        return
    total = sum(len(i) for i in items)
    gaps = len(items) - 1
    space = area - total
    if space < gaps:                      # too tight to justify; single-space it
        print(INDENT + head + " ".join(items))
        return
    base, extra = divmod(space, gaps)
    out = items[0]
    for i, it in enumerate(items[1:]):
        out += " " * (base + (1 if i < extra else 0)) + it
    print(INDENT + head + out)


def bar(fraction):
    filled = max(0, min(BAR_WIDTH, round(fraction * BAR_WIDTH)))
    return "|" + "#" * filled + "-" * (BAR_WIDTH - filled) + "|"


def home(data):
    clear()
    blank()
    two_sided("ITACLI · Italian", "Day %d" % data["day"])
    blank()
    rule()
    blank()
    two_sided("CEFR level", "%s   (assessed %s)"
              % (data["cefr_level"], data["cefr_assessed_ago"]))
    blank()
    pct = int(round(data["prof_fraction"] * 100))
    two_sided("Proficiency".ljust(LABEL_W) + bar(data["prof_fraction"]),
              "%d%% toward %s" % (pct, data["prof_next_band"]))
    blank()
    justify_row("Skills", ["%s %s" % kv for kv in data["skills"].items()])
    blank()
    justify_row("Focus", data["focus"])
    blank()
    justify_row("Plan", ["%s %d min" % p for p in data["plan"]])
    blank()
    rule()
    blank()
    line("1  Daily session                     6  Assessment & CEFR")
    line("2  Reading                           7  Progress & statistics")
    line("3  Grammar                           8  Content library")
    line("4  Vocabulary (Anki)                 9  Settings")
    line("5  Listening                         q  Quit")
    blank()
    rule()
    blank()


def panel(title, body_lines, footer="press Enter to return"):
    clear()
    blank()
    line(title)
    blank()
    rule()
    blank()
    for ln in body_lines:
        line(ln)
    blank()
    rule()
    blank()
    line(footer)
    try:
        input(INDENT + "> ")
    except EOFError:
        pass
