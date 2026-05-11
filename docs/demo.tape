# vhs tape — records the aidoctor demo GIF for the README hero.
#
# Run from project root: `vhs docs/demo.tape`
# Output:                `docs/demo.gif`

Output docs/demo.gif

Set Theme "Catppuccin Mocha"
Set FontSize 16
Set Width 1200
Set Height 760
Set Padding 20
Set Framerate 30
Set TypingSpeed 60ms
Set Shell "bash"

# Activate the venv silently so the `aidoctor` command resolves.
Hide
Type "source .venv/bin/activate"
Enter
Type "clear"
Enter
Show

Sleep 800ms
Type "# Better Python from your AI assistant."
Sleep 1s
Enter

Sleep 600ms
Type "aidoctor scan tests/fixtures/sample_repo"
Sleep 800ms
Enter

Sleep 6s

Type "aidoctor scan --explain hardcoded-api-key"
Sleep 800ms
Enter

Sleep 4s

Type "aidoctor install"
Sleep 800ms
Enter

Sleep 3s

Type "# Skill installed in 5 agent dirs · /aidoctor lives in 3 of them"
Sleep 2500ms
Enter
Sleep 2s
