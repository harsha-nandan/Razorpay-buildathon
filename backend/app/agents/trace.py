"""Turns a Strands agent's raw message history into a UI/audit-friendly trace."""

from typing import Any


def extract_trace(messages: list[dict[str, Any]]) -> list[dict[str, Any]]:
    trace: list[dict[str, Any]] = []
    tool_names_by_id: dict[str, str] = {}
    for message in messages:
        role = message.get("role", "")
        for block in message.get("content", []):
            if "text" in block and block["text"].strip():
                trace.append({"type": "text", "role": role, "text": block["text"]})
            elif "toolUse" in block:
                tool_use = block["toolUse"]
                tool_names_by_id[tool_use.get("toolUseId", "")] = tool_use.get("name", "")
                trace.append(
                    {
                        "type": "tool_call",
                        "role": role,
                        "tool": tool_use.get("name"),
                        "input": tool_use.get("input"),
                    }
                )
            elif "toolResult" in block:
                tool_result = block["toolResult"]
                text_parts = [c.get("text", "") for c in tool_result.get("content", []) if "text" in c]
                trace.append(
                    {
                        "type": "tool_result",
                        "role": role,
                        "tool": tool_names_by_id.get(tool_result.get("toolUseId", "")),
                        "status": tool_result.get("status"),
                        "output": "\n".join(text_parts),
                    }
                )
    return trace


def final_text(message: dict[str, Any] | None) -> str:
    if not message:
        return ""
    return "\n".join(block["text"] for block in message.get("content", []) if "text" in block).strip()
