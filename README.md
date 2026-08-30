# diy-harness-2026

A coding harness (AI coding agent), written from scratch in 
< 300 lines of Python, to show 
how and agentic coding tool system works.

The point of this repository is pedagogical. Tools like Claude Code and Cursor
look like magic. They are not. Strip away the interface and an agent is a
loop that sends a conversation to a language model, notices when the model asks
for a tool, runs it, appends the result to the conversation, and repeats. That
loop is `run_coding_agent_loop()` in `duke-diy-harness.py`.
You can read the
whole thing in one sitting.

## What it does

The basic harness `duke-diy-harness.py` gives the model just three tools:

| Tool | What it does |
|---|---|
| `read_file` | Return the full contents of a file |
| `list_files` | List the entries in a directory |
| `edit_file` | Replace the first occurrence of a string, or create a file |

That is enough for the model to explore a codebase and change it.

Tool calls are not made through any provider's function-calling API. The system
prompt asks the model to emit a single line of the form

```
tool: read_file({"filename": "hello.py"})
```

and `extract_tool_invocations()` finds those lines with string parsing and
`json.loads`. Doing it by hand rather than through a structured API 
makes the mechanism visible.

With `--all-conversation`, every request prints the entire conversation being
sent, prefixed with a call counter. Watching that JSON grow is the fastest way
to understand why context windows fill up and why agents get expensive.

## Running it

The harness talks to any OpenAI-compatible endpoint. It is configured for the
Duke AI proxy, which is a LiteLLM gateway:

```python
DUKE_BASE_URL = "https://aiproxy.duhs.duke.edu/v1"
```

Point `DUKE_BASE_URL` at any other OpenAI-compatible endpoint, including
`https://api.openai.com/v1` or a local server, and it will work unchanged.

Copy `.env.example` to `.env` and fill in your key. `.env` is gitignored.
`duke-diy-harness.py` needs only `DUKE_LITELLM_API_KEY`. The
`ANTHROPIC_API_KEY` entry is for `emperor-has-no-clothes.py`, which calls the
Anthropic API directly, and can be left blank otherwise.

With [pixi](https://pixi.sh):

```sh
pixi install
pixi run python duke-diy-harness.py
```

The script carries a `#!/usr/bin/env -S pixi run python` shebang, so from inside
the repository `./duke-diy-harness.py` also works. (`pixi run` searches upward
from the current directory for the manifest, so that shebang only works when you
are somewhere inside this repository.)

Without pixi, any Python 3.11+ with `openai`, `python-dotenv` and `anthropic`
installed will do.

Command-line arguments:

| Argument | What it does |
|---|---|
| `--model MODEL` | Model to use (default `glm-5.2`) |
| `--all-conversation` | Print the full conversation sent to the LLM on every call |
| `-h`, `--help` | Print usage plus the list of models available on the proxy |

Then talk to it:

```
You:: what files are here?
You:: read hello.py and add a docstring
```

Ctrl-D or Ctrl-C exits.

## What is in the repository

| File | What it is |
|---|---|
| `duke-diy-harness.py` | The harness. Start here. |
| `duke-diy-harness.qmd` | The Quarto source the `.py` is generated from, with the narrative |
| `duke-diy-harness-dump.py` / `.qmd` | An earlier variant that dumps more diagnostic detail |
| `emperor-has-no-clothes.qmd` / `.py` / `.html` | The base of the code in this repo, originally published at `https://www.mihaileric.com/The-Emperor-Has-No-Clothes/`, which was apparently based on Thorston Ball's How to Build an Agent (next line) |
| `ball-how-to-build-an-agent.html` | Copy of `https://ampcode.com/notes/how-to-build-an-agent` |
| `2026-06-01-diy-harness-summary.md` | Summary of what was learned building it |
| `conversation-dump.md` | An example session transcript |
| `hello.py` | A toy file to point the agent at |
| `examples/` | Configs pointing real agent CLIs at the same endpoint (see below) |

The `.py` files are generated from the `.qmd` sources, which is why they still
carry `#| eval: true` cell markers. Edit the `.qmd` if you want a change to
survive re-export.

## Pointing real agent CLIs at the same endpoint

Part of the lesson is that production agent CLIs are the same loop with a nicer
interface, and you can point them at the very same OpenAI-compatible endpoint
this harness uses. `examples/` holds two working configs (with the API key read
from the `DUKE_LITELLM_API_KEY` environment variable, never stored in the file):

| File | Install as | Run with |
|---|---|---|
| `examples/codex-duke.config.toml` | `~/.codex/duke.config.toml` | `codex --profile duke` |
| `examples/opencode-duke.jsonc` | `~/.config/opencode/opencode.jsonc` | `opencode` |

## Caveats

Teaching code! Do not use this in production.

THe `edit_file` tool run by the demo harnesses in this repo
writes to whatever path the model asks for.
There no sandbox, no
confirmation, and no diff shown first. 
Never run against anything you cannot restore.
Run it against a scratch directory or a
repository whose state is committed.

The harnesses here are minimal teaching examples.
There is also no retry logic, no token accounting, no streaming, no context
compaction, and no test suite. 

You could add any of these as a learning exercise.

## Licence

MIT. See [LICENSE](LICENSE).
