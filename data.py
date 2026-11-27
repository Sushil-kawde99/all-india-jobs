INDIAN_LOCATIONS = [
    # 28 States
    {"name": "Andhra Pradesh", "code": "AP", "is_ut": False, "cities": ["Visakhapatnam", "Vijayawada", "Guntur", "Tirupati", "Kakinada", "Nellore"]},
    {"name": "Arunachal Pradesh", "code": "AR", "is_ut": False, "cities": ["Itanagar", "Naharlagun", "Pasighat", "Tawang"]},
    {"name": "Assam", "code": "AS", "is_ut": False, "cities": ["Guwahati", "Silchar", "Dibrugarh", "Jorhat", "Nagaon", "Tezpur"]},
    {"name": "Bihar", "code": "BR", "is_ut": False, "cities": ["Patna", "Gaya", "Bhagalpur", "Muzaffarpur", "Darbhanga", "Purnia"]},
    {"name": "Chhattisgarh", "code": "CG", "is_ut": False, "cities": ["Raipur", "Bhilai", "Bilaspur", "Korba", "Durg"]},
    {"name": "Goa", "code": "GA", "is_ut": False, "cities": ["Panaji", "Margao", "Vasco da Gama", "Mapusa"]},
    {"name": "Gujarat", "code": "GJ", "is_ut": False, "cities": ["Ahmedabad", "Surat", "Vadodara", "Rajkot", "Bhavnagar", "Gandhinagar"]},
    {"name": "Haryana", "code": "HR", "is_ut": False, "cities": ["Gurugram", "Faridabad", "Panipat", "Ambala", "Rohtak", "Hisar", "Panchkula"]},
    {"name": "Himachal Pradesh", "code": "HP", "is_ut": False, "cities": ["Shimla", "Dharamshala", "Mandi", "Solan", "Baddi"]},
    {"name": "Jharkhand", "code": "JH", "is_ut": False, "cities": ["Ranchi", "Jamshedpur", "Dhanbad", "Bokaro Steel City", "Deoghar"]},
    {"name": "Karnataka", "code": "KA", "is_ut": False, "cities": ["Bengaluru", "Mysuru", "Hubballi", "Mangaluru", "Belagavi", "Shivamogga"]},
    {"name": "Kerala", "code": "KL", "is_ut": False, "cities": ["Thiruvananthapuram", "Kochi", "Kozhikode", "Thrissur", "Kollam", "Kannur"]},
    {"name": "Madhya Pradesh", "code": "MP", "is_ut": False, "cities": ["Bhopal", "Indore", "Jabalpur", "Gwalior", "Ujjain", "Sagar"]},
    {"name": "Maharashtra", "code": "MH", "is_ut": False, "cities": ["Mumbai", "Pune", "Nagpur", "Thane", "Nashik", "Chhatrapati Sambhajinagar", "Navi Mumbai"]},
    {"name": "Manipur", "code": "MN", "is_ut": False, "cities": ["Imphal", "Churachandpur", "Thoubal"]},
    {"name": "Meghalaya", "code": "ML", "is_ut": False, "cities": ["Shillong", "Tura", "Jowai"]},
    {"name": "Mizoram", "code": "MZ", "is_ut": False, "cities": ["Aizawl", "Lunglei", "Champhai"]},
    {"name": "Nagaland", "code": "NL", "is_ut": False, "cities": ["Kohima", "Dimapur", "Mokokchung"]},
    {"name": "Odisha", "code": "OD", "is_ut": False, "cities": ["Bhubaneswar", "Cuttack", "Rourkela", "Berhampur", "Sambalpur", "Puri"]},
    {"name": "Punjab", "code": "PB", "is_ut": False, "cities": ["Ludhiana", "Amritsar", "Jalandhar", "Patiala", "Bathinda", "Mohali"]},
    {"name": "Rajasthan", "code": "RJ", "is_ut": False, "cities": ["Jaipur", "Jodhpur", "Kota", "Bikaner", "Ajmer", "Udaipur"]},
    {"name": "Sikkim", "code": "SK", "is_ut": False, "cities": ["Gangtok", "Namchi", "Geyzing"]},
    {"name": "Tamil Nadu", "code": "TN", "is_ut": False, "cities": ["Chennai", "Coimbatore", "Madurai", "Tiruchirappalli", "Salem", "Tirunelveli"]},
    {"name": "Telangana", "code": "TS", "is_ut": False, "cities": ["Hyderabad", "Warangal", "Nizamabad", "Karimnagar", "Khammam"]},
    {"name": "Tripura", "code": "TR", "is_ut": False, "cities": ["Agartala", "Udaipur", "Dharmanagar"]},
    {"name": "Uttar Pradesh", "code": "UP", "is_ut": False, "cities": ["Noida", "Greater Noida", "Lucknow", "Kanpur", "Ghaziabad", "Agra", "Varanasi", "Prayagraj"]},
    {"name": "Uttarakhand", "code": "UK", "is_ut": False, "cities": ["Dehradun", "Haridwar", "Roorkee", "Haldwani", "Rishikesh"]},
    {"name": "West Bengal", "code": "WB", "is_ut": False, "cities": ["Kolkata", "Howrah", "Durgapur", "Asansol", "Siliguri", "Kharagpur"]},

    # 8 Union Territories
    {"name": "Andaman and Nicobar Islands", "code": "AN", "is_ut": True, "cities": ["Port Blair"]},
    {"name": "Chandigarh", "code": "CH", "is_ut": True, "cities": ["Chandigarh"]},
    {"name": "Dadra and Nagar Haveli and Daman and Diu", "code": "DH", "is_ut": True, "cities": ["Daman", "Silvassa"]},
    {"name": "Delhi", "code": "DL", "is_ut": True, "cities": ["New Delhi", "North Delhi", "South Delhi", "East Delhi", "Dwarka"]},
    {"name": "Jammu and Kashmir", "code": "JK", "is_ut": True, "cities": ["Srinagar", "Jammu", "Anantnag"]},
    {"name": "Ladakh", "code": "LA", "is_ut": True, "cities": ["Leh", "Kargil"]},
    {"name": "Lakshadweep", "code": "LD", "is_ut": True, "cities": ["Kavaratti"]},
    {"name": "Puducherry", "code": "PY", "is_ut": True, "cities": ["Puducherry", "Karaikal"]},
]

