#| eval: true
import inspect
import json
import os

import anthropic
from dotenv import load_dotenv
from pathlib import Path
from typing import Any, Dict, List, Tuple

load_dotenv()

claude_client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])
#| eval: true
YOU_COLOR = "\u001b[94m"
ASSISTANT_COLOR = "\u001b[93m"
RESET_COLOR = "\u001b[0m"
#| eval: true
def resolve_abs_path(path_str: str) -> Path:
    """
    Turn a possibly-messy path string into a clean absolute Path.
    Example: file.py -> /Users/you/project/file.py

    Why an agent needs this: the LLM may say "read file.py" without
    knowing the project's directory layout. This anchors any partial
    path to a real location on disk before we try to open it.
    """
    # Path(...) wraps the string in a pathlib.Path object (OS-aware: handles / vs \).
    # .expanduser() replaces a leading "~" with the user's home directory;
    # a no-op if there is no "~".
    path = Path(path_str).expanduser()

    # is_absolute() is True for paths starting at the filesystem root (e.g. /a/b),
    # False for relative paths like "file.py" or "sub/file.py".
    if not path.is_absolute():
        # Path.cwd() is the current working directory.
        # The "/" operator on Path is overloaded to mean "join path segments",
        # so Path.cwd() / path yields e.g. /Users/you/project/file.py.
        # .resolve() canonicalises the result: makes it absolute, collapses
        # "." and ".." segments, and follows symlinks.
        path = (Path.cwd() / path).resolve()
    return path
#| eval: true
def read_file_tool(filename: str) -> Dict[str, Any]:
    """
    Gets the full content of a file provided by the user.
    :param filename: The name of the file to read.
    :return: The full content of the file.
    """
    full_path = resolve_abs_path(filename)
    print(full_path)
    with open(str(full_path), "r") as f:
        content = f.read()
    return {
        "file_path": str(full_path),
        "content": content
    }
#| eval: true
def list_files_tool(path: str) -> Dict[str, Any]:
    """
    Lists the files in a directory provided by the user.
    :param path: The path to a directory to list files from.
    :return: A list of files in the directory.
    """
    full_path = resolve_abs_path(path)
    all_files = []
    for item in full_path.iterdir():
        all_files.append({
            "filename": item.name,
            "type": "file" if item.is_file() else "dir"
        })
    return {
        "path": str(full_path),
        "files": all_files
    }
#| eval: true
def edit_file_tool(path: str, old_str: str, new_str: str) -> Dict[str, Any]:
    """
    Replaces first occurrence of old_str with new_str in file. If old_str is empty,
    create/overwrite file with new_str.
    :param path: The path to the file to edit.
    :param old_str: The string to replace.
    :param new_str: The string to replace with.
    :return: A dictionary with the path to the file and the action taken.
    """
    full_path = resolve_abs_path(path)
    if old_str == "":
        full_path.write_text(new_str, encoding="utf-8")
        return {
            "path": str(full_path),
            "action": "created_file"
        }
    original = full_path.read_text(encoding="utf-8")
    if original.find(old_str) == -1:
        return {
            "path": str(full_path),
            "action": "old_str not found"
        }
    edited = original.replace(old_str, new_str, 1)
    full_path.write_text(edited, encoding="utf-8")
    return {
        "path": str(full_path),
        "action": "edited"
    }
#| eval: true
TOOL_REGISTRY = {
    "read_file": read_file_tool,
    "list_files": list_files_tool,
    "edit_file": edit_file_tool 
}
#| label: full-system-prompt
#| eval: true

# Build a human/LLM-readable description of one tool by introspecting its
# Python function. This is how the LLM "learns" what tools exist without us
# hand-writing JSON schemas: the function itself is the source of truth.
def get_tool_str_representation(tool_name: str) -> str:
    # TOOL_REGISTRY (defined earlier) maps a tool name string to its function object.
    tool = TOOL_REGISTRY[tool_name]
    # An f-string is a formatted string literal: anything in {curly braces} is a
    # Python expression that gets evaluated and interpolated.
    # - tool.__doc__ is the function's docstring (the """..."""  block right under "def").
    # - inspect.signature(tool) reflects on the function and returns its parameter
    #   list, e.g. "(filename: str) -> Dict[str, Any]". The `inspect` module is in
    #   Python's standard library; it lets code examine other code at runtime.
    return f"""
    Name: {tool_name}
    Description: {tool.__doc__}
    Signature: {inspect.signature(tool)}
    """

# Stitch together the full system prompt by concatenating every tool's description.
def get_full_system_prompt():
    # Start with an empty string we'll append to. Python strings are immutable,
    # so each "+=" actually rebinds the name to a new string, but for a handful
    # of tools this is fine; for thousands you'd use "".join([...]) instead.
    tool_str_repr = ""

    # Iterating over a dict yields its keys, so this loops over each tool name
    # ("read_file", "list_files", "edit_file"). Order is insertion order in
    # modern Python (3.7+).
    for tool_name in TOOL_REGISTRY:
        # For each tool, prepend a "TOOL\n===" header, then the formatted block.
        # "\n" is a newline character inside the string.
        tool_str_repr += "TOOL\n===" + get_tool_str_representation(tool_name)
        # Add a separator line of 15 "=" characters. "=" * 15 is Python's
        # string-repetition operator.
        tool_str_repr += f"\n{'='*15}\n"

    # SYSTEM_PROMPT (defined in the next cell) is a template string containing
    # the placeholder "{tool_list_repr}". The .format() method substitutes our
    # generated description in place of that placeholder, producing the final
    # prompt that will be sent to the LLM.
    return SYSTEM_PROMPT.format(tool_list_repr=tool_str_repr)
