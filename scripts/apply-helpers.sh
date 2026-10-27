# Browser helpers for applying with playwright-cli. Source from the repo root:
#   source scripts/apply-helpers.sh
# Needs a running session:  playwright-cli -s=apply open --headed --profile=search/chrome_profile/apply_profile https://www.linkedin.com/feed/
# Contact details come from profile.yaml; nothing personal is hardcoded here.

ROOT=$(git rev-parse --show-toplevel 2>/dev/null || pwd)
cd "$ROOT" || return
P="playwright-cli -s=${SESSION:-apply}"
eval "$(python3 - <<'PY'
import shlex, yaml
c = yaml.safe_load(open("profile.yaml"))["candidate"]
for k, v in {"FIRST": c["first_name"], "LAST": c["last_name"], "EMAIL": c["email"], "PHONE": c["phone"],
             "LINKEDIN": "https://" + c["linkedin"], "GITHUB": "https://" + c["github"],
             "CITY": c["city"], "CITY_OPTION": c["city_option"], "HEADER_LOC": c["header_location"]}.items():
    print(f"PF_{k}={shlex.quote(v)}")
PY
)"
PDF_NAME=$(python3 -c 'import yaml;print(yaml.safe_load(open("profile.yaml")).get("resume_pdf_name","Resume.pdf"))')

# snapf: take a snapshot, print its file path
snapf(){ $P snapshot >/dev/null 2>&1; ls -t .playwright-cli/*.yml | head -1; }

# resolve <job_id>: EASY <ref> | EXT <url> | APPLIED | CLOSED | NONE
resolve(){ $P goto "https://www.linkedin.com/jobs/view/$1/" >/dev/null 2>&1; sleep 4; local F; F=$(snapf)
  grep -q 'Application submitted' $F && { echo APPLIED; return; }
  local E; E=$(grep 'button "Easy Apply to this job"' $F | grep -o 'ref=e[0-9]*' | head -1 | cut -d= -f2); [ -n "$E" ] && { echo "EASY $E"; return; }
  local U; U=$(grep -A2 'link "Apply on company website"' $F | grep -o 'url=[^&]*' | head -1 | cut -c5-)
  [ -n "$U" ] && { python3 -c "import urllib.parse,sys;print('EXT',urllib.parse.unquote(sys.argv[1]))" "$U"; return; }
  grep -iqE "no longer accepting|not currently accepting" $F && { echo CLOSED; return; }
  grep -q 'link "Sign in"' $F && { echo "LOGGED_OUT"; return; }
  echo NONE; }

# ---------- LinkedIn Easy Apply ----------
_dialog(){ awk '/- dialog "Apply to/{if(!f){f=1; match($0,/^ */); ind=RLENGTH; print; next}} f{match($0,/^ */); if(RLENGTH<=ind) exit; print}' "$1"; }

# ea_step <resume.pdf> [cover.pdf]: handle email/resume/cover/follow on the current page; print fields + nav
ea_step(){ local F; F=$(snapf); local D; D=$(_dialog $F)
  local em; em=$(echo "$D" | grep 'combobox "Email address' | grep -o 'ref=e[0-9]*' | cut -d= -f2); [ -n "$em" ] && $P select $em "$PF_EMAIL" >/dev/null 2>&1
  local up; up=$(echo "$D" | grep 'button "Upload resume"' | grep -o 'ref=e[0-9]*' | cut -d= -f2)
  if [ -n "$up" ] && ! echo "$D" | grep -q "$(basename "$1")"; then $P click $up >/dev/null 2>&1; $P upload "$1" >/dev/null 2>&1; sleep 3; fi
  local cl; cl=$(echo "$D" | grep 'button "Upload cover letter"' | grep -o 'ref=e[0-9]*' | cut -d= -f2)
  if [ -n "$cl" ] && [ -n "$2" ] && ! echo "$D" | grep -q "$(basename "$2")"; then $P click $cl >/dev/null 2>&1; $P upload "$2" >/dev/null 2>&1; sleep 3; fi
  if echo "$D" | grep -q 'checkbox "Follow .*\[checked\]'; then local fo; fo=$(echo "$D" | grep -E 'paragraph \[ref=e[0-9]+\]: Follow ' | grep -o 'ref=e[0-9]*' | head -1 | cut -d= -f2); [ -n "$fo" ] && $P click $fo >/dev/null 2>&1; fi
  F=$(snapf); _dialog $F | grep -E 'paragraph \[ref=e[0-9]+\]: [0-9]+/[0-9]+ pages|textbox|combobox|radio |checkbox|button "(Next|Review|Submit application)"|generic \[ref=e[0-9]+\]: .*\?|paragraph \[ref=e[0-9]+\]: .*\?|\.pdf|error|required|Please enter|option .*selected' \
   | grep -vE 'Mark job as a top choice|Download|button "PDF |paragraph \[ref=e[0-9]+\]: [^ ]+\.pdf$|generic "[^"]+\.pdf"|radio "[^"]+\.(pdf|docx?)"$' | sed 's/^ *//' | cut -c1-170; }

