# Rubric: what the analyzer measures

`scripts/analyze_chat.py` uses plain rules (no model), so every number can be explained to the user.

## Tokens and cost

- A "request" is one call to the model. One typed prompt usually triggers many (each tool call is another request). Requests are de-duplicated by request id, because the log repeats a request once per content block.
- **cache_read** is earlier chat re-read cheaply. It is usually 90%+ of all tokens in long chats. It costs about a tenth of fresh input, so a big number here is not "waste" by itself; the lesson is that context size multiplies the price of every later prompt.
- **share** is a prompt's part of the chat's total *weighted* tokens (input 1, cache write 1.25, cache read 0.1, output 5). If the log has a cost counter, `cost_usd_est` splits that total by share. It is an estimate, good for ranking prompts, not for billing.
- **ctx_peak** is the largest context (input + cache) in any request of that turn.

## Prompt kinds

- `question`: asks something. Not penalised for missing files or outcomes.
- `reply`: three words or fewer with no action verb ("yes", "done"), or a prompt that opens with an approval ("Yes, push it", "ok, go ahead"). Claude already proposed the task, so there is nothing to name. Not scored.
- Unscored too: a prompt that was interrupted before Claude answered (usually re-sent right after).
- `command`: a slash command you typed, such as `/prompt-receipt` or `/compact`. It gets its own line so its cost is not charged to the prompt before it (a review run at the end of a chat is real cost, and after a long break it also re-writes the whole cached context). It is counted in the totals, shown as `command_cost_share`, and never scored or ranked. Tell the user how much the review itself cost.
- `action`: everything else. Scored.

## Flags (each subtracts from 100)

| flag | points | fires when | usual fix |
|---|---|---|---|
| `no_target` | -25 | action prompt under 500 chars names no file, path, function, route, or backticked term | name the file / page / endpoint |
| `problem_without_evidence` | -25 | says error / not working / bug but pastes no error text, status code, screenshot or log | paste the exact error + say what you did before it |
| `vague_words` | -10 | "properly", "everything", "whole", "better", "etc" ... | say what "properly" looks like |
| `too_short` | -15 | action prompt under 8 words | add target + expected result |
| `multi_task` | -15 | five or more different verbs, five or more list items, or repeated "also" | one goal per message |
| `no_expected_outcome` | -10 | build prompt with no "should / expected / returns / shows" language | say what done looks like |
| `huge_paste` | -5 | over 4000 characters | paste only the relevant part |

`correction` (not a flag, a pattern): a prompt that starts with "still", "no", "not working", "same error", "that's not what I asked" etc. marks the prompt before it as `led_to_correction`. `rework_share` is the weighted cost of corrections plus the turns they corrected.

## Overall score

Mean of prompt scores weighted by each prompt's cost share (floor 1% so cheap prompts still count). A 90+, B 80+, C 70+, D 55+, else E. It rates prompt quality in this chat only. It is not a rating of the person.

## Heads-ups (the `warnings` list)

The script writes these in plain words so Claude can pass them on. Level `alert` is most serious, then `warn`, then `info`. Show at most three, most serious first.

| code | level | fires when | what the user should do |
|---|---|---|---|
| `long_chat` | warn, alert at 500k | the chat's longest context reached 200,000 tokens | start a new chat when the topic changes |
| `review_cost` | warn | the review itself used 15% or more of the chat | run it next time in a fresh chat with `--session <id>` |
| `came_back_after_break` | info | a message came after a break of an hour or more and re-wrote 50,000+ tokens | start fresh if the old history is not needed |
| `rework` | warn | 20% or more of the cost went on redoing work after "that didn't work" | paste the exact error and say what was expected |
| `tool_errors` | info | 5 or more of Claude's steps failed | put run commands in `CLAUDE.md` |
| `secrets` | warn | a prompt contained something shaped like a key or password (hidden in the output) | never paste real secrets into a chat |
| `few_prompts` | info | fewer than 3 prompts | treat the grade as a rough guide |
| `no_cost` | info | the log has no cost counter | numbers are tokens only |
| `estimate` | info | the log has a cost counter | per-prompt dollars are estimates |
| `picked_chat` | info | no `--session` was given, so the newest chat was used | use `--list` if it was the wrong one |

The "came back after a break" warning exists because Claude keeps a short-lived copy of the chat so it does not have to pay full price to re-read it. After a long break that copy is gone, so the first message back re-reads everything once at full price.

A plain "No", "Not yet" or "No thanks" is an answer to Claude's question, not a complaint, so it is never counted as rework.

## Known blind spots

- A short prompt can be right when it answers Claude's last question.
- `no_target` can misfire on prompts about the whole project ("explain the architecture") or on pasted material the rule cannot parse.
- Topic shifts use word overlap; a deliberate follow-up in different words can look like a shift.
- Rework detection catches only corrections that start with the usual phrases; a calm rewording is missed.
- Sub-agent work may be counted in the turn that started it.
- `active_minutes` adds up time inside turns; `wall_minutes` is first prompt to last reply and includes idle days. Quote active time. Active time caps any pause between two log rows at 10 minutes, so days away from the chat do not count.