ALL_STATES = [loc["name"] for loc in INDIAN_LOCATIONS]

JOB_CATEGORIES = [
    {"name": "IT / Software", "icon": "code", "desc": "Software engineering, QA, DevOps, and cloud roles", "type": "it"},
    {"name": "Frontend Development", "icon": "layout", "desc": "React, Vue, Tailwind, UI engineering", "type": "it"},
    {"name": "Backend Development", "icon": "server", "desc": "Python, FastAPI, Django, Java, REST APIs", "type": "it"},
    {"name": "Full Stack Development", "icon": "layers", "desc": "End-to-end web and mobile applications", "type": "it"},
    {"name": "Data Entry", "icon": "file-spreadsheet", "desc": "Data processing, typing, transcription jobs", "type": "non-it"},
    {"name": "Back Office", "icon": "folder-kanban", "desc": "Administrative support, documentation & operations", "type": "non-it"},
    {"name": "Manufacturing", "icon": "factory", "desc": "Industrial plants, assembly line, machinery", "type": "non-it"},
    {"name": "Automobile", "icon": "car", "desc": "Automotive assembly, design, EV & maintenance", "type": "non-it"},
    {"name": "Production", "icon": "cog", "desc": "Shop floor, production line & quality metrics", "type": "non-it"},
    {"name": "Quality", "icon": "check-circle", "desc": "QA/QC inspectors, audits, ISO adherence", "type": "non-it"},
    {"name": "Logistics", "icon": "truck", "desc": "Supply chain, freight, dispatch & shipping", "type": "non-it"},
    {"name": "Dispatch", "icon": "send", "desc": "Goods packaging, tracking and fulfillment", "type": "non-it"},
    {"name": "Store / Warehouse", "icon": "package", "desc": "Inventory management, depot & stock keeping", "type": "non-it"},
    {"name": "Banking", "icon": "landmark", "desc": "Commercial banks, loan processing, branch staff", "type": "non-it"},
    {"name": "Finance", "icon": "badge-percent", "desc": "Accounting, auditing, GST, tax & wealth management", "type": "non-it"},
    {"name": "Healthcare", "icon": "heart-pulse", "desc": "Hospitals, medical labs, pharma & nursing", "type": "non-it"},
    {"name": "Teaching", "icon": "graduation-cap", "desc": "Schools, colleges, coaching and tutoring", "type": "non-it"},
    {"name": "Government Jobs", "icon": "building", "desc": "Central & State government official vacancies", "type": "govt"},
    {"name": "Railway Jobs", "icon": "train", "desc": "RRB, RRC, Loco Pilot, Station Staff, Technical", "type": "govt"},
    {"name": "PSU Jobs", "icon": "briefcase", "desc": "ONGC, BHEL, NTPC, IOCL, ISRO & public undertakings", "type": "govt"},
    {"name": "Apprenticeships", "icon": "wrench", "desc": "NATS, NAPS apprentice practical factory training", "type": "non-it"},
    {"name": "Internships", "icon": "sparkles", "desc": "College student & fresher career internships", "type": "it"},
    {"name": "Remote Jobs", "icon": "globe", "desc": "Work from home positions accessible pan-India", "type": "it"},
]

QUALIFICATIONS = [
    "10th Pass",
    "12th Pass",
    "ITI",
    "Diploma",
    "Any Graduate",
    "B.E. / B.Tech",
    "B.Sc / BCA",
    "B.Com / BBA",
    "Post Graduate / M.Tech / MBA / MCA",
    "Ph.D / Doctorate",
]

EXPERIENCE_LEVELS = [
    "Fresher (0 years)",
    "0-1 Year",
    "1-3 Years",
    "3-5 Years",
    "5-8 Years",
    "8+ Years",
]

EMPLOYMENT_TYPES = [
    "Full Time",
    "Part Time",
    "Contract",
    "Internship",
    "Apprenticeship",
    "Government",
]

