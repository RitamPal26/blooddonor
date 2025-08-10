# Enhanced Blood Donor Connect India - Hospital Selection Based MCP Server

import asyncio
import logging
import os
import json
from datetime import datetime
from typing import Any, Sequence

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
from geopy.distance import geodesic

import mcp.types as types
from mcp.server import NotificationOptions, Server
from mcp.server.models import InitializationOptions
import mcp.server.stdio

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("blood-donor-india")

# Create MCP server
server = Server("blood-donor-india")

# In-memory storage
donors = []
requests = []
MY_NUMBER = "918910662391"

# Data persistence file
DATA_FILE = "blood_donor_data.json"

# Complete Hospital database with coordinates for all major Indian cities
HOSPITALS = {
    "mumbai": [
        {"name": "Tata Memorial Hospital", "lat": 19.0110, "lng": 72.8569, "emergency": "022-2417-7000", "blood_bank": "022-2417-7100"},
        {"name": "Lilavati Hospital", "lat": 19.0520, "lng": 72.8270, "emergency": "022-2640-5000", "blood_bank": "022-2640-5100"},
        {"name": "KEM Hospital", "lat": 18.9893, "lng": 72.8371, "emergency": "022-2413-6051", "blood_bank": "022-2413-6052"},
        {"name": "Apollo Hospital Mumbai", "lat": 19.0896, "lng": 72.8656, "emergency": "022-2692-7777", "blood_bank": "022-2692-7800"}
    ],
    "delhi": [
        {"name": "AIIMS Delhi", "lat": 28.5672, "lng": 77.2100, "emergency": "011-2658-8500", "blood_bank": "011-2658-8700"},
        {"name": "Apollo Hospital Delhi", "lat": 28.5245, "lng": 77.2721, "emergency": "011-2692-5858", "blood_bank": "011-2692-5900"},
        {"name": "Max Super Speciality", "lat": 28.5933, "lng": 77.0571, "emergency": "011-2651-5050", "blood_bank": "011-2651-5100"},
        {"name": "Fortis Hospital Delhi", "lat": 28.5011, "lng": 77.0734, "emergency": "011-4277-6222", "blood_bank": "011-4277-6300"}
    ],
    "bangalore": [
        {"name": "Manipal Hospital", "lat": 12.9698, "lng": 77.7500, "emergency": "080-2502-4444", "blood_bank": "080-2502-4500"},
        {"name": "Apollo Hospital Bangalore", "lat": 12.9176, "lng": 77.6101, "emergency": "080-2630-0100", "blood_bank": "080-2630-0200"},
        {"name": "Narayana Health City", "lat": 12.8449, "lng": 77.6679, "emergency": "080-7122-4444", "blood_bank": "080-7122-4500"},
        {"name": "Fortis Hospital Bangalore", "lat": 12.9591, "lng": 77.7050, "emergency": "080-6621-4444", "blood_bank": "080-6621-4500"}
    ],
    "chennai": [
        {"name": "Apollo Hospital Chennai", "lat": 13.0358, "lng": 80.2297, "emergency": "044-2829-3333", "blood_bank": "044-2829-4444"},
        {"name": "Fortis Malar", "lat": 13.0645, "lng": 80.2623, "emergency": "044-4289-4289", "blood_bank": "044-4289-4200"},
        {"name": "MIOT Hospital", "lat": 13.0103, "lng": 80.2095, "emergency": "044-4200-4200", "blood_bank": "044-4200-4300"},
        {"name": "Stanley Medical College", "lat": 13.0901, "lng": 80.2707, "emergency": "044-2829-8256", "blood_bank": "044-2829-8300"}
    ],
    "kolkata": [
        {"name": "Apollo Gleneagles", "lat": 22.5179, "lng": 88.3493, "emergency": "033-2320-3040", "blood_bank": "033-2320-3100"},
        {"name": "AMRI Hospital", "lat": 22.4953, "lng": 88.3709, "emergency": "033-6606-3800", "blood_bank": "033-6606-3900"},
        {"name": "Fortis Hospital Kolkata", "lat": 22.6203, "lng": 88.4371, "emergency": "033-6628-4444", "blood_bank": "033-6628-4500"},
        {"name": "Medical College Kolkata", "lat": 22.5726, "lng": 88.3639, "emergency": "033-2241-5400", "blood_bank": "033-2241-5500"}
    ],
    "hyderabad": [
        {"name": "Apollo Hospital Hyderabad", "lat": 17.4435, "lng": 78.3772, "emergency": "040-2355-1020", "blood_bank": "040-2355-1100"},
        {"name": "CARE Hospital", "lat": 17.4399, "lng": 78.4482, "emergency": "040-6165-6565", "blood_bank": "040-6165-6600"},
        {"name": "Continental Hospital", "lat": 17.4924, "lng": 78.3570, "emergency": "040-6734-6734", "blood_bank": "040-6734-6800"},
        {"name": "Yashoda Hospital", "lat": 17.4239, "lng": 78.4738, "emergency": "040-4466-7777", "blood_bank": "040-4466-7800"}
    ],
    "pune": [
        {"name": "Ruby Hall Clinic", "lat": 18.5196, "lng": 73.8553, "emergency": "020-2611-2211", "blood_bank": "020-2611-2300"},
        {"name": "Sahyadri Hospital", "lat": 18.5679, "lng": 73.9143, "emergency": "020-2426-6666", "blood_bank": "020-2426-6700"},
        {"name": "KEM Hospital Pune", "lat": 18.4894, "lng": 73.8550, "emergency": "020-2612-1071", "blood_bank": "020-2612-1100"},
        {"name": "Manipal Hospital Pune", "lat": 18.5139, "lng": 73.9275, "emergency": "020-4466-5555", "blood_bank": "020-4466-5600"}
    ]
}

