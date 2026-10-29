---
name: prompt-receipt
description: End-of-chat review for vibe coders. Reads the finished Claude Code chat and reports how many tokens it used and which prompts cost the most. It names the prompts that were vague or missing keywords (no file name, no error text, no expected result, too many tasks in one message), rewrites them the better way, and estimates the tokens that would have been saved. It also gives context-hygiene tips and a ready-to-paste starter prompt for the next chat. Make sure to use this skill whenever the user says "review this chat", "chat review", "prompt receipt", "how many tokens did this use", "where did my tokens go", "how could I have prompted better", "what did I do wrong in my prompts", "token optimise", or wraps up a long build/debug session, even if they never say the word "review".
---

# Prompt Receipt

Vibe coders lose most of their tokens to a few weak prompts, not to the whole chat. A one-word "fix" makes Claude explore the project to guess what is broken. An error described but not pasted gets a guess instead of a diagnosis. This skill reads the chat that just finished, finds those moments, and shows the user exactly what to type next time.

It differs from two neighbours:
- `explain-usage` shows where tokens went but says nothing about the prompts.
- `prompt-postmortem` mines patterns across many sessions. This skill reviews **one chat**, right at the end, and adds the cost of each prompt and concrete rewrites. If the user wants cross-chat patterns, point them to `prompt-postmortem` after this.

The user may be new to coding. Plain words, short sentences, no shaming. Every criticism comes with the fix, and every review opens with what they did well.

## Step 1: get the numbers

Run the bundled analyzer. It only reads local files and sends nothing anywhere:

    python3 -I "${CLAUDE_SKILL_DIR}/scripts/analyze_chat.py" --format table

(If `${CLAUDE_SKILL_DIR}` was not substituted, use the base directory shown when this skill loaded.) With no arguments it picks the newest chat of the current folder, which is the chat that is ending. Then run it again without `--format` to get the full JSON (per-prompt fields, patterns, flags).

- Wrong chat? `--list` shows recent chats with their first prompt; pass `--session <id>`. If the user's project lives in another folder, pass `--project-dir ~/.claude/projects/<folder>`.
- No logs (claude.ai, Cowork, or the folder has none)? Do not stop. Review from the conversation itself: list the user's prompts, estimate tokens as characters / 4, apply the same rubric by judgment, and say clearly that every number is an estimate.

Read [references/rubric.md](references/rubric.md) once to know what each flag means and what the numbers do and do not prove. The flags are blunt rules, so you are the judge: drop a flag that does not fit (a short "fix" right after Claude asked "should I fix it?" is fine), and say so.

## Step 2: write the review

Use this order. Keep the whole thing about one to two screens; the user will not read more. [references/example-review.md](references/example-review.md) shows the tone, length and layout to aim for.

**1. Headline (3 lines).** Total tokens, the cost if the log has it, prompt score with letter grade, and one sentence on the biggest lesson. Example: "34 prompts, 187M tokens ($35). 17 prompts named no file or feature; they carried 65% of the cost."

**2. What you did well.** One to three real things from the chat (clear error pasted, screenshot attached, good step-by-step ordering). Skip if truly nothing; never invent praise.

**3. Token ledger.** A small table: input, output, cache reads, peak context size. Then one plain sentence: most tokens are Claude re-reading the earlier chat on every message, so a long chat makes every later prompt more expensive. This is why context hygiene (step 5) matters more than shortening prompts.

**4. The costliest prompts, fixed.** For the top 3 to 5 prompts by cost share (`top_cost_turns`, plus any with `led_to_correction`), show:
- the original prompt, shortened, with its cost share;
- what was missing, named in plain words (use the flag names as a guide);
- the **keywords to add**, taken from [references/prompt-fixes.md](references/prompt-fixes.md) and from this user's own project (real file names, routes, component names you saw in the chat's tool calls, not generic ones);
- a rewritten prompt they could have sent;
- a saving estimate, labelled as an estimate: roughly how many tool calls or corrections the better prompt would likely have avoided. Base it on what happened in that turn (`tools`, `requests`, `reread_files`, whether a correction followed). Do not quote a precise percentage you cannot support.

Only rewrite prompts you understood from the chat. If a prompt's intent is unclear even in context, say so and skip it.

**5. Habits that save the most.** Include only those the data supports:
- **Context hygiene:** if `topic_shifts` show the user switching topic with a large context behind them, name the turns and say "start a new chat here" (or `/compact`, or `/clear`). Mention the context size at that point.
- **Rework:** if `rework_share` is above about 10% or there were corrections, show the first-attempt prompt next to the correction and what one extra sentence would have prevented.
- **Re-read files / tool errors:** repeated reads of the same file, or many tool errors, suggest the project's run commands or structure should live in a `CLAUDE.md`.
- **Scope:** `multi_task` prompts. Split into one goal per message, in build order (backend, then API check, then frontend).
- **Questions:** many tiny "done?" / "will it reset?" messages in a huge context each cost a full context re-read. Batch them or ask in a fresh chat.
- **Model/effort:** a cheap model is enough for questions and small edits; save the strongest model for design-heavy backend and debugging. Only say this if the chat was one model throughout.

**6. Copy-paste kit.** Offer, and write on request or when it fits:
- two or three lines for `CLAUDE.md` (stack, how to run backend and frontend, conventions) so the user stops re-explaining the project;
- a **next-chat starter prompt**: what is finished, what is pending, key decisions, exact next task. Build it from the chat, not from guesses. This is how a 40%-done project moves on without carrying a 900k-token context.

**7. Close.** Offer to save the review as `prompt-receipt-<date>.md` in the project folder. Write nothing to disk without a yes. If they save it, tell them to run this skill again after their next chat and compare the score and rework share.

## Honesty rules

- Say "estimate" for per-prompt dollars: the log has one session total, which the script splits by token weight. Say "about", not "exactly".
- Do not claim a rewritten prompt would have cost X% less. Say what it would likely have avoided.
- A flag is a reason to look, not a verdict. Weigh the chat's real context (Claude may have just asked for the answer).
- Never quote anything that looks like a key, password, or token; the script masks common shapes, but check what you copy.
- If the chat was already efficient, say so. A short review is the right answer.
