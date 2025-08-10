# Enhanced Blood Donor Connect India - Hospital Selection Based MCP Server
# Complete corrected version with all improvements

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
    
    if city:
        # Search within specific city first
        city_hospitals = HOSPITALS.get(city.lower(), [])
        for hospital in city_hospitals:
            if hospital_name.lower() in hospital["name"].lower():
                matches.append((hospital, city.lower()))
    
    # If no matches in specified city, search all cities
    if not matches:
        for city_name, hospitals in HOSPITALS.items():
            for hospital in hospitals:
                if hospital_name.lower() in hospital["name"].lower():
                    matches.append((hospital, city_name))
    
    if not matches:
        return None, None
    elif len(matches) == 1:
        return matches[0]
    else:
        # Multiple matches - need disambiguation
        return "multiple", matches

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
            name="help",
            description="Show all available blood donor tools and how to use them",
            inputSchema={
                "type": "object",
                "properties": {
                    "tool_name": {"type": "string", "description": "Optional: Get detailed help for a specific tool"}
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
    """Handle tool calls for blood donor operations with hospital selection."""
    
    try:
        if name == "validate":
            return [types.TextContent(type="text", text=MY_NUMBER)]
        
        elif name == "help":
            tool_name = arguments.get("tool_name") if arguments else None
            
            if tool_name:
                help_content = {
                    "register_blood_donor": """🩸 REGISTER BLOOD DONOR HELP

Usage: Provide all required information:
• name: Your full name
• blood_type: O+, A+, B+, AB+, O-, A-, B-, AB-
• city: Choose from: mumbai, delhi, bangalore, chennai, kolkata, hyderabad, pune
• hospital_name: Name of your nearest hospital (partial name OK)
• phone: Your contact number

Example: "Register donor Arjun Kumar O+ Mumbai Apollo Hospital 9876543210"
""",
                    "find_nearby_donors": """🔍 FIND NEARBY DONORS HELP

Usage: Search for blood donors near a hospital:
• blood_type: Required blood type (O+, A+, B+, AB+, O-, A-, B-, AB-)
• city: City to search in
• hospital_name: Reference hospital for location
• radius_km: Search radius (default: 10km)

Example: "Find O+ donors near Apollo Hospital in Mumbai within 15km"
""",
                    "emergency_blood_request": """🚨 EMERGENCY BLOOD REQUEST HELP

Usage: Create urgent blood donation request:
• patient_name: Name of patient needing blood
• blood_type: Required blood type
• city: City where hospital is located
• hospital_name: Hospital where patient is admitted
• urgency: Urgency level (default: high)

Example: "Emergency request for John Doe O+ at Apollo Mumbai"
""",
                    "list_hospitals_by_city": """🏥 LIST HOSPITALS BY CITY HELP

Usage: View hospitals in specific city or all cities:
• city: City name (optional - shows all if not specified)

Examples:
• "List hospitals in Mumbai"
• "List all hospitals" (shows all cities)
""",
                    "list_donors": """📋 LIST DONORS HELP

Usage: View all registered blood donors
• No parameters needed

Shows complete list of registered donors with their details.
""",
                    "validate": """✅ VALIDATE TOOL HELP

System validation tool for PuchAI compliance.
Returns: 918910662391

Used for hackathon verification.
"""
                }
                
                if tool_name in help_content:
                    result = help_content[tool_name]
                else:
                    result = f"❌ Help not available for tool: {tool_name}\n\nUse 'help' without arguments to see all available tools."
            else:
                # General help with updated tool list
                result = """🩸 BLOOD DONOR CONNECT INDIA - AVAILABLE COMMANDS

📋 AVAILABLE TOOLS:
1. help - Show this help message or detailed help for specific tools
2. validate - System validation (returns: 918910662391)
3. register_blood_donor - Register as blood donor with hospital selection
4. find_nearby_donors - Find compatible donors near specific hospital
5. emergency_blood_request - Create urgent blood donation requests
6. list_hospitals_by_city - View hospitals by city or all cities
7. list_donors - See all registered blood donors across India

🏙️ SUPPORTED CITIES:
Mumbai, Delhi, Bangalore, Chennai, Kolkata, Hyderabad, Pune

🏥 HOSPITAL FEATURES:
• 28 major hospitals across 7 cities
• Emergency and blood bank contact numbers
• GPS coordinates for accurate matching
• Partial name matching (e.g., "Apollo" finds "Apollo Hospital")

💡 USAGE TIPS:
• Use 'help [tool_name]' for detailed help on specific tools
• City names are case-insensitive
• Hospital names support partial matching
• All tools designed for emergency blood matching across India

🚨 FOR EMERGENCIES: Use emergency_blood_request tool immediately
"""
            
            return [types.TextContent(type="text", text=result)]
        
        elif name == "register_blood_donor":
            if not arguments:
                return [types.TextContent(type="text", text="""❌ Missing registration information!

Please provide:
• Name: Your full name
• Blood Type: O+, A+, B+, AB+, O-, A-, B-, AB-
• City: mumbai, delhi, bangalore, chennai, kolkata, hyderabad, pune
• Hospital: Name of nearest hospital
• Phone: Your contact number

Example: "Register donor Arjun Kumar O+ Mumbai Apollo Hospital 9876543210"

Use 'help register_blood_donor' for more details.""")]
            
            # Check for missing required fields
            required_fields = ["name", "blood_type", "city", "hospital_name", "phone"]
            missing_fields = [field for field in required_fields if not arguments.get(field)]
            
            if missing_fields:
                cities_list = ", ".join(get_all_cities())
                result = f"❌ Missing required information: {', '.join(missing_fields)}\n\n"
                
                if "city" in missing_fields:
                    result += f"🏙️ Available cities: {cities_list}\n"
                
                if "hospital_name" in missing_fields and arguments.get("city"):
                    city_hospitals = get_hospitals_in_city(arguments["city"])
                    hospital_names = [h["name"] for h in city_hospitals]
                    result += f"🏥 Hospitals in {arguments['city'].title()}: {', '.join(hospital_names)}\n"
                
                result += "\n💡 Please provide all required information to register as a blood donor."
                return [types.TextContent(type="text", text=result)]
            
            # Validate blood type
            if not validate_blood_type(arguments.get("blood_type", "")):
                return [types.TextContent(type="text", text="❌ Invalid blood type. Please use: O+, A+, B+, AB+, O-, A-, B-, AB-")]
            
            # Validate city
            if not validate_city(arguments.get("city", "")):
                available_cities = ", ".join(get_all_cities())
                return [types.TextContent(type="text", text=f"❌ Invalid city. Available cities: {available_cities}")]
            
            city = arguments["city"].lower()
            hospital_name = arguments["hospital_name"]
            
            # Find hospital with disambiguation
            hospital_result, found_data = find_hospital_by_name(hospital_name, city)
            
            if hospital_result is None:
                available_hospitals = get_hospitals_in_city(city)
                hospital_list = ", ".join([h["name"] for h in available_hospitals])
                return [types.TextContent(type="text", text=f"❌ Hospital '{hospital_name}' not found in {city.title()}.\n\n🏥 Available hospitals: {hospital_list}\n\n💡 Try using partial names like 'Apollo' or 'Fortis'")]
            
            elif hospital_result == "multiple":
                match_list = "\n".join([f"• {h[0]['name']} in {h[1].title()}" for h in found_data])
                return [types.TextContent(type="text", text=f"❌ Multiple hospitals found for '{hospital_name}':\n\n{match_list}\n\n💡 Please be more specific with the hospital name.")]
            
            else:
                hospital, found_city = hospital_result, found_data
                
                # Ensure we use the correct city's hospital details
                if found_city != city:
                    return [types.TextContent(type="text", text=f"❌ '{hospital_name}' found in {found_city.title()}, but you selected {city.title()}.\n\nPlease either:\n• Change city to {found_city.title()}, or\n• Choose a hospital in {city.title()}")]
                
                # Create donor record
                donor = {
                    "name": arguments["name"],
                    "blood_type": arguments["blood_type"].upper(),
                    "city": city,
                    "hospital": hospital["name"],
                    "phone": arguments["phone"],
                    "latitude": hospital["lat"],
                    "longitude": hospital["lng"]
                }
                donors.append(donor)
                save_data()
                
                result = f"✅ Blood donor registered successfully!\n\n"
                result += f"👤 Name: {donor['name']}\n"
                result += f"🩸 Blood Type: {donor['blood_type']}\n"
                result += f"🏙️ City: {city.title()}\n"
                result += f"🏥 Hospital: {hospital['name']}\n"
                result += f"📞 Phone: {donor['phone']}\n"
                result += f"🆔 Donor ID: {len(donors)}\n\n"
                result += f"🚨 Emergency Contact: {hospital['emergency']}\n"
                result += f"🩸 Blood Bank: {hospital['blood_bank']}"
                
                return [types.TextContent(type="text", text=result)]
        
        elif name == "find_nearby_donors":
            if not arguments:
                return [types.TextContent(type="text", text="Missing arguments for find_nearby_donors")]
            
            blood_type = arguments["blood_type"].upper()
            city = arguments["city"].lower()
            hospital_name = arguments["hospital_name"]
            radius_km = arguments.get("radius_km", 10)
            
            # Find the hospital
            hospital, _ = find_hospital_by_name(hospital_name, city)
            if not hospital:
                return [types.TextContent(type="text", text=f"❌ Hospital '{hospital_name}' not found in {city}")]
            
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
        
        elif name == "hospital_network_status":
            result = f"🩸 Blood Donor Connect India - Network Status\n\n"
            result += f"✅ Server: Online and operational\n"
            result += f"🏥 Cities: {len(HOSPITALS)} major Indian cities\n"
            result += f"🏨 Hospitals: {sum(len(h) for h in HOSPITALS.values())} total\n"
            result += f"📱 Emergency contacts: Available for all hospitals\n\n"
            result += f"🔧 Use 'list_hospitals_by_city' with specific city for details"
            
            return [types.TextContent(type="text", text=result)]
        
        elif name == "emergency_blood_request":
            if not arguments:
                return [types.TextContent(type="text", text="Missing arguments for emergency_blood_request")]
            
            city = arguments["city"].lower()
            hospital_name = arguments["hospital_name"]
            
            # Find the hospital
            hospital, _ = find_hospital_by_name(hospital_name, city)
            if not hospital:
                return [types.TextContent(type="text", text=f"❌ Hospital '{hospital_name}' not found in {city}")]
            
            request = {
                "patient_name": arguments["patient_name"],
                "blood_type": arguments["blood_type"].upper(),
                "city": city,
                "hospital": hospital,
                "urgency": arguments.get("urgency", "high")
            }
            requests.append(request)
            save_data()
            
            # Find nearby donors automatically
            hospital_location = (hospital["lat"], hospital["lng"])
            compatible_donors = []
            
            for donor in donors:
                if donor["blood_type"] == request["blood_type"]:
                    donor_location = (donor["latitude"], donor["longitude"])
                    distance = geodesic(hospital_location, donor_location).kilometers
                    
                    if distance <= 25:  # Extended radius for emergencies
                        donor_copy = donor.copy()
                        donor_copy['distance_km'] = round(distance, 2)
                        compatible_donors.append(donor_copy)
            
            compatible_donors.sort(key=lambda x: x['distance_km'])
            
            result = f"🚨 EMERGENCY: {request['urgency'].upper()} blood request created\n"
            result += f"👤 Patient: {request['patient_name']}\n"
            result += f"🩸 Required: {request['blood_type']} blood\n"
            result += f"🏥 Hospital: {hospital['name']}, {city.title()}\n"
            result += f"📞 Emergency: {hospital['emergency']}\n"
            result += f"🩸 Blood Bank: {hospital['blood_bank']}\n"
            result += f"🆔 Request ID: {len(requests)}\n\n"
            
            if compatible_donors:
                result += f"📍 Found {len(compatible_donors)} nearby compatible donors:\n\n"
                for i, donor in enumerate(compatible_donors[:3], 1):
                    result += f"{i}. {donor['name']} - {donor['distance_km']}km away\n"
                    result += f"   📍 Near: {donor['hospital']}\n"
                    result += f"   📞 Contact: {donor['phone']}\n\n"
            else:
                result += "❌ No nearby donors found. Expanding search to blood banks...\n"
                result += f"🏥 Contact blood bank directly: {hospital['blood_bank']}"
            
            return [types.TextContent(type="text", text=result)]
        
        elif name == "list_hospitals_by_city":
            city_filter = arguments.get("city", "all").lower() if arguments else "all"
        
            if city_filter == "all":
                # Return summary instead of full list to avoid truncation
                total_hospitals = sum(len(hospitals) for hospitals in HOSPITALS.values())
                result = f"🏥 Blood Donor Connect India - Hospital Network\n\n"
                result += f"📊 Coverage: {len(HOSPITALS)} cities, {total_hospitals} hospitals\n\n"
                result += "🏙️ Available Cities:\n"
                for city_name in HOSPITALS.keys():
                    city_count = len(HOSPITALS[city_name])
                    result += f"• {city_name.title()}: {city_count} hospitals\n"
                result += f"\n💡 Use specific city name to view hospital details"
                
            else:
                city_hospitals = get_hospitals_in_city(city_filter)
                if city_hospitals:
                    # Limit to 3 hospitals max to avoid truncation
                    display_hospitals = city_hospitals[:3]
                    result = f"🏥 Top Hospitals in {city_filter.title()}:\n\n"
                    
                    for i, hospital in enumerate(display_hospitals, 1):
                        result += f"{i}. {hospital['name']}\n"
                        result += f"   🚨 Emergency: {hospital['emergency']}\n"
                        result += f"   🩸 Blood Bank: {hospital['blood_bank']}\n\n"
                    
                    if len(city_hospitals) > 3:
                        result += f"+ {len(city_hospitals)-3} more hospitals available"
                else:
                    available_cities = ", ".join(get_all_cities())
                    result = f"❌ City '{city_filter}' not found.\n🏙️ Available: {available_cities}"
        
            return [types.TextContent(type="text", text=result)]
        
        elif name == "list_donors":
            if not donors:
                result = "📋 No donors registered yet.\n\n"
                result += "💡 Use register_blood_donor to add donors:\n"
                result += "1. Choose your city from: " + ", ".join(get_all_cities()) + "\n"
                result += "2. Select your nearest hospital\n"
                result += "3. We'll handle the coordinates automatically!"
            else:
                result = f"🩸 Registered Blood Donors in India ({len(donors)} total):\n\n"
                for i, donor in enumerate(donors, 1):
                    result += f"{i}. {donor['name']} - {donor['blood_type']}\n"
                    result += f"   📍 City: {donor['city'].title()}\n"
                    result += f"   🏥 Hospital: {donor['hospital']}\n"
                    result += f"   📞 Phone: {donor['phone']}\n\n"
            
            return [types.TextContent(type="text", text=result)]
        
        else:
            return [types.TextContent(type="text", text=f"Unknown tool: {name}")]
    
    except Exception as e:
        logger.error(f"Error in tool {name}: {str(e)}", exc_info=True)
        return [types.TextContent(type="text", text=f"Error processing {name}: {str(e)}")]

# Create FastAPI app with CORS support
app = FastAPI(title="Blood Donor Connect India - Hospital Selection Based")

# Add CORS middleware for MCP client compatibility
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
    """Main endpoint showing server status"""
    return {
        "message": "🩸 Blood Donor Connect India - Hospital Selection Based",
        "status": "running",
        "platform": "Railway HTTP + MCP Deployment",
        "validation_phone": MY_NUMBER,
        "coverage": "Pan-India Blood Donor Network",
        "features": "Hospital-based location selection",
        "cities": list(HOSPITALS.keys()),
        "total_hospitals": sum(len(hospitals) for hospitals in HOSPITALS.values()),
        "mcp_endpoint": "/mcp",
        "available_tools": [
            "help - Show available commands",
            "validate - System validation", 
            "register_blood_donor - Register as donor",
            "find_nearby_donors - Find compatible donors",
            "emergency_blood_request - Create urgent requests",
            "list_hospitals_by_city - View hospitals",
            "list_donors - See registered donors"
        ],
        "help_tip": "Use 'help' tool for detailed command information",
        "stats": {
            "total_donors": len(donors),
            "total_requests": len(requests)
        }
    }

@app.get("/health")
async def health_check():
    """Health check endpoint for Railway"""
    return {
        "status": "healthy",
        "service": "blood-donor-india-mcp",
        "server_name": "blood-donor-india",
        "platform": "Railway",
        "validation_phone": MY_NUMBER,
        "total_donors": len(donors),
        "total_requests": len(requests),
        "mcp_support": True,
        "hospital_selection": True
    }

@app.get("/validate")
async def validate_endpoint():
    """PuchAI validation endpoint via HTTP"""
    return {
        "phone": MY_NUMBER,
        "status": "valid",
        "service": "blood-donor-india"
    }

@app.get("/tools")
async def list_tools_http():
    """List all MCP tools via HTTP"""
    try:
        tools = await handle_list_tools()
        return {
            "tools": [
                {
                    "name": tool.name,
                    "description": tool.description,
                    "required_params": tool.inputSchema.get("required", []) if hasattr(tool, 'inputSchema') else []
                }
                for tool in tools
            ],
            "total": len(tools),
            "server": "blood-donor-india",
            "feature": "hospital-selection-based"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error listing tools: {str(e)}")

# MCP JSON-RPC endpoint
@app.post("/mcp")
async def mcp_endpoint(request: Request):
    """Handle MCP JSON-RPC requests with comprehensive error handling"""
    try:
        logger.info("Received MCP request")
        payload = await request.json()
        logger.info(f"MCP method: {payload.get('method', 'unknown')}")
        
        if not payload.get("jsonrpc") == "2.0":
            logger.error("Invalid JSON-RPC version")
            return JSONResponse({
                "jsonrpc": "2.0",
                "id": payload.get("id"),
                "error": {"code": -32600, "message": "Invalid Request - missing jsonrpc 2.0"}
            }, status_code=400)
        
        method = payload.get("method")
        if not method:
            logger.error("Missing method in JSON-RPC request")
            return JSONResponse({
                "jsonrpc": "2.0",
                "id": payload.get("id"),
                "error": {"code": -32600, "message": "Invalid Request - missing method"}
            }, status_code=400)
        
        if method == "initialize":
            logger.info("Processing initialize request")
            return JSONResponse({
                "jsonrpc": "2.0",
                "id": payload.get("id"),
                "result": {
                    "protocolVersion": "2024-11-05",
                    "capabilities": {
                        "experimental": {},
                        "tools": {"listChanged": False}
                    },
                    "serverInfo": {
                        "name": "blood-donor-india",
                        "version": "1.0.0"
                    }
                }
            })
        
        elif method == "notifications/initialized":
            logger.info("Processing initialized notification")
            return JSONResponse({"status": "acknowledged"})
        
        elif method == "tools/list":
            logger.info("Processing tools/list request")
            try:
                tools = await handle_list_tools()
                return JSONResponse({
                    "jsonrpc": "2.0", 
                    "id": payload.get("id"),
                    "result": {
                        "tools": [
                            {
                                "name": tool.name, 
                                "description": tool.description, 
                                "inputSchema": tool.inputSchema
                            } 
                            for tool in tools
                        ]
                    }
                })
            except Exception as e:
                logger.error(f"Error in tools/list: {str(e)}", exc_info=True)
                return JSONResponse({
                    "jsonrpc": "2.0",
                    "id": payload.get("id"),
                    "error": {"code": -32603, "message": f"Internal error in tools/list: {str(e)}"}
                }, status_code=500)
        
        elif method == "tools/call":
            logger.info("Processing tools/call request")
            try:
                params = payload.get("params", {})
                tool_name = params.get("name")
                arguments = params.get("arguments", {})
                
                if not tool_name:
                    return JSONResponse({
                        "jsonrpc": "2.0",
                        "id": payload.get("id"),
                        "error": {"code": -32602, "message": "Missing tool name"}
                    }, status_code=400)
                
                logger.info(f"Calling tool: {tool_name} with args: {arguments}")
                result = await handle_call_tool(tool_name, arguments)
                
                return JSONResponse({
                    "jsonrpc": "2.0",
                    "id": payload.get("id"), 
                    "result": {
                        "content": [
                            {
                                "type": "text", 
                                "text": result[0].text if result else "No result"
                            }
                        ]
                    }
                })
            except Exception as e:
                logger.error(f"Error in tools/call for {tool_name}: {str(e)}", exc_info=True)
                return JSONResponse({
                    "jsonrpc": "2.0",
                    "id": payload.get("id"),
                    "error": {"code": -32603, "message": f"Tool execution error: {str(e)}"}
                }, status_code=500)
        
        else:
            logger.warning(f"Unknown method: {method}")
            return JSONResponse({
                "jsonrpc": "2.0",
                "id": payload.get("id"),
                "error": {"code": -32601, "message": f"Method not found: {method}"}
            }, status_code=404)
    
    except Exception as e:
        logger.error(f"Unexpected error in MCP endpoint: {str(e)}", exc_info=True)
        return JSONResponse({
            "jsonrpc": "2.0", 
            "id": payload.get("id", None) if 'payload' in locals() else None,
            "error": {
                "code": -32603, 
                "message": "Internal server error",
                "data": str(e) if not os.environ.get("RAILWAY_ENVIRONMENT") else "Server error"
            }
        }, status_code=500)

@app.options("/mcp")
async def mcp_options():
    """Handle CORS preflight for MCP endpoint"""
    return {"status": "ok"}

async def main():
    print("=== Blood Donor Connect MCP Server for India ===")
    print("Platform: Railway HTTP + MCP Deployment")
    print("Feature: Hospital Selection Based Location")
    print(f"Validation Phone: {MY_NUMBER}")
    print("Coverage: Pan-India Blood Donor Network")
    print(f"Cities: {', '.join(get_all_cities())}")
    print(f"Total Hospitals: {sum(len(hospitals) for hospitals in HOSPITALS.values())}")
    
    # Load existing data on startup
    load_data()
    
    port = int(os.environ.get("PORT", 8080))
    host = "0.0.0.0"
    
    print(f"🌐 Starting HTTP server on {host}:{port}")
    print("🩸 Hospital-based blood donor tools ready")
    print("📡 MCP endpoint available at /mcp")
    print("=" * 50)
    
    config = uvicorn.Config(
        app, 
        host=host, 
        port=port, 
        log_level="info"
    )
    server_instance = uvicorn.Server(config)
    await server_instance.serve()

if __name__ == "__main__":
    asyncio.run(main())