# Helper functions with all fixes
def save_data():
    """Save donors and requests to file"""
    data = {
        "donors": donors,
        "requests": requests,
        "last_updated": datetime.now().isoformat()
    }
    try:
        with open(DATA_FILE, "w") as f:
            json.dump(data, f, indent=2)
        logger.info(f"Data saved: {len(donors)} donors, {len(requests)} requests")
    except Exception as e:
        logger.error(f"Failed to save data: {e}")

def load_data():
    """Load donors and requests from file"""
    global donors, requests
    try:
        if os.path.exists(DATA_FILE):
            with open(DATA_FILE, "r") as f:
                data = json.load(f)
                donors = data.get("donors", [])
                requests = data.get("requests", [])
                logger.info(f"Loaded {len(donors)} donors and {len(requests)} requests")
    except Exception as e:
        logger.error(f"Failed to load data: {e}")
        donors = []
        requests = []

def get_all_cities():
    """Get list of all available cities"""
    return list(HOSPITALS.keys())

def get_hospitals_in_city(city):
    """Get all hospitals in a specific city"""
    return HOSPITALS.get(city.lower(), [])

def find_hospital_by_name(hospital_name, city=None):
    """Find hospital by name with disambiguation for multiple matches"""
    matches = []
    
    # Search within specific city first if provided
    if city:
        city_hospitals = HOSPITALS.get(city.lower(), [])
        for hospital in city_hospitals:
            if hospital_name.lower() in hospital["name"].lower():
                matches.append((hospital, city.lower()))
    
    # If no matches found in the specified city, or if no city was provided, search all cities
    if not matches:
        for city_name, hospitals in HOSPITALS.items():
            # Avoid re-searching the same city
            if city and city_name == city.lower():
                continue
            for hospital in hospitals:
                if hospital_name.lower() in hospital["name"].lower():
                    matches.append((hospital, city_name))
    
    if not matches:
        return None, None
    elif len(matches) == 1:
        return matches[0]  # Returns (hospital_dict, city_name)
    else:
        # Multiple matches - need disambiguation
        return "multiple", matches # Returns ("multiple", list_of_matches)

def validate_blood_type(blood_type):
    """Validate blood type format"""
    valid_types = ["O+", "A+", "B+", "AB+", "O-", "A-", "B-", "AB-"]
    return blood_type.upper() in valid_types

def validate_city(city):
    """Validate city name"""
    return city.lower() in HOSPITALS.keys()

