---
name: prompt-receipt
description: Reviews a finished Claude Code chat in plain English. Shows how many tokens it used, which prompts cost the most, and what to type instead, with calm heads-ups such as "this chat got too long" or "that number is only an estimate". Use it when the user says "review this chat", "prompt receipt", "where did my tokens go", "why did that use so much", "am I hitting my limit", "why is Claude slow or expensive", "how can I prompt better", or signs off after a long build or debug session. Also offer it in one line (never run it unasked) when a chat has run very long or the user is about to start a new topic. Do not use it for help with a problem still in progress, or for patterns across many chats (that is prompt-postmortem).
---

# Prompt Receipt

A receipt for a chat. It shows what the chat cost, which few prompts caused most of it, and the exact words to use next time.

Most tokens are not spent on what you type. They are spent on Claude **re-reading the whole earlier chat on every message**. A one-word "fix" also makes Claude search the whole project to guess what you meant. This skill finds those moments and fixes them.

The reader may be new to coding. Write for them.

## When to use it

**Run it** when the user:
- asks for a review of the chat, or for "prompt receipt";
- asks where tokens or money went, or why something was slow, expensive or hit a limit;
- asks how to prompt better, or what they did wrong;
- signs off after a long session ("thanks, that's all", "done for today").

**Offer it, do not run it**, in one line, when the chat has run very long, the user says it feels slow or costly, or they are about to start a different topic. Example: "This chat is getting long. Want a Prompt Receipt before we move on?" Ask once. If they say no, do not ask again.

**Do not use it** when the user needs help with a problem right now (fix that first), or wants patterns across many chats (point them to `prompt-postmortem`).

## How to write it (the plain-words rules)

Everything the user reads follows these rules. They matter more than any other detail here.

1. **Short sentences, everyday words.** Aim for a 13-year-old's reading level. No jargon.
2. **Explain "token" once**, the first time: "a token is a small chunk of text Claude reads or writes. You pay for each one."
3. **Never show internal names.** Do not print `no_target`, `cache_read`, `ctx_peak` or any flag name. Translate:

   | Internal | Say this |
   |---|---|
   | `no_target` | "didn't say which file or page" |
   | `problem_without_evidence` | "said it was broken but didn't paste the error" |
   | `vague_words` | "used a word like 'properly' or 'better' without saying what it means" |
   | `too_short` | "too short for Claude to know what to do" |
   | `multi_task` | "asked for several things at once" |
   | `no_expected_outcome` | "didn't say what 'done' looks like" |
   | cache reads | "Claude re-reading the chat" |
   | context | "how long the chat had grown" |

4. **No blame.** Say what was missing, then what to type. "This one didn't say which file" and never "this was a bad prompt".
5. **Every problem comes with its fix** in the same breath.
6. **Be calm.** A heads-up is a heads-up, not an alarm. No capital letters, no "WARNING!".
7. **Numbers:** round them ("about 9.7 million tokens", "about half"). Say "about" and "estimate". Never "exactly".

## Step 1: get the numbers

Run the bundled script. It only reads files on this computer and sends nothing anywhere:

    python3 -I "${CLAUDE_SKILL_DIR}/scripts/analyze_chat.py" --format table

(If `${CLAUDE_SKILL_DIR}` was not filled in, use the folder this skill loaded from.) With no options it reviews the newest chat in the current folder. Then run it once without `--format` to get the full details as JSON, including a ready-made `warnings` list and a one-line `verdict`.

- Wrong chat? `--list` shows recent chats. Use `--session <id>`. For another project use `--project-dir ~/.claude/projects/<folder>`.
- No log file (claude.ai, Cowork, or none found)? Do not stop. Review from the conversation itself: list the user's prompts, estimate tokens as characters divided by 4, and say clearly at the top: "These numbers are estimates."

Read [references/rubric.md](references/rubric.md) once to know what the numbers do and do not prove. The script's flags are blunt rules, so you are the judge. Drop any flag that does not fit (a short "fix" right after Claude asked "should I fix it?" is fine) and say so.

