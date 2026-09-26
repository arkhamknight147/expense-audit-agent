"""Static reference data for the synthetic golden set.

Everything here is fictional: company, employees, vendors and GSTINs.
Vendor names are generic and deliberately avoid real brands. GSTINs follow the
public 15-character format but are fictitious (PAN part starts with "ZZ" and the
checksum character is not computed). Every rendered receipt is watermarked
"SYNTHETIC SAMPLE - NOT A VALID INVOICE" (ADR G3).
"""

COMPANY_NAME = "Acme India Pvt Ltd"
COMPANY_GSTIN = "29ZZAXA2026M1ZG"  # fictitious, checksum-valid, Karnataka (29) (ADR-016)

# PAN 4th character = holder type in real PANs. Fictitious GSTINs never use these,
# so they cannot collide with a real business.
REAL_PAN_ENTITY_CODES = set("ABCEFGHJKLPT")
FAKE_PAN_ENTITY_CODES = "QRUVWXYZ"

# GST state codes (first two digits of a GSTIN) for the cities used.
STATE_CODES = {
    "Jammu & Kashmir": "01", "Himachal Pradesh": "02", "Punjab": "03", "Chandigarh": "04",
    "Uttarakhand": "05", "Haryana": "06", "Delhi": "07", "Rajasthan": "08", "Uttar Pradesh": "09",
    "West Bengal": "19", "Odisha": "21", "Madhya Pradesh": "23", "Gujarat": "24",
    "Maharashtra": "27", "Karnataka": "29", "Kerala": "32", "Tamil Nadu": "33",
    "Telangana": "36", "Andhra Pradesh": "37",
}

# Destination cities used in the synthetic data, with their state.
CITIES = {
    # X
    "Ahmedabad": "Gujarat", "Bengaluru": "Karnataka", "Chennai": "Tamil Nadu", "Delhi": "Delhi",
    "Hyderabad": "Telangana", "Kolkata": "West Bengal", "Mumbai": "Maharashtra", "Pune": "Maharashtra",
    # Y
    "Jaipur": "Rajasthan", "Lucknow": "Uttar Pradesh", "Kochi": "Kerala", "Indore": "Madhya Pradesh",
    "Nagpur": "Maharashtra", "Coimbatore": "Tamil Nadu", "Chandigarh": "Chandigarh",
    "Bhubaneswar": "Odisha", "Surat": "Gujarat", "Vadodara": "Gujarat",
    # Z (not in the X or Y lists)
    "Hosur": "Tamil Nadu", "Udupi": "Karnataka", "Shimla": "Himachal Pradesh",
    "Haridwar": "Uttarakhand", "Alibaug": "Maharashtra", "Tirupati": "Andhra Pradesh",
}

# Cities without a commercial airport (flights are never booked to these).
NO_AIRPORT = {"Hosur", "Udupi", "Haridwar", "Alibaug"}

BASE_CITIES = ["Bengaluru", "Pune", "Hyderabad", "Delhi", "Mumbai", "Chennai"]

FIRST_NAMES = [
    "Aarav", "Ananya", "Rohan", "Priya", "Vikram", "Sneha", "Arjun", "Kavya", "Rahul", "Meera",
    "Siddharth", "Nisha", "Karthik", "Pooja", "Aditya", "Divya", "Manish", "Shruti", "Varun", "Isha",
    "Nikhil", "Lakshmi", "Harsh", "Neha", "Sameer", "Aishwarya", "Deepak", "Ritu", "Gaurav", "Swati",
    "Imran", "Fatima", "Joseph", "Mary", "Gurpreet", "Harleen", "Tenzin", "Anjali", "Suresh", "Farhan",
]
LAST_NAMES = [
    "Sharma", "Iyer", "Patel", "Reddy", "Nair", "Kulkarni", "Deshpande", "Menon", "Rao", "Gupta",
    "Singh", "Das", "Mehta", "Joshi", "Pillai", "Banerjee", "Khan", "Fernandes", "Chauhan", "Bhat",
]

HOTEL_NAMES = ["Sai Residency", "Green Leaf Inn", "Silver Oak Comforts", "Palm Grove Suites",
               "Sunrise Business Hotel", "Blue Bay Residency", "Lotus Petal Inn", "Metro Stay Grand"]
RESTAURANT_NAMES = ["Annapurna Bhojanalaya", "Spice Trail Kitchen", "Udupi Sagar Veg",
                    "Tandoor Junction", "Coastal Curry House", "Masala Mile Cafe", "Biryani Bazaar",
                    "The Filter Coffee Co"]
CAB_NAMES = ["CityRide Cabs", "QuickWheels Taxi", "MetroGo Rides"]
AIRLINE_NAMES = ["Kestrel Air", "Monsoon Airways"]
LAUNDRY_NAMES = ["Sparkle Laundry Services", "Fresh Fold Dry Cleaners"]
TELECOM_NAMES = ["NetLink Mobile", "SignalPlus Telecom"]

AREAS = ["MG Road", "Station Road", "Ring Road", "Civil Lines", "Park Street", "Airport Road",
         "Market Yard", "Beach Road", "Nehru Nagar", "Gandhi Chowk"]

PURPOSES = [
    "Client workshop for the Q4 rollout", "Quarterly business review with client",
    "Vendor site inspection", "Implementation go-live support", "Sales meeting with prospect",
    "Internal leadership offsite", "Training delivery for client team", "Audit fieldwork",
]

CLIENT_ORGS = ["Northwind Retail", "Bluefin Logistics", "Orchid Pharma", "Vertex Motors",
               "Kaveri Textiles", "Himgiri Foods"]

VEG_ITEMS = [("Veg Thali", 220, 380), ("Paneer Butter Masala", 260, 360), ("Masala Dosa", 90, 160),
             ("Dal Tadka", 180, 260), ("Butter Naan", 45, 80), ("Jeera Rice", 150, 220),
             ("Idli Vada", 70, 120), ("Filter Coffee", 40, 90), ("Fresh Lime Soda", 80, 140)]
NONVEG_ITEMS = [("Chicken Biryani", 280, 420), ("Fish Curry Meal", 300, 480),
                ("Mutton Rogan Josh", 380, 560), ("Chicken Tikka", 320, 460)]
ALCOHOL_ITEMS = [("Draught Beer 500ml", 280, 420), ("House Red Wine (glass)", 450, 700),
                 ("Single Malt 60ml", 650, 1100)]