@server.list_tools()
async def handle_list_tools() -> list[types.Tool]:
    """List available blood donor tools with hospital selection."""
    return [
        types.Tool(
            name="donor_help",
            description="Shows all available commands and help for the blood donor tool set.",
            inputSchema={
                "type": "object",
                "properties": {
                    "tool_name": {"type": "string", "description": "Optional: Get detailed help for a specific command"}
                },
            },
        ),
        types.Tool(
            name="validate",
            description="Validation tool that returns your phone number for PuchAI",
            inputSchema={
                "type": "object",
                "properties": {},
            },
        ),
        types.Tool(
            name="register_blood_donor",
            description="Register a new blood donor by selecting their nearest hospital in India",
            inputSchema={
                "type": "object",
                "properties": {
                    "name": {"type": "string", "description": "Donor's full name"},
                    "blood_type": {"type": "string", "description": "Blood type (O+, A+, B+, AB+, O-, A-, B-, AB-)"},
                    "city": {"type": "string", "description": "City where donor is located", "enum": list(HOSPITALS.keys())},
                    "hospital_name": {"type": "string", "description": "Name of nearest hospital (partial name is okay)"},
                    "phone": {"type": "string", "description": "Contact phone number"},
                },
                "required": ["name", "blood_type", "city", "hospital_name", "phone"],
            },
        ),
        types.Tool(
            name="get_hospital_details",
            description="Get detailed information for hospitals in a specific city with pagination",
            inputSchema={
                "type": "object",
                "properties": {
                    "city": {"type": "string", "description": "City name", "enum": list(HOSPITALS.keys())},
                    "start_index": {"type": "integer", "description": "Starting hospital index", "default": 0},
                    "limit": {"type": "integer", "description": "Number of hospitals to return", "default": 2}
                },
                "required": ["city"]
            },
        ),
        types.Tool(
            name="find_nearby_donors",
            description="Find compatible blood donors near a specific hospital in India",
            inputSchema={
                "type": "object",
                "properties": {
                    "blood_type": {"type": "string", "description": "Required blood type"},
                    "city": {"type": "string", "description": "City to search in", "enum": list(HOSPITALS.keys())},
                    "hospital_name": {"type": "string", "description": "Hospital name for location reference"},
                    "radius_km": {"type": "integer", "description": "Search radius in kilometers", "default": 10},
                },
                "required": ["blood_type", "city", "hospital_name"],
            },
        ),
        types.Tool(
            name="emergency_blood_request",
            description="Create emergency blood donation request at a specific hospital in India",
            inputSchema={
                "type": "object",
                "properties": {
                    "patient_name": {"type": "string", "description": "Patient name needing blood"},
                    "blood_type": {"type": "string", "description": "Required blood type"},
                    "city": {"type": "string", "description": "City where hospital is located", "enum": list(HOSPITALS.keys())},
                    "hospital_name": {"type": "string", "description": "Hospital name where patient is admitted"},
                    "urgency": {"type": "string", "description": "Urgency level", "default": "high"},
                },
                "required": ["patient_name", "blood_type", "city", "hospital_name"],
            },
        ),
        types.Tool(
            name="list_hospitals_by_city",
            description="List all available hospitals in a specific city or all cities in India",
            inputSchema={
                "type": "object",
                "properties": {
                    "city": {"type": "string", "description": "City name (optional - shows all cities if not specified)", "enum": list(HOSPITALS.keys()) + ["all"]},
                },
            },
        ),
        # CORRECTED: Added pagination to list_donors
        types.Tool(
            name="list_donors",
            description="List all registered blood donors across India with pagination",
            inputSchema={
                "type": "object",
                "properties": {
                    "start_index": {"type": "integer", "description": "Starting donor index", "default": 0},
                    "limit": {"type": "integer", "description": "Number of donors to return", "default": 3}
                },
            },
        ),
    ]

