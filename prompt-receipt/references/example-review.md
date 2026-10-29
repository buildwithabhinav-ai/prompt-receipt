# Example review (from the `vague-fix-chat` test fixture)

Use this as a model for tone, length and layout. Names and numbers come from that fixture; replace them with the user's own.

---

## Chat review: 5 prompts, 9.7M tokens, about $4.20 · Prompt score 60 (D)

**Biggest lesson:** two vague prompts ("fix" and "make the website better and add everything properly") caused 64% of this chat's cost, and "still not working" was a repeat of the first one. Together, rework was about 35% of the bill.

**What you did well:** Your last real prompt (the `Upload.jsx` 500 error) is a model prompt. You gave the file, pasted the traceback, said what the JSON should look like and limited the change to `app.py`. Claude fixed it in 3 requests; the vague ones needed 14 to 16 each.

### Token ledger
| | tokens |
|---|---|
| Fresh input | 2,200 |
| Cache writes | 88,000 |
| Cache reads (earlier chat re-read) | 9,571,000 (99%) |
| Output | 17,600 |
| Peak context | 422,050 |

Almost everything is Claude re-reading the earlier chat on each step. That is why a long chat makes later prompts pricier: the same sentence costs more at message 40 than at message 2.

### Costliest prompts, fixed

**1. `fix` (15% of cost, 14 requests, then a correction)**
Missing: which file, what error, what you expected. Claude searched the project and re-read `app.py` 3 times to guess.
Add: file name, the exact error text, the step that triggers it.
Better: `In backend/app.py the /api/predict route returns 500 when I upload a jpg. Error: <paste traceback>. It should return {disease, confidence}. Only change app.py.`
Likely saved: most of the 11 file reads and the follow-up "still not working".

**2. `make the website better and add everything properly` (49% of cost, 16 requests)**
Missing: what "better" means, which page, a finish line. "Everything" has no end, so Claude kept exploring.
Better: split it into one goal per message: `Upload.jsx: show a spinner while /api/predict runs and an error message on 400/500. Reuse styles.css.` then a second message for the next screen.
Likely saved: the open-ended search (8 Glob calls) and the later cleanup.

**3. `still not working` (20% of cost)**
A correction. It cost as much as a fresh task because the whole context was re-read. When a fix fails, send the new error text, not just the feeling. `Still failing after your change. New error: <paste>. Same request as before.`

### Habits that would save the most
- **Start a new chat at message 4.** You moved from fixing to a different question with 400k tokens of context behind you; a fresh chat with a 5-line summary would have cost a fraction.
- **`CLAUDE.md`:** `app.py` and `Upload.jsx` were each opened 15+ times. Add: stack, how to run backend and frontend, and where each feature lives, once.

### Next-chat starter (fill the <> parts)
    Project: crop disease prediction. Stack: <Flask + React>. Done: /api/predict returns JSON. Pending: <...>.
    Run: <backend cmd>, <frontend cmd>. Task now: <one goal>.

Save this review as `prompt-receipt-<date>.md`? I only write it with your yes.
