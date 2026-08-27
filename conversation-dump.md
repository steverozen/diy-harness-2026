*system*


You are a coding assistant whose goal it is to help us solve coding tasks.
You have access to a series of tools you can execute. Here are the tools you can execute:

TOOL
===
    Name: read_file
    Description: 
Gets the full content of a file provided by the user.
:param filename: The name of the file to read.
:return: The full content of the file.

    Signature: (filename: str) -> Dict[str, Any]
    
===============
TOOL
===
    Name: list_files
    Description: 
Lists the files in a directory provided by the user.
:param path: The path to a directory to list files from.
:return: A list of files in the directory.

    Signature: (path: str) -> Dict[str, Any]
    
===============
TOOL
===
    Name: edit_file
    Description: 
Replaces first occurrence of old_str with new_str in file. If old_str is empty,
create/overwrite file with new_str.
:param path: The path to the file to edit.
:param old_str: The string to replace.
:param new_str: The string to replace with.
:return: A dictionary with the path to the file and the action taken.

    Signature: (path: str, old_str: str, new_str: str) -> Dict[str, Any]
    
===============
TOOL
===
    Name: dump_conversation
    Description: 
Writes the entire running conversation to ./conversation-dump.md in the
current working directory, overwriting any previous dump. Each turn is
rendered as a block of the form:

    *role*

    content

with a blank line between turns. Useful for inspecting what the model
has been shown so far.
:return: A dictionary with the absolute path written and the number of turns.

    Signature: () -> Dict[str, Any]
    
===============


When you want to use a tool, reply with exactly one line in the format: 'tool: TOOL_NAME({JSON_ARGS})' and nothing else.
Use compact single-line JSON with double quotes. For tools that take no arguments (e.g. dump_conversation), use an empty object: 'tool: dump_conversation({})'.
After receiving a tool_result(...) message, continue the task.
If no tool is needed, respond normally.


*user*

reply "ok" for this turn only

*assistant*

ok

*user*

reply "not ok"

*assistant*

not ok

*user*

dump conversation

*assistant*

tool: dump_conversation({})

xxxxxxx
