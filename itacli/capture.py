"""Global-hotkey word capture (SPECS §10). Stub.

ONE keyboard shortcut triggers the entire pipeline, in ANY app (Discord and
WhatsApp included), by simulating copy and reading the clipboard:

    capture text
      -> translate / show (native macOS Translate where the OS exposes it;
         Apple's on-device engine via Shortcuts elsewhere; no LLM)
      -> spaCy splits into sentence fragments (tokens, lemmas, noun-chunks)
      -> dedupe against existing Anki notes + a frequency threshold
      -> smart-save the relevant cards to Anki

The hotkey itself is registered by a small external daemon (Hammerspoon or a
pynput/Quartz helper, needs Accessibility permission); it calls into here.
"""


def capture_pipeline(selected_text):
    """Run the full capture -> chunk -> dedupe -> save pipeline. Stub."""
    # TODO: implement the five stages above.
    raise NotImplementedError


def translate(text):
    """Word gloss (dictionary) + phrase via Apple on-device / OPUS-MT. Stub."""
    raise NotImplementedError