## Step 2: write the receipt

Use exactly this order and keep the whole thing to **one or two screens**. [references/example-review.md](references/example-review.md) shows the tone and length.

**1. Title and verdict (2 lines).** `Prompt Receipt: <N> prompts, about <X> million tokens (about $<cost> if the log has it)`, then the grade with the script's `verdict`. Example: "Grade D. Costly habits. Fixing two or three prompts will help most."

**2. Heads-up (only if the script gave warnings).** Show **at most three**, most serious first (`alert`, then `warn`, then `info`). Each is one sentence plus one thing to do. Use the script's wording, shortened if needed. Always keep the estimate note, as a small footnote at the very end instead. Examples of what to say:
- Long chat: "This chat grew very long. Claude re-reads all of it on every message, so each one cost more. Start a new chat when you change topic."
- Came back after a break: "Coming back after a long break made Claude re-read everything once at full price. If you don't need the old history, start fresh."
- Review cost: "This review itself used about a third of the chat's tokens. Next time, run it in a fresh chat on the old one."
- Secret hidden: "Something that looked like a password was hidden here. Never paste real keys into a chat."

**3. What went well.** One or two real things (pasted the exact error, named the file, one task at a time). Skip it if there is truly nothing. Never invent praise.

**4. Where the tokens went.** Two or three plain lines, not a table of jargon. Example: "About 96% was Claude re-reading the chat. Only about 1% was your typing. The biggest single prompt was #3, about 44%."

**5. Fix these prompts.** The top three by cost (`top_cost_turns`, plus any that needed a correction). For each:
- **Your prompt:** shortened, with its share of the cost ("about 49%").
- **Missing:** the plain-words reason from the table above.
- **Try this:** a rewritten prompt using the user's real file names, routes and page names from the chat, never generic ones. Templates are in [references/prompt-fixes.md](references/prompt-fixes.md).
- **Probably avoids:** what the better prompt would likely have saved (for example "most of the 11 file reads and the follow-up"), labelled as an estimate. Never a precise percentage.

Only rewrite prompts you understood from the chat. If one is unclear even in context, say so and skip it. A short answer to Claude's own question ("yes", "add MIT") is fine as it is: say "this one was fine" and move on.

**6. Do this next time.** At most three habits, and only ones the data supports:
- **New chat for a new topic** (name the turn and how long the chat had grown by then).
- **One goal per message**, in the order you would build it.
- **Paste the error, don't describe it.**
- **Put how to run the project in a `CLAUDE.md` file** if the same files were opened again and again, or many steps failed.

**7. Offer the next-chat starter.** Ask: "Want a paste-ready summary to start your next chat?" If yes, write it from the chat itself: what is done, what is left, key decisions, how to run it, and the one next task. Never guess.

**8. Close.** "Want me to explain any line, or save this as `prompt-receipt-<date>.md`?" Write nothing to disk without a yes. If they save it, suggest running Prompt Receipt again after their next chat and comparing the grade.

## Quick answers

If the user only asks a small question ("how many tokens did that use?", "was that expensive?"), do not write the whole receipt. Answer in two or three lines (tokens, cost if known, the one biggest reason), add the single most important heads-up if there is one, and offer the full receipt.

## Honesty rules

- **Estimates are labelled.** The log has one cost total for the whole chat. The script shares it out by token weight, so per-prompt dollars are guesses good enough to rank prompts, not to bill.
- **No made-up savings.** Say what a better prompt would likely have avoided, never "you'd have saved 40%".
- **A flag is a reason to look, not a verdict.** Weigh the real situation, such as Claude having just asked for the answer.
- **Never quote anything that looks like a key, password or token.** The script hides common shapes. Check what you copy.
- **If the chat was already efficient, say so.** A short review is the right answer. Do not invent problems.
- **If you are unsure, say so.** Few prompts, an unusual log, or a guessed chat all mean the grade is a rough guide.
