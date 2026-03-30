# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What This Is

A multi-account Gmail MCP server for Claude Desktop. Exposes 5 tools (list_accounts, search_emails, read_email, create_draft, mark_read) over stdio transport, backed by the Google Gmail API with OAuth 2.0 authentication.

## Running & Setup

```bash
# Activate virtual environment
venv\Scripts\activate        # Windows
source venv/bin/activate     # Unix

# Install dependencies (no requirements.txt exists — these are the deps)
pip install mcp google-auth google-auth-oauthlib google-auth-httplib2 google-api-python-client

# Authenticate all accounts (opens browser for each)
python auth_accounts.py

# Run the server directly (normally launched by Claude Desktop via stdio)
python server.py
```

There are no tests, linter, or build steps configured.

## Architecture

- **server.py** — The MCP server. Registers 5 tools via `list_tools()`, dispatches calls via `call_tool()`. Each tool call independently builds a Gmail API service client via `get_service()` → `get_credentials()`. Stateless between calls.
- **auth_accounts.py** — One-time setup utility. Iterates accounts from config.json and runs OAuth flow for each, caching tokens in `tokens/`.
- **config.json** — Maps account keys (e.g. "personal", "dev") to email addresses. Has a `default_account` fallback.
- **credentials.json** — Google OAuth 2.0 client credentials (shared across all accounts).
- **tokens/** — Cached OAuth tokens per account. Delete a token file to force re-auth.

## Key Behaviors

- **Fuzzy account matching**: `resolve_account()` does substring matching on account keys. If no match, falls back to `DEFAULT_ACCOUNT`. This means "estimates" won't match any key and silently uses the default.
- **Token refresh**: `get_credentials()` auto-refreshes expired tokens. If refresh fails, triggers full re-auth flow.
- **Email parsing**: `read_email` handles both simple and multipart MIME, base64-decodes bodies.
- **Gmail scope**: Uses `gmail.modify` (read + modify, but not delete).

## Claude Desktop Config

The server is configured in Claude Desktop's config as:
```json
{
  "mcpServers": {
    "gmail-multi": {
      "command": "D:\\claude-desktop-connectors\\claude-gmail-mcp\\venv\\Scripts\\python.exe",
      "args": ["D:\\claude-desktop-connectors\\claude-gmail-mcp\\server.py"]
    }
  }
}
```