@server.call_tool()
async def handle_call_tool(name: str, arguments: dict[str, Any] | None) -> list[types.TextContent]:
    """Handle tool calls for blood donor operations with hospital selection."""
    
    try:
        if name == "validate":
            return [types.TextContent(type="text", text=MY_NUMBER)]
        
        elif name == "donor_help":
            # (Help logic remains the same, omitted for brevity but should be kept in your file)
            tool_name = arguments.get("tool_name") if arguments else None
            
            if tool_name:
                # Specific help content...
                result = f"Help for {tool_name}..."
            else:
                # General help content...
                result = "General help..."
            return [types.TextContent(type="text", text=result)]
        
        elif name == "register_blood_donor":
            if not arguments:
                return [types.TextContent(type="text", text="❌ Missing registration information!")]

            required_fields = ["name", "blood_type", "city", "hospital_name", "phone"]
            missing_fields = [field for field in required_fields if not arguments.get(field)]
            if missing_fields:
                return [types.TextContent(type="text", text=f"❌ Missing required information: {', '.join(missing_fields)}")]

            if not validate_blood_type(arguments.get("blood_type", "")):
                return [types.TextContent(type="text", text="❌ Invalid blood type. Please use: O+, A+, B+, AB+, O-, A-, B-, AB-")]
            
            if not validate_city(arguments.get("city", "")):
                return [types.TextContent(type="text", text=f"❌ Invalid city. Available cities: {', '.join(get_all_cities())}")]
            
            city = arguments["city"].lower()
            hospital_name = arguments["hospital_name"]
            
            hospital_result, found_data = find_hospital_by_name(hospital_name, city)
            
            if hospital_result is None:
                available_hospitals = get_hospitals_in_city(city)
                hospital_list = ", ".join([h["name"] for h in available_hospitals])
                return [types.TextContent(type="text", text=f"❌ Hospital '{hospital_name}' not found in {city.title()}.\nAvailable hospitals: {hospital_list}")]
            
            elif hospital_result == "multiple":
                match_list = "\n".join([f"• {h[0]['name']} in {h[1].title()}" for h in found_data])
                return [types.TextContent(type="text", text=f"❌ Multiple hospitals found for '{hospital_name}':\n\n{match_list}\n\nPlease be more specific.")]

            else:
                hospital, found_city = hospital_result, found_data
                
                # Create donor record
                donor = {
                    "name": arguments["name"],
                    "blood_type": arguments["blood_type"].upper(),
                    "city": found_city,
                    "hospital": hospital["name"],
                    "phone": arguments["phone"],
                    "latitude": hospital["lat"],
                    "longitude": hospital["lng"]
                }
                donors.append(donor)
                save_data()
                
                result = (f"✅ Blood donor registered successfully!\n\n"
                          f"👤 Name: {donor['name']}\n"
                          f"🩸 Blood Type: {donor['blood_type']}\n"
                          f"🏙️ City: {found_city.title()}\n"
                          f"🏥 Hospital: {hospital['name']}\n"
                          f"📞 Phone: {donor['phone']}\n"
                          f"🚨 Emergency Contact: {hospital['emergency']}\n"
                          f"🩸 Blood Bank: {hospital['blood_bank']}")
                return [types.TextContent(type="text", text=result)]
        
        # CORRECTED: `find_nearby_donors` with robust hospital checking
        elif name == "find_nearby_donors":
            if not arguments:
                return [types.TextContent(type="text", text="❌ Missing arguments for find_nearby_donors")]

            blood_type = arguments["blood_type"].upper()
            city = arguments["city"].lower()
            hospital_name = arguments["hospital_name"]
            radius_km = arguments.get("radius_km", 10)

            hospital_result, found_data = find_hospital_by_name(hospital_name, city)

            if hospital_result is None:
                return [types.TextContent(type="text", text=f"❌ Hospital '{hospital_name}' not found in {city.title()}")]
            
            if hospital_result == "multiple":
                match_list = "\n".join([f"• {h[0]['name']} in {h[1].title()}" for h in found_data])
                return [types.TextContent(type="text", text=f"❌ Multiple hospitals found for '{hospital_name}'. Please be more specific:\n\n{match_list}")]
            
            hospital = hospital_result
            
            hospital_location = (hospital["lat"], hospital["lng"])
            nearby_donors = []
            
            for donor in donors:
                if donor["blood_type"] == blood_type:
                    donor_location = (donor["latitude"], donor["longitude"])
                    distance = geodesic(hospital_location, donor_location).kilometers
                    
                    if distance <= radius_km:
                        donor_copy = donor.copy()
                        donor_copy['distance_km'] = round(distance, 2)
                        nearby_donors.append(donor_copy)
            
            nearby_donors.sort(key=lambda x: x['distance_km'])
            
            if nearby_donors:
                result = f"🩸 Found {len(nearby_donors)} {blood_type} donors within {radius_km}km of {hospital['name']}:\n\n"
                for i, donor in enumerate(nearby_donors[:5], 1):
                    result += f"{i}. {donor['name']} ({donor['city'].title()})\n"
                    result += f"   📍 Hospital: {donor['hospital']}\n"
                    result += f"   📏 Distance: {donor['distance_km']}km\n"
                    result += f"   📞 Phone: {donor['phone']}\n\n"
            else:
                result = f"❌ No {blood_type} donors found within {radius_km}km of {hospital['name']} in {city.title()}"
            
            return [types.TextContent(type="text", text=result)]

        # CORRECTED: `emergency_blood_request` with robust hospital checking
        elif name == "emergency_blood_request":
            if not arguments:
                return [types.TextContent(type="text", text="Missing arguments for emergency_blood_request")]
            
            city = arguments["city"].lower()
            hospital_name = arguments["hospital_name"]
            
            hospital_result, found_data = find_hospital_by_name(hospital_name, city)

            if hospital_result is None:
                return [types.TextContent(type="text", text=f"❌ Hospital '{hospital_name}' not found in {city.title()}")]
            
            if hospital_result == "multiple":
                match_list = "\n".join([f"• {h[0]['name']} in {h[1].title()}" for h in found_data])
                return [types.TextContent(type="text", text=f"❌ Multiple hospitals found. Please be more specific:\n\n{match_list}")]
            
            hospital = hospital_result
            found_city = found_data
            
            request = {
                "patient_name": arguments["patient_name"],
                "blood_type": arguments["blood_type"].upper(),
                "city": found_city,
                "hospital": hospital,
                "urgency": arguments.get("urgency", "high")
            }
            requests.append(request)
            save_data()
            # ... (rest of logic to find donors for the request) ...
            return [types.TextContent(type="text", text=f"🚨 Emergency request created at {hospital['name']} for {request['patient_name']}.")]
        
        elif name == "list_hospitals_by_city":
            # (This logic remains the same, omitted for brevity but should be kept in your file)
            city_filter = arguments.get("city", "all").lower() if arguments else "all"
            if city_filter == "all":
                result = "Showing all cities..."
            else:
                result = f"Showing hospitals for {city_filter}..."
            return [types.TextContent(type="text", text=result)]

        # NEW: Implemented `get_hospital_details` tool logic
        elif name == "get_hospital_details":
            if not arguments or not arguments.get("city"):
                return [types.TextContent(type="text", text="❌ City is required. Usage: get_hospital_details city='<city_name>'")]

            city = arguments["city"].lower()
            start_index = arguments.get("start_index", 0)
            limit = arguments.get("limit", 2)

            city_hospitals = get_hospitals_in_city(city)

            if not city_hospitals:
                return [types.TextContent(type="text", text=f"❌ City '{city}' not found.")]

            paginated_hospitals = city_hospitals[start_index : start_index + limit]
            
            if not paginated_hospitals:
                return [types.TextContent(type="text", text=f"🏥 No more hospitals to show for {city.title()}.")]

            result = f"🏥 Hospitals in {city.title()} ({start_index + 1} to {start_index + len(paginated_hospitals)} of {len(city_hospitals)}):\n\n"
            for i, hospital in enumerate(paginated_hospitals, start=start_index + 1):
                result += f"{i}. {hospital['name']}\n"
                result += f"   🚨 Emergency: {hospital['emergency']}\n"
                result += f"   🩸 Blood Bank: {hospital['blood_bank']}\n\n"

            if start_index + limit < len(city_hospitals):
                result += f"💡 To see more, use start_index={start_index + limit}"
            
            return [types.TextContent(type="text", text=result)]

        # CORRECTED: `list_donors` with pagination
        elif name == "list_donors":
            start_index = arguments.get("start_index", 0) if arguments else 0
            limit = arguments.get("limit", 3) if arguments else 3

            if not donors:
                return [types.TextContent(type="text", text="📋 No donors registered yet.")]

            paginated_donors = donors[start_index : start_index + limit]

            if not paginated_donors:
                return [types.TextContent(type="text", text=f"📋 No more donors to show. Total: {len(donors)}")]

            result = f"🩸 Registered Donors ({start_index + 1} to {start_index + len(paginated_donors)} of {len(donors)}):\n\n"
            for i, donor in enumerate(paginated_donors, start=start_index + 1):
                result += f"{i}. {donor['name']} - {donor['blood_type']}\n"
                result += f"   📍 City: {donor['city'].title()}\n"
                result += f"   🏥 Hospital: {donor['hospital']}\n"
                result += f"   📞 Phone: {donor['phone']}\n\n"
            
            if start_index + limit < len(donors):
                result += f"💡 To see more, use start_index={start_index + limit}"

            return [types.TextContent(type="text", text=result)]
        
        else:
            return [types.TextContent(type="text", text=f"Unknown tool: {name}")]
    
    except Exception as e:
        logger.error(f"Error in tool {name}: {str(e)}", exc_info=True)
        return [types.TextContent(type="text", text=f"Error processing {name}: {str(e)}")]

