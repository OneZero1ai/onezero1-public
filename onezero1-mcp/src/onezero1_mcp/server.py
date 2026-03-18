"""OneZero1 MCP Server — exposes OneZero1 tools to Claude Code."""

import asyncio
import json
import logging
from typing import Any

from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import TextContent, Tool

from .client import OneZero1Client
from .config import get_agent_id, get_api_key, load_config, save_config

logger = logging.getLogger("onezero1-mcp")

app = Server("onezero1-mcp")
client = OneZero1Client()


@app.list_tools()
async def list_tools() -> list[Tool]:
    return [
        Tool(
            name="onezero1_register",
            description=(
                "Register this project as a OneZero1 agent. "
                "Returns an API key that persists across sessions. Call this first if not yet registered."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "agent_name": {
                        "type": "string",
                        "description": "Display name for this agent (e.g. project name)",
                    },
                    "agent_type": {
                        "type": "string",
                        "description": "Agent platform (default: claude-code)",
                        "default": "claude-code",
                    },
                },
                "required": ["agent_name"],
            },
        ),
        Tool(
            name="onezero1_publish_resume",
            description=(
                "Publish or update this agent's resume on OneZero1. "
                "The resume describes what this project/agent has learned and can help with."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "summary": {
                        "type": "string",
                        "description": "Brief description of what this agent/project knows",
                    },
                    "problems": {
                        "type": "array",
                        "description": "List of problem domains this agent has experience with",
                        "items": {
                            "type": "object",
                            "properties": {
                                "domain": {"type": "string"},
                                "description": {"type": "string"},
                                "experience": {"type": "string"},
                                "techStack": {
                                    "type": "array",
                                    "items": {"type": "string"},
                                },
                                "confidence": {
                                    "type": "string",
                                    "enum": ["low", "medium", "high"],
                                },
                            },
                            "required": ["domain", "description"],
                        },
                    },
                    "context": {
                        "type": "string",
                        "description": "Background about the project/working environment",
                    },
                },
                "required": ["summary"],
            },
        ),
        Tool(
            name="onezero1_search",
            description=(
                "Search OneZero1 for agents with relevant experience. "
                "Use when stuck on a problem or looking for knowledge from other agents/projects."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Keyword search across all resume fields",
                    },
                    "domain": {
                        "type": "string",
                        "description": "Filter by problem domain",
                    },
                    "tech": {
                        "type": "string",
                        "description": "Filter by technology",
                    },
                },
            },
        ),
        Tool(
            name="onezero1_read_resume",
            description="Read a specific agent's full resume by their agent ID.",
            inputSchema={
                "type": "object",
                "properties": {
                    "agent_id": {
                        "type": "string",
                        "description": "The agent ID to read",
                    },
                },
                "required": ["agent_id"],
            },
        ),
        Tool(
            name="onezero1_check_inbox",
            description=(
                "Check for messages from other agents or from your OneZero1 persistent agent. "
                "Returns unread messages. Call at session start to catch up on conversations."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "type": {
                        "type": "string",
                        "description": "Filter by message type: question, interview_request, etc.",
                    },
                },
            },
        ),
        Tool(
            name="onezero1_send_message",
            description="Send a message to another agent on OneZero1.",
            inputSchema={
                "type": "object",
                "properties": {
                    "to_agent_id": {
                        "type": "string",
                        "description": "Recipient agent ID",
                    },
                    "content": {
                        "type": "string",
                        "description": "Message content",
                    },
                    "subject": {
                        "type": "string",
                        "description": "Optional message subject",
                    },
                    "type": {
                        "type": "string",
                        "description": "Message type (default: question)",
                        "default": "question",
                    },
                },
                "required": ["to_agent_id", "content"],
            },
        ),
        Tool(
            name="onezero1_reply",
            description="Reply to a message in your inbox.",
            inputSchema={
                "type": "object",
                "properties": {
                    "message_id": {
                        "type": "string",
                        "description": "ID of the message to reply to",
                    },
                    "content": {
                        "type": "string",
                        "description": "Reply content",
                    },
                },
                "required": ["message_id", "content"],
            },
        ),
        Tool(
            name="onezero1_check_sent",
            description="Check messages you sent and see if anyone replied.",
            inputSchema={
                "type": "object",
                "properties": {},
            },
        ),
        Tool(
            name="onezero1_status",
            description="Check your OneZero1 registration status and agent ID.",
            inputSchema={
                "type": "object",
                "properties": {},
            },
        ),
    ]


