# Claude Gmail MCP (
[![Tools](https://img.shields.io/badge/tools-5-green.svg)]()

Local MCP server providing multi-account Gmail access for Claude Desktop. Search, read, draft, and manage emails across multiple Google accounts from a single interface.

## Installation

### Prerequisites

- Python 3.9+
- Claude Desktop
- Google Cloud project with Gmail API enabled
- OAuth 2.0 credentials for each Gmail account

### Setup

> **Run PowerShell as Administrator** (right-click → "Run as administrator")

```powershell
# Create the directory structure (skip if it already exists)
New-Item -ItemType Directory -Force -Path "D:\claude-desktop-connectors\claude-gmail-mcp"

# Navigate into the project folder
cd D:\claude-desktop-connectors\claude-gmail-mcp

# Create virtual environment and install dependencies
python -m venv venv
venv\Scripts\activate
pip install mcp google-auth google-auth-oauthlib google-auth-httplib2 google-api-python-client
```

### Connect to Claude Desktop

Press `Win+R`, type `%APPDATA%\Claude`, open `claude_desktop_config.json` and add to the `mcpServers` section:

```json
"gmail-multi": {
  "command": "D:\\claude-desktop-connectors\\claude-gmail-mcp\\venv\\Scripts\\python.exe",
  "args": [
    "D:\\claude-desktop-connectors\\claude-gmail-mcp\\server.py"
  ]
}
```

Fully quit Claude Desktop (tray icon → Quit) and reopen.

### Authentication

Each Google account requires OAuth 2.0 authentication:

1. Create OAuth credentials in [Google Cloud Console](https://console.cloud.google.com/)
2. Enable the Gmail API for your project
3. Download the credentials JSON and place it in the MCP folder
4. On first run, complete the OAuth flow in your browser for each account
5. Tokens are cached locally for subsequent sessions

## Tools (5)

| Tool | Description |
|------|-------------|
| `list_accounts` | List all connected Gmail accounts |
| `search_emails` | Search emails using Gmail query syntax across accounts |
| `read_email` | Read a specific email message by ID |
| `create_draft` | Create a new email draft in a specified account |
| `mark_read` | Mark one or more emails as read |

## Usage

```
List my Gmail accounts
```

```
Search my email for messages from Amazon in the last week
```

```
Read the latest email in my inbox
```

```
Draft a reply to that email
```

## Project Structure

```
D:\claude-desktop-connectors\claude-gmail-mcp\
├── server.py              ← MCP server (stdio transport)
├── config.json            ← Account configuration
├── venv\                  ← Python virtual environment
├── credentials*.json      ← OAuth credentials per account
└── token*.json            ← Cached auth tokens per account
```

## Troubleshooting

### Claude says it can't find the Gmail tools

Fully quit and relaunch Claude Desktop after editing `claude_desktop_config.json`. Verify the paths use double backslashes `\\` and point to `D:\claude-desktop-connectors\claude-gmail-mcp\`.

### Authentication expired

Delete the relevant `token*.json` file and restart Claude Desktop. You'll be prompted to re-authenticate via browser.

### Server fails to start

Confirm dependencies are installed in the venv:

```powershell
D:\claude-desktop-connectors\claude-gmail-mcp\venv\Scripts\python.exe -c "import mcp, googleapiclient; print('OK')"
```

## License

MIT
