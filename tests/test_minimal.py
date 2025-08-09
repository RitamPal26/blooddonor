# test_minimal.py
import asyncio
import os
from dotenv import load_dotenv
from fastmcp import FastMCP
from fastmcp.server.auth.providers.bearer import BearerAuthProvider, RSAKeyPair
from mcp.server.auth.provider import AccessToken
from typing import Annotated
from pydantic import Field

load_dotenv()
TOKEN = os.environ.get("AUTH_TOKEN", "your-super-secret-token-12345")

class SimpleBearerAuthProvider(BearerAuthProvider):
    def __init__(self, token: str):
        k = RSAKeyPair.generate()
        super().__init__(public_key=k.public_key, jwks_uri=None, issuer=None, audience=None)
        self.token = token

    async def load_access_token(self, token: str) -> AccessToken | None:
        if token == self.token:
            return AccessToken(token=token, client_id="puch-client", scopes=["*"], expires_at=None)
        return None

# Create minimal MCP server
mcp = FastMCP("Test Blood Donor Server", auth=SimpleBearerAuthProvider(TOKEN))

@mcp.tool
async def validate() -> str:
    """Validation tool that returns your phone number."""
    return "918910662391"

@mcp.tool
async def register_donor(
    name: Annotated[str, Field(description="Donor's full name")],
    blood_type: Annotated[str, Field(description="Blood type")]
) -> str:
    """Register a new blood donor."""
    return f"Successfully registered {name} with blood type {blood_type}"

async def main():
    print("=== Minimal MCP Server Starting ===")
    print(f"Server: {mcp.name}")
    await mcp.run_async("streamable-http", host="0.0.0.0", port=8087)

if __name__ == "__main__":
    asyncio.run(main())