# nav: click Next/Review/Submit
nav(){ local F; F=$(snapf); local R; R=$(grep -E 'button "(Submit application|Review|Next)"' $F | grep -o 'ref=e[0-9]*' | head -1 | cut -d= -f2); $P click $R >/dev/null 2>&1; sleep 2.5; }

# pick "<question substring>" "<option text>": tick the radio/checkbox option of a question
pick(){ $P eval "() => { const q=$(python3 -c 'import json,sys;print(json.dumps(sys.argv[1].lower()))' "$1"), a=$(python3 -c 'import json,sys;print(json.dumps(sys.argv[1].lower()))' "$2");
  const opt = i => (i.parentElement.parentElement.innerText||'').trim().toLowerCase();
  const ins=[...document.querySelectorAll('input[type=radio],input[type=checkbox]')].filter(i => ((i.getAttribute('aria-label')||'')+' '+(i.closest('fieldset')?.innerText||'')).toLowerCase().includes(q));
  if(!ins.length) return 'no inputs for '+q;
  const hit=ins.find(i=>opt(i)===a); if(!hit) return 'no option '+a+' in: '+ins.map(opt).slice(0,15).join('|');
  if(!hit.checked) hit.click(); return 'ok '+a+' checked='+hit.checked; }" 2>&1 | sed -n 2p; }

# city_fill: answer a required "Location (city)" typeahead with profile city
city_fill(){ local F; F=$(snapf); local C; C=$(grep -E 'textbox "Enter city or location"' $F | grep -o 'ref=e[0-9]*' | head -1 | cut -d= -f2); [ -z "$C" ] && return 0
  grep -qE 'Location \(city\)\*|This field is required' $F || return 0
  $P fill $C "" >/dev/null 2>&1; $P click $C >/dev/null 2>&1; $P type "$PF_CITY" >/dev/null 2>&1; sleep 2.5; F=$(snapf)
  local R; R=$(grep -F "option \"$PF_CITY_OPTION\"" $F | grep -o 'ref=e[0-9]*' | head -1 | cut -d= -f2); [ -n "$R" ] && $P click $R >/dev/null 2>&1; sleep 1; }

# join_terms: accept JOIN's terms radio ("Yes" after the privacy-policy link)
join_terms(){ local F; F=$(snapf); local R; R=$(awk '/join.com\/(de\/datenschutz|privacy-policy)/{f=1} f && /paragraph \[ref=e[0-9]+\]: "?(Yes|Ja)"?$/{print; exit}' $F | grep -o 'ref=e[0-9]*' | cut -d= -f2); [ -n "$R" ] && $P click $R >/dev/null 2>&1; }

# consent: tick unchecked "I consent/Confirmed/I agree/I acknowledge" checkboxes
consent(){ local F; F=$(snapf); for r in $(grep -B2 -E 'paragraph \[ref=e[0-9]+\]: (I consent|Confirmed|I agree|I acknowledge|I Agree|Acknowledge)' $F | grep -A2 -E 'checkbox( \[active\])?$' | grep -oE 'paragraph \[ref=e[0-9]+\]' | grep -o 'e[0-9]*'); do $P click $r >/dev/null 2>&1; done; }

