import json
import os
import pickle
from pathlib import Path
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp import types
import base64
import email

SCOPES = ['https://www.googleapis.com/auth/gmail.modify']
BASE_DIR = Path(__file__).parent
TOKENS_DIR = BASE_DIR / "tokens"
TOKENS_DIR.mkdir(exist_ok=True)

with open(BASE_DIR / "config.json") as f:
    CONFIG = json.load(f)

ACCOUNTS = CONFIG["accounts"]
DEFAULT_ACCOUNT = CONFIG.get("default_account", list(ACCOUNTS.keys())[0])

def get_credentials(account_key: str) -> Credentials:
    token_path = TOKENS_DIR / f"{account_key}.pickle"
    creds = None

    if token_path.exists():
        with open(token_path, "rb") as f:
            creds = pickle.load(f)

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(
                BASE_DIR / "credentials.json", SCOPES
            )
            creds = flow.run_local_server(port=0)
        with open(token_path, "wb") as f:
            pickle.dump(creds, f)

    return creds

def get_service(account_key: str):
    creds = get_credentials(account_key)
    return build("gmail", "v1", credentials=creds)

def resolve_account(account_key: str | None) -> str:
    if not account_key:
        return DEFAULT_ACCOUNT
    if account_key in ACCOUNTS:
        return account_key
    # fuzzy match — lets Claude say "estimates account" and still find it
    for key in ACCOUNTS:
        if account_key.lower() in key.lower() or key.lower() in account_key.lower():
            return key
    return DEFAULT_ACCOUNT

server = Server("gmail-multi")

@server.list_tools()
async def list_tools() -> list[types.Tool]:
    account_list = ", ".join(ACCOUNTS.keys())
    return [
        types.Tool(
            name="list_accounts",
            description="List all connected Gmail accounts",
            inputSchema={"type": "object", "properties": {}}
        ),
        types.Tool(
            name="search_emails",
            description=f"Search emails in a Gmail account. Available accounts: {account_list}",
            inputSchema={
                "type": "object",
                "properties": {
                    "account": {"type": "string", "description": f"Account key ({account_list}) — defaults to {DEFAULT_ACCOUNT}"},
                    "query": {"type": "string", "description": "Gmail search query (e.g. 'from:someone@email.com is:unread')"},
                    "max_results": {"type": "integer", "description": "Max emails to return (default 10)"}
                },
                "required": ["query"]
            }
        ),
        types.Tool(
            name="read_email",
            description="Read a specific email by ID",
            inputSchema={
                "type": "object",
                "properties": {
                    "account": {"type": "string"},
                    "message_id": {"type": "string", "description": "Gmail message ID"}
                },
                "required": ["message_id"]
            }
        ),
        types.Tool(
            name="create_draft",
            description="Create an email draft in a Gmail account",
            inputSchema={
                "type": "object",
                "properties": {
                    "account": {"type": "string"},
                    "to": {"type": "string"},
                    "subject": {"type": "string"},
                    "body": {"type": "string"}
                },
                "required": ["to", "subject", "body"]
            }
        ),
        types.Tool(
            name="mark_read",
            description="Mark an email as read",
            inputSchema={
                "type": "object",
                "properties": {
                    "account": {"type": "string"},
                    "message_id": {"type": "string"}
                },
                "required": ["message_id"]
            }
        )
    ]

@server.call_tool()
async def call_tool(name: str, arguments: dict) -> list[types.TextContent]:
    account_key = resolve_account(arguments.get("account"))
    
    if name == "list_accounts":
        result = "Connected Gmail accounts:\n"
        for key, email_addr in ACCOUNTS.items():
            marker = " (default)" if key == DEFAULT_ACCOUNT else ""
            result += f"  {key}: {email_addr}{marker}\n"
        return [types.TextContent(type="text", text=result)]

    elif name == "search_emails":
        service = get_service(account_key)
        query = arguments["query"]
        max_results = arguments.get("max_results", 10)
        
        results = service.users().messages().list(
            userId="me", q=query, maxResults=max_results
        ).execute()
        
        messages = results.get("messages", [])
        if not messages:
            return [types.TextContent(type="text", text=f"No emails found in [{account_key}] for query: {query}")]
        
        output = f"Found {len(messages)} emails in [{account_key}] ({ACCOUNTS[account_key]}):\n\n"
        for msg in messages:
            detail = service.users().messages().get(
                userId="me", id=msg["id"], format="metadata",
                metadataHeaders=["From", "Subject", "Date"]
            ).execute()
            headers = {h["name"]: h["value"] for h in detail["payload"]["headers"]}
            output += f"ID: {msg['id']}\n"
            output += f"From: {headers.get('From', 'Unknown')}\n"
            output += f"Subject: {headers.get('Subject', 'No subject')}\n"
            output += f"Date: {headers.get('Date', 'Unknown')}\n\n"
        
        return [types.TextContent(type="text", text=output)]

    elif name == "read_email":
        service = get_service(account_key)
        msg = service.users().messages().get(
            userId="me", id=arguments["message_id"], format="full"
        ).execute()
        
        headers = {h["name"]: h["value"] for h in msg["payload"]["headers"]}
        body = ""
        
        if "parts" in msg["payload"]:
            for part in msg["payload"]["parts"]:
                if part["mimeType"] == "text/plain":
                    body = base64.urlsafe_b64decode(part["body"]["data"]).decode("utf-8")
                    break
        elif "body" in msg["payload"] and "data" in msg["payload"]["body"]:
            body = base64.urlsafe_b64decode(msg["payload"]["body"]["data"]).decode("utf-8")
        
        output = f"Account: [{account_key}] {ACCOUNTS[account_key]}\n"
        output += f"From: {headers.get('From')}\n"
        output += f"To: {headers.get('To')}\n"
        output += f"Subject: {headers.get('Subject')}\n"
        output += f"Date: {headers.get('Date')}\n\n"
        output += body
        
        return [types.TextContent(type="text", text=output)]

    elif name == "create_draft":
        service = get_service(account_key)
        message = f"To: {arguments['to']}\nSubject: {arguments['subject']}\n\n{arguments['body']}"
        encoded = base64.urlsafe_b64encode(message.encode()).decode()
        draft = service.users().drafts().create(
            userId="me", body={"message": {"raw": encoded}}
        ).execute()
        
        return [types.TextContent(type="text", text=f"Draft created in [{account_key}] ({ACCOUNTS[account_key]}). Draft ID: {draft['id']}")]

    elif name == "mark_read":
        service = get_service(account_key)
        service.users().messages().modify(
            userId="me", id=arguments["message_id"],
            body={"removeLabelIds": ["UNREAD"]}
        ).execute()
        return [types.TextContent(type="text", text=f"Marked as read in [{account_key}]")]

    return [types.TextContent(type="text", text=f"Unknown tool: {name}")]

async def main():
    async with stdio_server() as (read_stream, write_stream):
        await server.run(read_stream, write_stream, server.create_initialization_options())

if __name__ == "__main__":
    import asyncio
    asyncio.run(main())