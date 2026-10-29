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

## Known blind spots

- A short prompt can be right when it answers Claude's last question.
- `no_target` can misfire on prompts about the whole project ("explain the architecture") or on pasted material the rule cannot parse.
- Topic shifts use word overlap; a deliberate follow-up in different words can look like a shift.
- Rework detection catches only corrections that start with the usual phrases; a calm rewording is missed.
- Sub-agent work may be counted in the turn that started it.
- `active_minutes` adds up time inside turns; `wall_minutes` is first prompt to last reply and includes idle days. Quote active time.
