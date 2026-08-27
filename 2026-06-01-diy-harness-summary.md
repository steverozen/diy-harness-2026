# DIY Coding-Harness Workshop Files

**Date:** 2026-06-01
**Folder:** `~/EA/projects/2026-diy-claude/`
**Source article:** Mihail Eric, *"The Emperor Has No Clothes: How to Code Claude Code in 200 Lines of Code"*, January 2026,
<https://www.mihaileric.com/The-Emperor-Has-No-Clothes/>

**Pedigree.** Eric's article is itself a Python retelling of an earlier and
more influential piece by Thorsten Ball, *"How to Build an Agent"*,
published 2025-04-15 on ampcode.com,
<https://ampcode.com/notes/how-to-build-an-agent>. Ball's original is
written in Go (~400 lines, mostly boilerplate) and lays out the same core
thesis Eric repeats: *an agent is an LLM in a loop with a small set of
local tools*. Ball starts with a single `read_file` tool and then layers on
`list_files` and `edit_file`, exactly the trio Eric and our harnesses use.
A saved copy of Ball's article lives next to this summary as
`ball-how-to-build-an-agent.html`. Notable ports of Ball's Go original:

- Python: <https://medium.com/@jbrathnayake98/how-to-build-an-agent-by-thorsten-ball-python-version-ebbabb8665f6>
- JavaScript / TypeScript: <https://dev.to/cultureamp/how-to-build-an-agent-in-javascript-2n75>, <https://github.com/ivanleomk/building-an-agent>
- Hacker News discussion of Eric's Python remix: <https://news.ycombinator.com/item?id=46545620>

So the lineage feeding this workshop is: **Ball (Go, 2025-04) → Eric
(Python, 2026-01) → this folder (Python, Anthropic / Duke-proxy /
Duke-proxy + dump, 2026-06)**.

## Purpose

Build a minimal "Claude Code"-style coding agent in ~200 lines of Python and
use it as a workshop teaching vehicle. The agent is a single REPL loop that
hands an LLM three tools (read file, list files, edit file) and lets the model
drive a session by emitting `tool: name({...})` lines that the loop parses and
executes locally.

The folder contains three progressive variants of the same harness, each as a
runnable Quarto document plus an extracted `.py` script.

## Environment

- Pixi env at `~/EA/` (`pixi.toml`).
  Added `anthropic`, `jupyter` (alongside pre-existing `openai`, `python-dotenv`).
- `.env` in this folder (mode 600) holds `ANTHROPIC_API_KEY` and is read by
  `load_dotenv()`.
- `~/EA/.gitignore` includes `.env` and `**/.env` so secrets stay local.

To run any version:

```bash
cd ~/EA/projects/2026-diy-claude
pixi run python <file>.py
```

To render a Quarto version (skips `input()` cells if `eval: false` is set):

```bash
pixi run quarto render <file>.qmd
```

## The three variants

### 1. `emperor-has-no-clothes.qmd` / `.py`  -  Anthropic, annotated

Direct port of Eric's article with workshop annotations.

- LLM client: `anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])`
- API call: `claude_client.messages.create(model="claude-sonnet-4-...",
  max_tokens=2000, system=..., messages=...)`
- Notable: Anthropic's API takes the system prompt as a *separate* top-level
  parameter, so `execute_llm_call` splits the conversation into `system_content`
  and `messages` before sending.
- Inline comments explain `pathlib.Path`, `inspect.signature`, f-strings,
  dict iteration order, the `*` string-repetition operator, and what
  `response.content[0].text` is doing.
- Tools: `read_file`, `list_files`, `edit_file`.

### 2. `duke-diy-harness.qmd` / `.py`  -  Duke AI Proxy

Same harness, but routed through the Duke LiteLLM proxy at
`https://aiproxy.duhs.duke.edu/v1`. This lets the workshop drive any model the
Duke gateway exposes (`gpt-5.1`, `gpt-5-pro`, `gpt-4.1`, `o4-mini`,
`gpt-oss-120b`, `grok-4-1-fast-reasoning`, ...).

Differences from variant 1, isolated to the client and the one API-call cell:

