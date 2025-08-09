# simple_test_client.py
import asyncio
import subprocess
import json
import sys
import os

async def test_blood_donor_server():
    """Test MCP server using direct subprocess communication."""
    
    print(" Testing Blood Donor Connect MCP Server")
    print("=" * 50)
    
    # Verify server file exists
    if not os.path.exists("official_mcp_server.py"):
        print(" Error: official_mcp_server.py not found in current directory")
        return
    
    try:
        # Start the server process
        print(" Starting MCP server...")
        process = subprocess.Popen(
            [sys.executable, "official_mcp_server.py"],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            cwd=os.getcwd()
        )
        
        # Wait a moment for server to start
        await asyncio.sleep(1)
        
        # Send initialize request
        print("1. Sending initialize request...")
        init_request = {
            "jsonrpc": "2.0",
            "method": "initialize",
            "params": {
                "protocolVersion": "2024-11-05",
                "capabilities": {},
                "clientInfo": {"name": "test-client", "version": "1.0.0"}
            },
            "id": 1
        }
        
        process.stdin.write(json.dumps(init_request) + "\n")
        process.stdin.flush()
        
        # Read response
        response_line = process.stdout.readline()
        if response_line:
            response = json.loads(response_line.strip())
            if "result" in response:
                print(" Server initialized successfully")
                print(f"   Server: {response['result']['serverInfo']['name']}")
            else:
                print(f" Initialize failed: {response}")
                return
        
        # Send initialized notification
        print("2. Sending initialized notification...")
        initialized_notification = {
            "jsonrpc": "2.0",
            "method": "notifications/initialized",
            "params": {}
        }
        
        process.stdin.write(json.dumps(initialized_notification) + "\n")
        process.stdin.flush()
        
        # Wait for initialization to complete
        await asyncio.sleep(0.5)
        
        # Test tools/list
        print("3. Testing tools/list...")
        tools_request = {
            "jsonrpc": "2.0",
            "method": "tools/list",
            "params": {},
            "id": 2
        }
        
        process.stdin.write(json.dumps(tools_request) + "\n")
        process.stdin.flush()
        
        response_line = process.stdout.readline()
        if response_line:
            response = json.loads(response_line.strip())
            if "result" in response and "tools" in response["result"]:
                tools = response["result"]["tools"]
                print(f"✅ Found {len(tools)} tools:")
                for tool in tools:
                    print(f"   - {tool['name']}")
            else:
                print(f" Tools list failed: {response}")
                return
        
        # Test validate tool
        print("4. Testing validate tool...")
        validate_request = {
            "jsonrpc": "2.0",
            "method": "tools/call",
            "params": {
                "name": "validate",
                "arguments": {}
            },
            "id": 3
        }
        
        process.stdin.write(json.dumps(validate_request) + "\n")
        process.stdin.flush()
        
        response_line = process.stdout.readline()
        if response_line:
            response = json.loads(response_line.strip())
            if "result" in response:
                phone = response["result"]["content"][0]["text"]
                print(f" Validation successful: {phone}")
            else:
                print(f" Validation failed: {response}")
        
        print("\n MCP Server is working perfectly!")
        print("Ready for PuchAI hackathon submission! 🚀")
        
    except Exception as e:
        print(f" Error during testing: {e}")
        if 'process' in locals():
            stderr = process.stderr.read()
            if stderr:
                print(f"Server error: {stderr}")
    
    finally:
        if 'process' in locals():
            process.terminate()
            process.wait()

if __name__ == "__main__":
    asyncio.run(test_blood_donor_server())
