# focus demo — run with:  browser-harness < ~/.claude/skills/focus/demo.py
import os
exec(open(os.path.expanduser("~/.claude/skills/focus/focus.py")).read())

focus_new_tab("https://en.wikipedia.org/wiki/Typst", "Demo: watching the agent work through Wikipedia")

focus_read("#mw-content-text .mw-parser-output p", "First paragraph — what is this page about?")
focus_shot("/tmp/focus-demo-1.png")

focus_type("#searchInput, input[name=search]", "Digital product passport", "Searching for a related topic")
focus_press("Enter", "Submitting the search")
wait_for_load()
focus_install()

focus_look("#firstHeading", "Landed on the result page")
focus_shot("/tmp/focus-demo-2.png")

focus_read("#mw-content-text .mw-parser-output p", "Reading the lead paragraph")
focus_say("Done — that is what the agent saw and did. Clearing the overlay.", "ok")
focus_shot("/tmp/focus-demo-3.png")
wait(1.5)
focus_clear()
print("demo finished; screenshots in /tmp/focus-demo-{1,2,3}.png")