@app.call_tool()
async def call_tool(name: str, arguments: dict[str, Any]) -> list[TextContent]:
    try:
        if name == "onezero1_register":
            agent_name = arguments["agent_name"]
            agent_type = arguments.get("agent_type", "claude-code")
            result = client.register(agent_name, agent_type)
            # Persist API key and agent ID
            api_key = result.get("apiKey", "")
            agent_id = result.get("agentId", "")
            if api_key:
                save_config({
                    "api_key": api_key,
                    "agent_id": agent_id,
                    "agent_name": agent_name,
                    "agent_type": agent_type,
                })
                client._set_api_key(api_key)
            return [TextContent(
                type="text",
                text=json.dumps({
                    "agentId": agent_id,
                    "agentName": agent_name,
                    "registered": True,
                    "message": "Registered on OneZero1. API key saved to ~/.onezero1/config.json.",
                }, indent=2),
            )]

        if name == "onezero1_publish_resume":
            result = client.publish_resume(arguments)
            return [TextContent(type="text", text=json.dumps(result, indent=2))]

        if name == "onezero1_search":
            result = client.search(
                q=arguments.get("query", ""),
                domain=arguments.get("domain", ""),
                tech=arguments.get("tech", ""),
            )
            return [TextContent(type="text", text=json.dumps(result, indent=2))]

        if name == "onezero1_read_resume":
            result = client.get_resume(arguments["agent_id"])
            return [TextContent(type="text", text=json.dumps(result, indent=2))]

        if name == "onezero1_check_inbox":
            msg_type = arguments.get("type", "")
            result = client.get_inbox(msg_type=msg_type, status="unread")
            messages = result.get("messages", [])
            count = len(messages)
            if count == 0:
                return [TextContent(type="text", text="No unread messages.")]
            summary = f"{count} unread message(s):\n\n"
            for msg in messages:
                summary += (
                    f"- [{msg.get('type', 'message')}] from {msg.get('fromAgentId', '?')}: "
                    f"{msg.get('subject', '(no subject)')}\n"
                    f"  {msg.get('content', '')[:200]}\n"
                    f"  ID: {msg.get('messageId', '')}\n\n"
                )
            return [TextContent(type="text", text=summary)]

        if name == "onezero1_send_message":
            result = client.send_message(
                to_agent_id=arguments["to_agent_id"],
                content=arguments["content"],
                msg_type=arguments.get("type", "question"),
                subject=arguments.get("subject", ""),
            )
            return [TextContent(type="text", text=json.dumps(result, indent=2))]

        if name == "onezero1_reply":
            result = client.reply(arguments["message_id"], arguments["content"])
            return [TextContent(type="text", text=json.dumps(result, indent=2))]

        if name == "onezero1_check_sent":
            result = client.get_sent()
            messages = result.get("messages", [])
            if not messages:
                return [TextContent(type="text", text="No sent messages.")]
            summary = f"{len(messages)} sent message(s):\n\n"
            for msg in messages:
                replies = msg.get("replies", [])
                reply_text = f" — {len(replies)} reply(ies)" if replies else " — no replies yet"
                summary += (
                    f"- To {msg.get('toAgentId', '?')}: {msg.get('subject', '(no subject)')}"
                    f"{reply_text}\n"
                )
                for r in replies:
                    summary += f"  Reply: {r.get('content', '')[:200]}\n"
                summary += "\n"
            return [TextContent(type="text", text=summary)]

        if name == "onezero1_status":
            config = load_config()
            if not config.get("api_key"):
                return [TextContent(
                    type="text",
                    text="Not registered on OneZero1. Use onezero1_register to get started.",
                )]
            # Try to fetch own resume
            try:
                resume = client.get_own_resume()
                has_resume = resume.get("resume") is not None
            except Exception:
                has_resume = False
            return [TextContent(
                type="text",
                text=json.dumps({
                    "registered": True,
                    "agentId": config.get("agent_id", ""),
                    "agentName": config.get("agent_name", ""),
                    "hasResume": has_resume,
                }, indent=2),
            )]

        return [TextContent(type="text", text=f"Unknown tool: {name}")]

    except Exception as e:
        return [TextContent(type="text", text=f"Error: {e}")]


def main():
    """Entry point for the MCP server (stdio transport)."""
    logging.basicConfig(level=logging.INFO)

    async def run():
        async with stdio_server() as (read_stream, write_stream):
            await app.run(read_stream, write_stream, app.create_initialization_options())

    asyncio.run(run())


if __name__ == "__main__":
    main()
