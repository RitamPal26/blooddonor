# official_mcp_server.py
import asyncio
import logging
from mcp.server import NotificationOptions, Server
from mcp.server.models import InitializationOptions
import mcp.server.stdio
import mcp.types as types
from typing import Any, Sequence
from geopy.distance import geodesic

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("blood-donor-india")

# Create MCP server
server = Server("blood-donor-india")

# In-memory storage
donors = []
requests = []
MY_NUMBER = "918910662391"

@server.list_tools()
async def handle_list_tools() -> list[types.Tool]:
    """List available blood donor tools."""
    return [
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
            description="Register a new blood donor anywhere in India with GPS location",
            inputSchema={
                "type": "object",
                "properties": {
                    "name": {"type": "string", "description": "Donor's full name"},
                    "blood_type": {"type": "string", "description": "Blood type (O+, A+, B+, AB+, O-, A-, B-, AB-)"},
                    "latitude": {"type": "number", "description": "Latitude coordinate in India"},
                    "longitude": {"type": "number", "description": "Longitude coordinate in India"},
                    "phone": {"type": "string", "description": "Contact phone number"},
                },
                "required": ["name", "blood_type", "latitude", "longitude", "phone"],
            },
        ),
        types.Tool(
            name="find_nearby_donors",
            description="Find compatible blood donors within specified radius anywhere in India",
            inputSchema={
                "type": "object",
                "properties": {
                    "blood_type": {"type": "string", "description": "Required blood type"},
                    "latitude": {"type": "number", "description": "Patient/hospital latitude"},
                    "longitude": {"type": "number", "description": "Patient/hospital longitude"},
                    "radius_km": {"type": "integer", "description": "Search radius in kilometers", "default": 10},
                },
                "required": ["blood_type", "latitude", "longitude"],
            },
        ),
        types.Tool(
            name="emergency_blood_request",
            description="Create emergency blood donation request at any hospital in India",
            inputSchema={
                "type": "object",
                "properties": {
                    "patient_name": {"type": "string", "description": "Patient name needing blood"},
                    "blood_type": {"type": "string", "description": "Required blood type"},
                    "hospital_name": {"type": "string", "description": "Hospital name in India"},
                    "latitude": {"type": "number", "description": "Hospital latitude"},
                    "longitude": {"type": "number", "description": "Hospital longitude"},
                    "urgency": {"type": "string", "description": "Urgency level", "default": "high"},
                },
                "required": ["patient_name", "blood_type", "hospital_name", "latitude", "longitude"],
            },
        ),
        types.Tool(
            name="india_hospitals",  
            description="Get major hospitals across India with emergency blood bank contacts",
            inputSchema={
                "type": "object",
                "properties": {
                    "city": {"type": "string", "description": "City name (optional - returns all if not specified)", "default": "all"}
                },
            },
        ),
        types.Tool(
            name="list_donors",
            description="List all registered blood donors across India",
            inputSchema={
                "type": "object",
                "properties": {},
            },
        ),
    ]