| Aspect | Anthropic version | Duke / OpenAI-Completions version |
|---|---|---|
| Client | `anthropic.Anthropic(api_key=...)` | `OpenAI(api_key=..., base_url=DUKE_BASE_URL)` |
| Auth env var | `ANTHROPIC_API_KEY` | `DUKE_LITELLM_API_KEY` |
| System prompt | top-level `system=` kwarg | first message with `role="system"` |
| Reply-length cap | `max_tokens` | `max_completion_tokens` |
| Reply text | `response.content[0].text` | `response.choices[0].message.content` |
| Model id | `claude-sonnet-4-...` | `gpt-5.1` (constant `DUKE_MODEL`) |

Tools, registry, system-prompt builder, tool-call parser, and agent loop are
byte-for-byte identical to variant 1. The point of the variant is to show
that the "harness" is provider-agnostic and only a thin adapter cell needs to
know which wire protocol it is speaking.

### 3. `duke-diy-harness-dump.qmd` / `.py`  -  Duke proxy + conversation dump

Variant 2 plus a fourth tool, `dump_conversation`, which writes the running
conversation to `conversation-dump.md` (one `*role*` / content block per turn).
Useful in workshop demos to peek at exactly what context the model has been
shown.

Implementation notes:

- Conversation moved from a local variable to a module-level
  `CONVERSATION: List[Dict[str, str]] = []` so the dump tool can read it
  without threading state through every tool call. The loop calls
  `CONVERSATION.clear()` at start of each session to preserve the list
  identity that the tool closed over.
- System-prompt template grew one sentence telling the model how to invoke
  zero-argument tools (`'tool: dump_conversation({})'`).
- Tool dispatch in the loop grew an `elif name == "dump_conversation": resp = tool()`
  branch.

**Bug found and fixed:** the original agent loop only appended the assistant
turn to `conversation` when it contained no tool calls. Tool-emitting
assistant turns were silently dropped, so a dump would show two consecutive
`user` turns (the original request and the `tool_result`) with the
`tool: edit_file(...)` line missing in between. Fix: append the assistant
response *unconditionally* before acting on it.

**Secondary fix:** the ANSI color-code constants (`YOU_COLOR`,
`ASSISTANT_COLOR`, `RESET_COLOR`) lost their literal ESC (`\x1b`) bytes when
the qmd was first authored, so the "You:" prompt was uncolored. Re-inserted
the ESC bytes via a small Python edit.

## Workflow conventions established

- Each `.qmd` has Quarto frontmatter (`title`, `author`, `date`, `source`,
  `format: html toc: true`) plus a workshop-notes hint about using
  `::: {.callout-note}` blocks for annotations.
- Python chunks are tagged as executable Quarto cells:

  ```
  ```{python}
  #| eval: true
  ```

  with `#| label:` on the longer ones so cross-references work.
- `.py` files are produced from `.qmd` by:

  ```bash
  awk '/^```\{python\}/{flag=1; next} /^```$/{flag=0; next} flag' \
    <file>.qmd > <file>.py
  ```

  The `#| eval: true` directive lines survive as harmless Python comments.

## File index

| File | Role |
|---|---|
| `emperor-has-no-clothes.qmd` | Anthropic version, annotated |
| `emperor-has-no-clothes.py` | extracted script |
| `emperor-has-no-clothes.html` | raw HTML grab of the Eric article |
| `ball-how-to-build-an-agent.html` | raw HTML grab of Ball's original Go article |
| `duke-diy-harness.qmd` | Duke-proxy version |
| `duke-diy-harness.py` | extracted script |
| `duke-diy-harness-dump.qmd` | Duke-proxy + `dump_conversation` tool |
| `duke-diy-harness-dump.py` | extracted script |
| `conversation-dump.md` | sample dump from a live session |
| `.env` | `ANTHROPIC_API_KEY` (gitignored) |
| `2026-06-01-diy-harness-summary.md` | this file |

## Pedagogical arc

1. **Variant 1** establishes the core idea: a coding agent is a `while` loop
   around an LLM call plus three local tools, plus a text-based protocol for
   the model to request tool execution.
2. **Variant 2** isolates the LLM-provider seam by swapping just the client
   and the one API-call cell. Everything else carries over unchanged, making
   the "harness is provider-agnostic" claim concrete.
3. **Variant 3** extends the tool set in a small but illustrative way (a tool
   that introspects the agent's own state), and surfaces a real bug in the
   reference loop, which is itself a teachable moment about why every turn
   should be recorded.
