"""Terminal rendering. Horizontal, minimal rules, roomy, shifted right,
fully justified within a fixed measure (SPECS §6). Pure stdlib.

Layout contract:
  - INDENT shifts the whole block right (a left margin).
  - WIDTH is the measure; NOTHING prints past it (a hard right margin).
  - Data rows are fully justified: a fixed label column on the left, then the
    row's items distributed so the last item lands flush on the right margin.
"""
import os
import sys
import time

INDENT = "     "   # left margin
WIDTH = 72         # the measure (also the length of every rule)
LABEL_W = 12       # label column; row content starts here
BAR_WIDTH = 30     # proficiency thermometer length

# Italian tricolore (only emitted to a real terminal, never into pipes/tests,
# so the justified-layout math is never thrown off by escape codes).
_GREEN, _WHITE, _RED, _RESET = "\033[32m", "\033[97m", "\033[31m", "\033[0m"


def _colour_on():
    return sys.stdout.isatty()


def tricolore(s):
    """Colour a string across green / white / red bands (a terminal only)."""
    if not _colour_on() or not s:
        return s
    n = len(s)
    out = []
    for i, ch in enumerate(s):
        band = _GREEN if i < n / 3 else (_WHITE if i < 2 * n / 3 else _RED)
        out.append(band + ch)
    return "".join(out) + _RESET


_BANNER = [
    "      _ _             _ _",
    "     (_) |_ __ _  ___| (_)",
    "     | | __/ _` |/ __| | |",
    "     | | || (_| | (__| | |",
    "     |_|\\__\\__,_|\\___|_|_|",
]


def banner():
    """Print the itacli word-mark in vertical tricolore bands."""
    w = max(len(l) for l in _BANNER)
    on = _colour_on()
    for line in _BANNER:
        if not on:
            print(INDENT + line)
            continue
        out = []
        for i, ch in enumerate(line):
            band = _GREEN if i < w / 3 else (_WHITE if i < 2 * w / 3 else _RED)
            out.append(band + ch)
        print(INDENT + "".join(out) + _RESET)


def clear():
    os.system("cls" if os.name == "nt" else "clear")


def rule():
    print(INDENT + "-" * WIDTH)


def line(text=""):
    print(INDENT + text)


def blank():
    print()


def slow(text="", delay=0.018):
    """Typewriter print (only when attached to a terminal; instant otherwise)."""
    if delay and sys.stdout.isatty():
        sys.stdout.write(INDENT)
        for ch in text:
            sys.stdout.write(ch)
            sys.stdout.flush()
            time.sleep(delay)
        sys.stdout.write("\n")
    else:
        print(INDENT + text)


def two_sided(left, right, pad_ref=None):
    """Label flush left, value flush right, filling the measure. pad_ref is the
    plain text to measure when `left` contains invisible colour codes."""
    ref = pad_ref if pad_ref is not None else left
    pad = WIDTH - len(ref) - len(right)
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
    plain = "ITACLI · Italian"
    if data.get("name"):
        plain = "ITACLI · Italian   —   ciao, %s" % data["name"]
    display = tricolore("ITACLI") + plain[len("ITACLI"):]
    two_sided(display, "Day %d" % data["day"], pad_ref=plain)
    blank()
    rule()
    blank()
    if data.get("cefr_level"):
        two_sided("CEFR level", "%s   (assessed %s)"
                  % (data["cefr_level"], data["cefr_assessed"]))
    else:
        two_sided("CEFR level", "not assessed yet")
    blank()
    two_sided("Proficiency".ljust(LABEL_W) + bar(data.get("prof_fraction", 0.0)),
              data.get("prof_label", "no data yet"))
    blank()
    justify_row("Vocabulary", ["%d words saved" % data["vocab_count"]])
    blank()
    justify_row("Focus", data["weak"] if data.get("weak") else ["nothing tracked yet"])
    blank()
    if data.get("plan"):
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
