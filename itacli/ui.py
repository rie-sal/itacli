"""Terminal rendering. Horizontal, minimal rules, roomy, shifted right,
justified, wide (SPECS §6). Pure stdlib so it runs with zero installs.
"""
import os

INDENT = "     "          # shift the block toward the right
WIDTH = 70               # content width (also the length of the rules)
BAR_WIDTH = 30           # proficiency thermometer length


def clear():
    os.system("cls" if os.name == "nt" else "clear")


def rule():
    print(INDENT + "-" * WIDTH)


def line(text=""):
    print(INDENT + text)


def justified(left, right):
    """Left label, right value, filling the full content width."""
    pad = WIDTH - len(left) - len(right)
    if pad < 1:
        pad = 1
    print(INDENT + left + " " * pad + right)


def bar(fraction):
    filled = max(0, min(BAR_WIDTH, round(fraction * BAR_WIDTH)))
    return "|" + "#" * filled + "-" * (BAR_WIDTH - filled) + "|"


def blank():
    print()


def home(data):
    clear()
    blank()
    justified("ITACLI · Italian", "Day %d" % data["day"])
    blank()
    rule()
    blank()
    justified("CEFR level", "%s   (assessed %s)" % (data["cefr_level"], data["cefr_assessed_ago"]))
    blank()
    pct = int(round(data["prof_fraction"] * 100))
    justified("Proficiency    " + bar(data["prof_fraction"]),
              "%d%% toward %s" % (pct, data["prof_next_band"]))
    blank()
    skills = "     ".join("%s %s" % (k, v) for k, v in data["skills"].items())
    line("Skills         " + skills)
    blank()
    line("Focus          " + "   ·   ".join(data["focus"]))
    blank()
    plan = "    ".join("%s %d min" % (name, mins) for name, mins in data["plan"])
    line("Plan           " + plan)
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
    """A simple stub screen used by every not-yet-built pillar."""
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
