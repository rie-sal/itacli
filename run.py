#!/usr/bin/env python3
"""itacli entry point.

    python3 run.py              open the menu
    python3 run.py listen       run the capture-hotkey daemon
    python3 run.py capture      run one capture cycle
    python3 run.py add "term" "meaning"   quick-add a card
"""
import sys

from itacli.app import main

if __name__ == "__main__":
    main(sys.argv[1:])