# ea_go <job_id> <resume>: open the job and its Easy Apply dialog
ea_go(){ local F0; F0=$(snapf); local NN; NN=$(grep 'button "Not now"' $F0 | grep -o 'ref=e[0-9]*' | head -1 | cut -d= -f2); [ -n "$NN" ] && $P click $NN >/dev/null 2>&1; $P press Escape >/dev/null 2>&1
  local r; r=$(resolve $1); echo "$r"; [ "${r%% *}" = EASY ] || return 1
  $P click ${r#EASY } >/dev/null 2>&1; sleep 3; local F; F=$(snapf)
  grep -q 'Continue applying' $F && { $P click $(grep 'link "Continue applying"' $F | grep -o 'ref=e[0-9]*' | cut -d= -f2) >/dev/null 2>&1; sleep 3; }
  ea_step $2 >/dev/null; }

# ea_auto_cont <resume>: step through pages; stop on unanswered fields. SENT | SUBMIT? | NEEDS INPUT | LOOPED
ea_auto_cont(){ for i in 1 2 3 4 5 6 7 8 9 10 11 12 13 14 15; do
    city_fill; local O; O=$(ea_step "$1")
    if echo "$O" | grep -q 'button "Submit application"'; then nav; sleep 2; local F; F=$(snapf)
      grep -q 'Your application was sent' $F && { echo SENT; $P press Escape >/dev/null 2>&1; return 0; }; echo "SUBMIT?"; return 2; fi
    local empty; empty=$(echo "$O" | grep -v "Enter city or location" | grep -cE 'textbox "[^"]*" \[ref=e[0-9]+\]$|option "Select an option" \[disabled\] \[selected\]')
    local radq; radq=$(echo "$O" | grep -E '^- radio "' | sed 's/^\(- radio "[^"]*"\).*/\1/' | sort -u | wc -l)
    local radc; radc=$(echo "$O" | grep -cE '^- radio ".*\[checked\]')
    if [ "$empty" -gt 0 ] || [ "$radq" -gt "$radc" ]; then echo "NEEDS INPUT:"; echo "$O" | grep -vE '^- checkbox$'; return 3; fi
    nav; done; echo LOOPED; return 4; }

# a1 <job_id> <key>: Easy Apply with output/<id>-<key>/<Resume>_<key>.pdf and record the result
a1(){ local R=.claude/skills/resume-gen/output/$1-$2/${PDF_NAME%.pdf}_$2.pdf; local out
  out=$(ea_go $1 "$R" | head -1); case "$out" in EASY*) out=$(ea_auto_cont "$R");; esac
  echo "## $1 $2"; echo "$out" | head -30
  case "$out" in SENT*) python3 scripts/tracker.py mark $1 --status Applied --notes "Submitted $(date +%F) via Easy Apply. Resume: $R" >/dev/null;;
    CLOSED*) python3 scripts/tracker.py mark $1 --status Closed >/dev/null;;
    APPLIED*) python3 scripts/tracker.py mark $1 --status Applied --notes "Already applied" >/dev/null;; esac; }

# fin: after answering a NEEDS INPUT page, tick consents and continue to submit
fin(){ consent; local o; o=$(ea_auto_cont x); if echo "$o" | grep -q LOOPED; then consent; o=$(ea_auto_cont x); fi; echo "$o" | tail -3; }

# ---------- External ATS forms ----------
_ref(){ grep -E "$2" "$1" | grep -o 'ref=e[0-9]*' | head -1 | cut -d= -f2; }

# gp <ref> <option> [typed]: Greenhouse react-select pick
gp(){ $P click $1 >/dev/null 2>&1; [ -n "$3" ] && $P type "$3" >/dev/null; sleep 1; local F; F=$(snapf)
  local R; R=$(grep -A60 'listbox' $F | grep -E "option \"$2" | grep -o 'ref=e[0-9]*' | head -1 | cut -d= -f2)
  [ -n "$R" ] && { $P click $R >/dev/null 2>&1; echo "ok $2"; } || { echo "miss $2:"; grep -A20 'listbox' $F | grep option | head -6; $P press Escape >/dev/null; }; }

