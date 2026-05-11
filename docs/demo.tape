# vhs tape — records the aidoctor demo GIF for the README hero.
#
# Run with: `vhs docs/demo.tape`
# Output:   `docs/demo.gif`
# Install vhs: https://github.com/charmbracelet/vhs

Output docs/demo.gif

Set Theme "Catppuccin Mocha"
Set FontSize 16
Set Width 1200
Set Height 700
Set Padding 20
Set Framerate 30
Set TypingSpeed 50ms

# Open with a clean prompt
Type "# Your agent writes bad Python. This catches it."
Enter
Sleep 1s

Type "pip install aidoctor"
Enter
Sleep 2s

Type "aidoctor scan ./examples/slop_app.py"
Enter
Sleep 4s

# Let the doctor face linger
Sleep 3s

# Show one of the rules in detail
Type "aidoctor scan --explain hardcoded-api-key"
Enter
Sleep 4s

# Show the install command
Type "aidoctor install"
Enter
Sleep 3s

# Show that it set up the skill in claude / cursor
Type "ls ~/.claude/skills/aidoctor/"
Enter
Sleep 2s

# Quick rescan after fix
Type "aidoctor scan ./examples/clean_app.py"
Enter
Sleep 3s