@server.call_tool()
async def handle_call_tool(name: str, arguments: dict[str, Any] | None) -> list[types.TextContent]:
    """Handle tool calls for blood donor operations."""
    
    if name == "validate":
        return [types.TextContent(type="text", text=MY_NUMBER)]
    
    elif name == "register_blood_donor":
        if not arguments:
            raise ValueError("Missing arguments for register_blood_donor")
        
        donor = {
            "name": arguments["name"],
            "blood_type": arguments["blood_type"],
            "latitude": arguments["latitude"],
            "longitude": arguments["longitude"],
            "phone": arguments["phone"]
        }
        donors.append(donor)
        
        result = f"✅ Successfully registered {donor['name']} as {donor['blood_type']} blood donor in India at coordinates ({donor['latitude']}, {donor['longitude']}). Total donors: {len(donors)}"
        return [types.TextContent(type="text", text=result)]
    
    elif name == "find_nearby_donors":
        if not arguments:
            raise ValueError("Missing arguments for find_nearby_donors")
        
        blood_type = arguments["blood_type"]
        latitude = arguments["latitude"]
        longitude = arguments["longitude"]
        radius_km = arguments.get("radius_km", 10)
        
        request_location = (latitude, longitude)
        nearby_donors = []
        
        for donor in donors:
            if donor["blood_type"] == blood_type:
                donor_location = (donor["latitude"], donor["longitude"])
                distance = geodesic(request_location, donor_location).kilometers
                
                if distance <= radius_km:
                    donor_copy = donor.copy()
                    donor_copy['distance_km'] = round(distance, 2)
                    nearby_donors.append(donor_copy)
        
        nearby_donors.sort(key=lambda x: x['distance_km'])
        
        if nearby_donors:
            result = f"🩸 Found {len(nearby_donors)} {blood_type} donors within {radius_km}km:\n"
            for i, donor in enumerate(nearby_donors[:5], 1):
                result += f"{i}. {donor['name']} - {donor['distance_km']}km away (📞 {donor['phone']})\n"
        else:
            result = f"❌ No {blood_type} donors found within {radius_km}km of the location."
        
        return [types.TextContent(type="text", text=result)]
    
    elif name == "emergency_blood_request":
        if not arguments:
            raise ValueError("Missing arguments for emergency_blood_request")
        
        request = {
            "patient_name": arguments["patient_name"],
            "blood_type": arguments["blood_type"],
            "hospital_name": arguments["hospital_name"],
            "latitude": arguments["latitude"],
            "longitude": arguments["longitude"],
            "urgency": arguments.get("urgency", "high")
        }
        requests.append(request)
        
        # Find nearby donors automatically
        request_location = (request["latitude"], request["longitude"])
        compatible_donors = []
        
        for donor in donors:
            if donor["blood_type"] == request["blood_type"]:
                donor_location = (donor["latitude"], donor["longitude"])
                distance = geodesic(request_location, donor_location).kilometers
                
                if distance <= 15:  # Extended radius for emergencies
                    donor_copy = donor.copy()
                    donor_copy['distance_km'] = round(distance, 2)
                    compatible_donors.append(donor_copy)
        
        compatible_donors.sort(key=lambda x: x['distance_km'])
        
        result = f"🚨 EMERGENCY: {request['urgency'].upper()} blood request created for {request['patient_name']} at {request['hospital_name']} in India\n"
        result += f"Required: {request['blood_type']} blood\n"
        result += f"Request ID: {len(requests)}\n\n"
        
        if compatible_donors:
            result += f"📍 Found {len(compatible_donors)} nearby donors:\n"
            for i, donor in enumerate(compatible_donors[:3], 1):
                result += f"{i}. {donor['name']} - {donor['distance_km']}km (📞 {donor['phone']})\n"
        else:
            result += "❌ No nearby donors found. Expanding search to blood banks...\n"
        
        return [types.TextContent(type="text", text=result)]
    
    elif name == "india_hospitals":
        city_filter = arguments.get("city", "all").lower() if arguments else "all"
        
        hospitals = {
            "mumbai": [
                {"name": "Tata Memorial Hospital", "emergency": "022-2417-7000", "blood_bank": "022-2417-7100"},
                {"name": "Lilavati Hospital", "emergency": "022-2640-5000", "blood_bank": "022-2640-5100"},
                {"name": "KEM Hospital", "emergency": "022-2413-6051", "blood_bank": "022-2413-6052"}
            ],
            "delhi": [
                {"name": "AIIMS Delhi", "emergency": "011-2658-8500", "blood_bank": "011-2658-8700"},
                {"name": "Apollo Hospital Delhi", "emergency": "011-2692-5858", "blood_bank": "011-2692-5900"},
                {"name": "Max Super Speciality", "emergency": "011-2651-5050", "blood_bank": "011-2651-5100"}
            ],
            "bangalore": [
                {"name": "Manipal Hospital", "emergency": "080-2502-4444", "blood_bank": "080-2502-4500"},
                {"name": "Apollo Hospital Bangalore", "emergency": "080-2630-0100", "blood_bank": "080-2630-0200"},
                {"name": "Narayana Health City", "emergency": "080-7122-4444", "blood_bank": "080-7122-4500"}
            ],
            "chennai": [
                {"name": "Apollo Hospital Chennai", "emergency": "044-2829-3333", "blood_bank": "044-2829-4444"},
                {"name": "Fortis Malar", "emergency": "044-4289-4289", "blood_bank": "044-4289-4200"},
                {"name": "MIOT Hospital", "emergency": "044-4200-4200", "blood_bank": "044-4200-4300"}
            ],
            "kolkata": [
                {"name": "Apollo Gleneagles", "emergency": "033-2320-3040", "blood_bank": "033-2320-3100"},
                {"name": "AMRI Hospital", "emergency": "033-6606-3800", "blood_bank": "033-6606-3900"},
                {"name": "Fortis Hospital Kolkata", "emergency": "033-6628-4444", "blood_bank": "033-6628-4500"}
            ],
            "hyderabad": [
                {"name": "Apollo Hospital Hyderabad", "emergency": "040-2355-1020", "blood_bank": "040-2355-1100"},
                {"name": "CARE Hospital", "emergency": "040-6165-6565", "blood_bank": "040-6165-6600"},
                {"name": "Continental Hospital", "emergency": "040-6734-6734", "blood_bank": "040-6734-6800"}
            ],
            "pune": [
                {"name": "Ruby Hall Clinic", "emergency": "020-2611-2211", "blood_bank": "020-2611-2300"},
                {"name": "Sahyadri Hospital", "emergency": "020-2426-6666", "blood_bank": "020-2426-6700"},
                {"name": "KEM Hospital Pune", "emergency": "020-2612-1071", "blood_bank": "020-2612-1100"}
            ]
        }
        
        if city_filter == "all":
            result = "🏥 Major Hospitals Across India with Blood Banks:\n\n"
            for city_name, city_hospitals in hospitals.items():
                result += f"📍 {city_name.upper()}:\n"
                for i, hospital in enumerate(city_hospitals, 1):
                    result += f"{i}. {hospital['name']}\n"
                    result += f"   Emergency: {hospital['emergency']}\n"
                    result += f"   Blood Bank: {hospital['blood_bank']}\n\n"
        else:
            city_hospitals = hospitals.get(city_filter, [])
            if city_hospitals:
                result = f"🏥 Major Hospitals in {city_filter.title()}:\n\n"
                for i, hospital in enumerate(city_hospitals, 1):
                    result += f"{i}. {hospital['name']}\n"
                    result += f"   Emergency: {hospital['emergency']}\n"
                    result += f"   Blood Bank: {hospital['blood_bank']}\n\n"
            else:
                result = f"❌ No hospital data found for {city_filter}. Available cities: Mumbai, Delhi, Bangalore, Chennai, Kolkata, Hyderabad, Pune"
        
        return [types.TextContent(type="text", text=result)]
    
    elif name == "list_donors":
        if not donors:
            result = "📋 No donors registered yet. Use register_blood_donor to add donors."
        else:
            result = f"🩸 Registered Blood Donors in India ({len(donors)} total):\n\n"
            for i, donor in enumerate(donors, 1):
                result += f"{i}. {donor['name']} - {donor['blood_type']}\n"
                result += f"   Location: ({donor['latitude']}, {donor['longitude']})\n"
                result += f"   Phone: {donor['phone']}\n\n"
        
        return [types.TextContent(type="text", text=result)]
    
    else:
        raise ValueError(f"Unknown tool: {name}")

async def main():
    print("=== Blood Donor Connect MCP Server for India ===")
    print("Platform: Official MCP SDK")
    print(f"Validation Phone: {MY_NUMBER}")
    print("Coverage: Pan-India Blood Donor Network")
    print("=" * 50)
    
    import os
    port = int(os.environ.get("PORT", 8080))
    host = os.environ.get("HOST", "0.0.0.0")
    
    # Run the server using stdio transport
    async with mcp.server.stdio.stdio_server() as (read_stream, write_stream):
        await server.run(
            read_stream,
            write_stream,
            InitializationOptions(
                server_name="blood-donor-india",
                server_version="1.0.0",
                capabilities=server.get_capabilities(
                    notification_options=NotificationOptions(),
                    experimental_capabilities={},
                ),
            ),
        )

if __name__ == "__main__":
    asyncio.run(main())
