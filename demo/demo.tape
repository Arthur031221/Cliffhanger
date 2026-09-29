# Render with: vhs demo/demo.tape  (from the repository root)
Output demo/demo.gif

Set Shell "bash"
Set FontSize 15
Set Width 1180
Set Height 480
Set Padding 18
Set TypingSpeed 25ms
Set Theme "Catppuccin Mocha"

Hide
Type "export CLIFFHANGER_HOME=$(mktemp -d) PATH=$PWD/bin:$PATH PS1='$ ' && clear" Enter
Show

Type "# The agent ends its turn with an offer instead of the work:" Enter
Type "jq -r .last_assistant_message demo/payloads/offer.json" Enter
Sleep 1.5s
Type "python3 hooks/cliffhanger.py < demo/payloads/offer.json | jq ." Enter
Sleep 3s
Type "# An honest blocker goes through:" Enter
Type "python3 hooks/cliffhanger.py < demo/payloads/blocked.json; echo exit=$?" Enter
Sleep 1.5s
Type "python3 hooks/cliffhanger.py < demo/payloads/unverified.json > /dev/null; python3 hooks/cliffhanger.py < demo/payloads/done.json" Enter
Sleep 1s
Type "clear && cliffhanger stats" Enter
Sleep 4s
