#!/usr/bin/env -S pixi run python

import inspect
import json
import os
from pathlib import Path
from typing import Any

from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()

DUKE_BASE_URL = "https://aiproxy.duhs.duke.edu/v1"
DUKE_MODEL = "glm-5.2"  # "gpt-5.3-codex"

duke_client = OpenAI(
    api_key=os.environ["DUKE_LITELLM_API_KEY"],
    base_url=DUKE_BASE_URL,
)
#| eval: true
YOU_COLOR = "\033[94m"
ASSISTANT_COLOR = "\033[93m"
RESET_COLOR = "\033[0m"


def resolve_abs_path(path_str: str) -> Path:
    """
    Turn a possibly-messy path string into a clean absolute Path.
    Example: file.py -> /Users/you/project/file.py
    """
    path = Path(path_str).expanduser()
    if not path.is_absolute():
        path = (Path.cwd() / path).resolve()
    return path


#| eval: true
def read_file_tool(filename: str) -> dict[str, Any]:
    """
    Gets the full content of a file provided by the user.
    :param filename: The name of the file to read.
    :return: The full content of the file.
    """
    full_path = resolve_abs_path(filename)
    print(full_path)
    with open(str(full_path), "r") as f:
        content = f.read()
    return {"file_path": str(full_path), "content": content}


#| eval: true
def list_files_tool(path: str) -> dict[str, Any]:
    """
    Lists the files in a directory provided by the user.
    :param path: The path to a directory to list files from.
    :return: A list of files in the directory.
    """
    full_path = resolve_abs_path(path)
    all_files = []
    for item in full_path.iterdir():
        all_files.append(
            {"filename": item.name, "type": "file" if item.is_file() else "dir"}
        )
    return {"path": str(full_path), "files": all_files}


#| eval: true
def edit_file_tool(path: str, old_str: str, new_str: str) -> dict[str, Any]:
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
        return {"path": str(full_path), "action": "created_file"}
    original = full_path.read_text(encoding="utf-8")
    if original.find(old_str) == -1:
        return {"path": str(full_path), "action": "old_str not found"}
    edited = original.replace(old_str, new_str, 1)
    full_path.write_text(edited, encoding="utf-8")
    return {"path": str(full_path), "action": "edited"}


TOOL_REGISTRY = {
    "read_file": read_file_tool,
    "list_files": list_files_tool,
    "edit_file": edit_file_tool,
}


#| label: full-system-prompt
#| eval: true
def get_tool_str_representation(tool_name: str) -> str:
    tool = TOOL_REGISTRY[tool_name]
    return f"""
    Name: {tool_name}
    Description: {tool.__doc__}
    Signature: {inspect.signature(tool)}
    """


def get_full_system_prompt():
    tool_str_repr = ""
    for tool_name in TOOL_REGISTRY:
        tool_str_repr += "TOOL\n===" + get_tool_str_representation(tool_name)
        tool_str_repr += f"\n{'=' * 15}\n"
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
def extract_tool_invocations(text: str) -> list[tuple[str, dict[str, Any]]]:
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
            after = line[len("tool:") :].strip()
            name, rest = after.split("(", 1)
            name = name.strip()
            if not rest.endswith(")"):
                continue
            json_str = rest[:-1].strip()
            args = json.loads(json_str)
            invocations.append((name, args))
        except ValueError:
            # Malformed tool line (bad split or invalid JSON), skip it.
            continue
    return invocations


LLM_CALL_COUNTER = 0


def execute_llm_call(conversation: list[dict[str, str]]):
    """
    Send the full conversation (including the system message) to the Duke AI
    Proxy and return the assistant's reply as a plain string.

    The conversation list is already in OpenAI chat format, dicts with
    role in {"system", "user", "assistant"} and a "content" string, so we
    pass it through unchanged.
    """
    global LLM_CALL_COUNTER
    LLM_CALL_COUNTER += 1
    print(
        f"\n\n\n\n\n================================================\n"
        f"LLM CALL COUNTER: {LLM_CALL_COUNTER}\n"
        f"================================================\n\n\nSending conversation: "
    )
    print(json.dumps(conversation, indent=2))

    response = duke_client.chat.completions.create(
        model=DUKE_MODEL,
        max_completion_tokens=2000,
        messages=conversation,
    )
    return response.choices[0].message.content


#| eval: true
def run_coding_agent_loop():
    print(get_full_system_prompt())
    conversation = [{"role": "system", "content": get_full_system_prompt()}]
    while True:
        try:
            user_input = input(f"{YOU_COLOR}You:{RESET_COLOR}:")
        except (KeyboardInterrupt, EOFError):
            break
        conversation.append({"role": "user", "content": user_input.strip()})
        while True:
            assistant_response = execute_llm_call(conversation)
            tool_invocations = extract_tool_invocations(assistant_response)
            if not tool_invocations:
                print(f"{ASSISTANT_COLOR}Assistant:{RESET_COLOR}: {assistant_response}")
                conversation.append(
                    {"role": "assistant", "content": assistant_response}
                )
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
                    resp = tool(
                        args.get("path", "."),
                        args.get("old_str", ""),
                        args.get("new_str", ""),
                    )
                conversation.append(
                    {"role": "user", "content": f"tool_result({json.dumps(resp)})"}
                )


#| eval: true
if __name__ == "__main__":
    run_coding_agent_loop()
