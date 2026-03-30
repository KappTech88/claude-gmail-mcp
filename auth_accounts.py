import json
import pickle
from pathlib import Path
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request

SCOPES = ['https://www.googleapis.com/auth/gmail.modify']
BASE_DIR = Path(__file__).parent
TOKENS_DIR = BASE_DIR / "tokens"
TOKENS_DIR.mkdir(exist_ok=True)

with open(BASE_DIR / "config.json") as f:
    CONFIG = json.load(f)

ACCOUNTS = CONFIG["accounts"]

def get_credentials(account_key):
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

for key in ACCOUNTS:
    print(f"Authenticating: {key} ({ACCOUNTS[key]})")
    get_credentials(key)
    print(f"  Done.")

print("All accounts authenticated.")