#| eval: true
SYSTEM_PROMPT = """
You are a coding assistant whose goal it is to help us solve coding tasks. 
You have access to a series of tools you can execute. Here are the tools you can execute:

{tool_list_repr}

When you want to use a tool, reply with exactly one line in the format: 'tool: TOOL_NAME({{JSON_ARGS}})' and nothing else.
Use compact single-line JSON with double quotes. After receiving a tool_result(...) message, continue the task.
If no tool is needed, respond normally.
"""
get_full_system_prompt()
#| eval: true
def extract_tool_invocations(text: str) -> List[Tuple[str, Dict[str, Any]]]:
    """
    Return list of (tool_name, args) requested in 'tool: name({...})' lines.
    The parser expects single-line, compact JSON in parentheses.
    """
    invocations = []
    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line.startswith("tool:"):
            continue
        try:
            after = line[len("tool:"):].strip()
            name, rest = after.split("(", 1)
            name = name.strip()
            if not rest.endswith(")"):
                continue
            json_str = rest[:-1].strip()
            args = json.loads(json_str)
            invocations.append((name, args))
        except Exception:
            continue
    return invocations
#| eval: true
#| label: exec-llm-call

# Send the current conversation to Claude and return the model's reply as a string.
#
# Parameter type hint: List[Dict[str, str]] means "a list of dicts where each
# dict has string keys and string values". A typical element looks like:
#     {"role": "user", "content": "Read hello.py"}
# Roles in this codebase are "system", "user", or "assistant".
def execute_llm_call(conversation: List[Dict[str, str]]):
    # The Anthropic API treats the system prompt as a *separate* top-level
    # parameter, not as another message in the messages list (this differs
    # from OpenAI's chat-completions API, where system is just role="system").
    # So we split the conversation into two pieces:
    #   - system_content: the single system-prompt string
    #   - messages:       everything else (user/assistant turns)
    system_content = ""
    messages = []

    # Walk through the conversation once, sorting each entry into the right bucket.
    # msg["role"] indexes into the dict by key, just like msg.get("role")
    # except KeyError is raised if the key is missing.
    for msg in conversation:
        if msg["role"] == "system":
            # Overwrite (not append) — we expect at most one system message.
            # If multiple system messages appear, the last one wins.
            system_content = msg["content"]
        else:
            # User and assistant turns go into the messages list in order.
            messages.append(msg)

    # Call the Anthropic API. claude_client was constructed in the first cell
    # via anthropic.Anthropic(api_key=...). The .messages.create(...) method
    # is the main "send a prompt, get a completion" entrypoint.
    response = claude_client.messages.create(
        # Which Claude model to use. Hard-coded here; in production you'd
        # usually read this from a config or environment variable.
        model="claude-sonnet-4-20250514",
        # Upper bound on the length of the model's reply, measured in tokens
        # (roughly 3/4 of a word each). The API will stop early if the model
        # finishes its thought before hitting this limit.
        max_tokens=2000,
        # The system prompt — instructions that shape the model's behavior
        # for the whole conversation (tool list, response format, etc.).
        system=system_content,
        # The back-and-forth history of user/assistant turns.
        messages=messages
    )

    # The API returns a structured response object. response.content is a
    # list of "content blocks" (text, tool use, images, ...). For a plain
    # text reply there is exactly one block, of type text, so we grab the
    # first one and pull out its .text attribute.
    # In a more robust implementation you'd iterate over response.content
    # and handle each block type explicitly.
    return response.content[0].text
#| eval: true
def run_coding_agent_loop():
    print(get_full_system_prompt())
    conversation = [{
        "role": "system",
        "content": get_full_system_prompt()
    }]
    while True:
        try:
            user_input = input(f"{YOU_COLOR}You:{RESET_COLOR}:")
        except (KeyboardInterrupt, EOFError):
            break
        conversation.append({
            "role": "user",
            "content": user_input.strip()
        })
        while True:
            assistant_response = execute_llm_call(conversation)
            tool_invocations = extract_tool_invocations(assistant_response)
            if not tool_invocations:
                print(f"{ASSISTANT_COLOR}Assistant:{RESET_COLOR}: {assistant_response}")
                conversation.append({
                    "role": "assistant",
                    "content": assistant_response
                })
                break
            for name, args in tool_invocations:
                tool = TOOL_REGISTRY[name]
                resp = ""
                print(name, args)
                if name == "read_file":
                    resp = tool(args.get("filename", "."))
                elif name == "list_files":
                    resp = tool(args.get("path", "."))
                elif name == "edit_file":
                    resp = tool(args.get("path", "."), 
                                args.get("old_str", ""), 
                                args.get("new_str", ""))
                conversation.append({
                    "role": "user",
                    "content": f"tool_result({json.dumps(resp)})"
                })
#| eval: true
if __name__ == "__main__":
    run_coding_agent_loop()