# Create FastAPI app with CORS support
app = FastAPI(title="Blood Donor Connect India - Hospital Selection Based")

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Standard HTTP endpoints for Railway compatibility
@app.get("/")
async def root():
    return {"message": "🩸 Blood Donor Connect India - Server is Running"}

@app.get("/health")
async def health_check():
    return {"status": "healthy"}

@app.get("/validate")
async def validate_endpoint():
    return {"phone": MY_NUMBER}

# MCP JSON-RPC endpoint
@app.post("/mcp")
async def mcp_endpoint(request: Request):
    """Handle MCP JSON-RPC requests with comprehensive error handling"""
    try:
        payload = await request.json()
        
        if not payload.get("jsonrpc") == "2.0" or not payload.get("method"):
            raise HTTPException(status_code=400, detail="Invalid JSON-RPC request")

        method = payload["method"]
        req_id = payload.get("id")

        if method == "initialize":
            return {
                "jsonrpc": "2.0", "id": req_id,
                "result": {
                    "protocolVersion": "2024-11-05",
                    "capabilities": {"tools": {"listChanged": False}},
                    "serverInfo": {"name": "blood-donor-india", "version": "1.0.0"}
                }
            }
        
        elif method == "notifications/initialized":
            return JSONResponse({"status": "acknowledged"})
        
        elif method == "tools/list":
            tools = await handle_list_tools()
            return {
                "jsonrpc": "2.0", "id": req_id,
                "result": {
                    "tools": [{"name": t.name, "description": t.description, "inputSchema": t.inputSchema} for t in tools]
                }
            }
        
        elif method == "tools/call":
            params = payload.get("params", {})
            tool_name = params.get("name")
            arguments = params.get("arguments", {})
            
            if not tool_name:
                raise HTTPException(status_code=400, detail="Missing tool name in call")

            result_content = await handle_call_tool(tool_name, arguments)
            
            return {
                "jsonrpc": "2.0", "id": req_id,
                "result": {
                    "content": [{"type": item.type, "text": item.text} for item in result_content]
                }
            }
        
        else:
            return {
                "jsonrpc": "2.0", "id": req_id,
                "error": {"code": -32601, "message": f"Method not found: {method}"}
            }

    except Exception as e:
        logger.error(f"Error in MCP endpoint: {str(e)}", exc_info=True)
        req_id = None
        if 'payload' in locals() and isinstance(payload, dict):
            req_id = payload.get("id")
        return JSONResponse(
            status_code=500,
            content={
                "jsonrpc": "2.0", "id": req_id,
                "error": {"code": -32603, "message": "Internal server error", "data": str(e)}
            }
        )

@app.options("/mcp")
async def mcp_options():
    return {"status": "ok"}

async def main():
    print("=== Blood Donor Connect MCP Server for India ===")
    load_data()
    port = int(os.environ.get("PORT", 8080))
    host = "0.0.0.0"
    
    print(f"🌐 Starting HTTP server on {host}:{port}")
    print("📡 MCP endpoint available at /mcp")
    
    config = uvicorn.Config(app, host=host, port=port, log_level="info")
    server_instance = uvicorn.Server(config)
    await server_instance.serve()

if __name__ == "__main__":
    asyncio.run(main())