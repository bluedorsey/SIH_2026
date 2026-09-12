# Labelling in any chatbot (no API key, no agent)

Same prompt, same validator and same output file as the API lanes - only the transport is you
pasting into ChatGPT / Claude / Gemini instead of a key calling an endpoint.

## The loop

```powershell
# 1. get the next chunk (writes two files, skips everything already labelled)
python -m TRAINING.extract_for_labeling

#    TRAINING\label_prompt.md                    <- the rules, paste ONCE per chat
#    DATA\distilled\manual\rows_to_label.md      <- this chunk's rows

# 2. in the chatbot:
#      paste label_prompt.md      (once, at the start of a new chat)
#      paste rows_to_label.md     (the part under the --- line)
#      save the JSON reply as reply.json

# 3. import it
python -m TRAINING.import_labeled_answers reply.json --model chatgpt

# 4. back to step 1 - it hands you the next chunk
```

`--dry-run` on the import validates and prints the reject reasons without writing anything.

## Options

    python -m TRAINING.extract_for_labeling --limit 100      # bigger chunk (default 40)
    python -m TRAINING.extract_for_labeling --output D:\rows.md
    python -m TRAINING.extract_for_labeling --force          # re-do rows already labelled
    python -m TRAINING.import_labeled_answers a.json b.json  # several replies at once
    python -m TRAINING.import_labeled_answers reply.json --dry-run

Use `--model` to record which chatbot produced the rows (`chatgpt`, `gemini`, `claude`, ...).
It lands in the row's `model` field, so the agreement report can compare teachers later.

## How resuming works

`extract_for_labeling` reads `DATA/distilled/raw/label.jsonl` and skips every seed that already
has an accepted row - from the API lanes, from Antigravity, or from an earlier chatbot chunk.
Run it as often as you like: you always get the next unlabelled rows, never a repeat.
Rejected rows are *not* marked done, so they come back in a later chunk.

## Keeping the prompt honest

`label_prompt.md` is GENERATED from `TRAINING/distill/prompts.py` every time you run the extract -
never edit it by hand. If the pipeline's prompt version changes, the extract prints
`(UPDATED - paste it again in a fresh chat)` and you start a new chat with the new rules.
That is what keeps chatbot rows and API rows scoring the same.

## When rows get rejected

The importer prints the exact reason. The common ones:

- `span 'x' not found in text` - the chatbot paraphrased instead of copying a verbatim substring
- `serious_injury=false but text states 'fractured'` - contradiction with the injury wording
- `verdict X contradicts questions (Y)` - the four questions and the verdict disagree
- `annotated text matches no seed row` - the chatbot rewrote the narrative, or dropped `input_id`

Fix those elements in `reply.json` and import again; the seeds are still pending, so nothing is lost.

## Batch size

40 rows is a comfortable chunk for one chat. Larger chunks mean fewer requests (useful when the
chatbot rate-limits you) but structured output degrades on long replies - if rejects start
appearing near the end of a chunk, that is the signal to go smaller.