# personio <url> <resume> [cover]: fill common Personio fields + uploads; print what's left
personio(){ $P goto "$1" >/dev/null 2>&1; sleep 6; local F; F=$(snapf); local u; u=$($P eval "() => location.href" 2>&1 | sed -n 2p)
  case "$u" in *"/apply"*) ;; *) local A; A=$(_ref $F 'link "Apply[^"]*"|button "Apply[^"]*"|link "Jetzt bewerben'); [ -n "$A" ] && { $P click $A >/dev/null 2>&1; sleep 4; };; esac
  $P run-code "async page => { const f = page.locator('input[type=file]'); const n = await f.count(); await f.nth(0).setInputFiles('$PWD/$2'); if ('$3' && n > 1) await f.nth(1).setInputFiles('$PWD/$3'); return 'files '+n; }" 2>&1 | grep -E '^"'; sleep 3
  F=$(snapf); local x  # fill after uploads: Personio re-renders and drops earlier text
  x=$(_ref $F 'textbox "First"'); [ -n "$x" ] && $P fill $x "$PF_FIRST" >/dev/null; x=$(_ref $F 'textbox "Last"'); [ -n "$x" ] && $P fill $x "$PF_LAST" >/dev/null
  x=$(_ref $F 'textbox "Email'); [ -n "$x" ] && $P fill $x "$PF_EMAIL" >/dev/null; x=$(_ref $F 'textbox "Phone'); [ -n "$x" ] && $P fill $x "$PF_PHONE" >/dev/null
  x=$(_ref $F 'textbox "LinkedIn'); [ -n "$x" ] && $P fill $x "$PF_LINKEDIN" >/dev/null
  x=$(_ref $F 'textbox "(Available from|Earliest|Start date)'); [ -n "$x" ] && { $P click $x >/dev/null; $P type "$(date -d '+7 days' +%d.%m.%Y)" >/dev/null; $P press Tab >/dev/null; }
  F=$(snapf); grep -E 'textbox|combobox|radio|checkbox|button "Submit|\.pdf|\(required\)' $F | grep -vE 'Select language' | cut -c1-170 | head -30; }

# ashby <application url> <resume>: fill common Ashby fields + resume; print what's left
ashby(){ $P goto "$1" >/dev/null 2>&1; sleep 6
  $P run-code "async page => { const f = page.locator('input[type=file]'); const n = await f.count(); await f.nth(n>1?1:0).setInputFiles('$PWD/$2'); return 'files '+n; }" 2>&1 | grep -E '^"'; sleep 3
  local F; F=$(snapf); local x
  x=$(_ref $F 'textbox "(Full name|Name)\*?"'); [ -n "$x" ] && $P fill $x "$PF_FIRST $PF_LAST" >/dev/null
  x=$(_ref $F 'textbox "(Email|Email address)\*?"'); [ -n "$x" ] && $P fill $x "$PF_EMAIL" >/dev/null
  x=$(_ref $F 'textbox "Phone[^"]*"'); [ -n "$x" ] && $P fill $x "$PF_PHONE" >/dev/null
  x=$(_ref $F 'textbox "[^"]*LinkedIn[^"]*"'); [ -n "$x" ] && $P fill $x "$PF_LINKEDIN" >/dev/null
  x=$(_ref $F 'textbox "[^"]*GitHub[^"]*"'); [ -n "$x" ] && $P fill $x "$PF_GITHUB" >/dev/null
  F=$(snapf); grep -E 'textbox|combobox|radio|checkbox|spinbutton|button "(Yes|No)"|generic \[ref=e[0-9]+\]: .*[?*]$|\.pdf' $F | cut -c1-170 | head -40; }

# ayn "<question substring>" Yes|No: click an Ashby yes/no button (re-click before submit; they can reset)
ayn(){ $P run-code "async page => { const box = page.locator('div', {hasText: '$1'}).filter({has: page.getByRole('button',{name:'$2',exact:true})}).last(); await box.getByRole('button',{name:'$2',exact:true}).click(); return 'ok $1=$2'; }" 2>&1 | grep -E '^"|rror' | head -1; }

ashby_submit(){ local F; F=$(snapf); $P click $(grep 'button "Submit Application"' $F | grep -o 'ref=e[0-9]*' | cut -d= -f2) >/dev/null 2>&1; sleep 7; F=$(snapf)
  grep -iE "success|successfully|missing entry|required|captcha" $F | head -3; grep -A2 'Missing entry' $F | grep button | cut -c1-120; }

# upload <resume> [index]: set a file input directly (works when "Attach" buttons open native dialogs)
upload_file(){ $P run-code "async page => { await page.locator('input[type=file]').nth(${2:-0}).setInputFiles('$PWD/$1'); return 'ok'; }" 2>&1 | grep -E '^"|rror'; }
