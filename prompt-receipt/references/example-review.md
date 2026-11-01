# Example review (from the `vague-fix-chat` test fixture)

Use this as a model for tone, length and layout. Names and numbers come from that fixture; replace them with the user's own. Notice what it does **not** do: no flag names, no jargon, no blame, and every problem has its fix right next to it.

---

## Prompt Receipt: 5 prompts, about 9.7 million tokens (about $4.20)

**Grade D. Costly habits. Fixing two or three prompts will help most.**

⚠ **Heads-up**
- This chat grew very long (about 420,000 tokens by the end). Claude re-reads all of it on every message, so each one cost more. Start a new chat when you change topic.
- About a third of the cost (35%) went on redoing work after "still not working". Next time, paste the exact error and say what you expected.

**What went well**
Your last real prompt (the `Upload.jsx` 500 error) was a model prompt. It named the file, pasted the error, said what the result should look like, and limited the change to `app.py`. Claude fixed it in 3 steps. The vague ones needed 14 to 16.

**Where the tokens went**
A token is a small chunk of text Claude reads or writes. You pay for each one. About 99% of them were Claude re-reading the chat, and only a tiny part was your typing. The biggest single prompt was #3, at about half the cost.

**Fix these prompts**

**1. "make the website better and add everything properly"** (about 49% of the cost)
- Missing: it didn't say which page, what "better" means, or when it is done. "Everything" has no end, so Claude kept exploring.
- Try: `Upload.jsx: show a spinner while /api/predict runs and an error message on 400 or 500. Reuse styles.css.` Then send a second message for the next screen.
- Probably avoids (estimate): the open-ended search (8 file searches) and the cleanup afterwards.

**2. "still not working"** (about 20%)
- Missing: the new error. Claude had to start from scratch, and the whole chat was re-read again.
- Try: `Still failing after your change. New error: <paste>. Same request as before.`

**3. "fix"** (about 15%)
- Missing: which file, what error, and what you expected. Claude searched the project and opened `app.py` 3 times to guess.
- Try: `In backend/app.py the /api/predict route returns 500 when I upload a jpg. Error: <paste>. It should return {disease, confidence}. Only change app.py.`
- Probably avoids (estimate): most of the 11 file reads and the follow-up "still not working".

**Do this next time**
- **Start a new chat at message 4.** You changed topic with about 420,000 tokens behind you. A fresh chat with a five-line summary costs a fraction.
- **Put how to run the project in a `CLAUDE.md` file.** `app.py` and `Upload.jsx` were each opened 15+ times.

Want a paste-ready summary to start your next chat? Or I can explain any line, or save this as `prompt-receipt-<date>.md` (I only write it with your yes).

*Dollar amounts per prompt are estimates. The log keeps one total for the chat, shared out by token weight.*

---

## Short-answer version

When the user only asks "was that expensive?", do not write the whole receipt:

> About 9.7 million tokens, about $4.20. Nearly all of it was Claude re-reading a chat that grew very long, and two vague prompts ("fix", "make it better and add everything") caused most of the rest. Heads-up: start a new chat when you change topic. Want the full receipt?
