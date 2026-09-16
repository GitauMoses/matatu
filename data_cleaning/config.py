import os
from pathlib import Path

# Paths
BASE_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = BASE_DIR.parent
EXCEL_PATH = Path("/home/gitau/Downloads/Registered NMA PTOS and their Routes of Operation .xlsx")
OUTPUT_DIR = BASE_DIR / "output"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

APP_ROUTES_CSV = PROJECT_ROOT / "backend" / "data" / "network" / "routes.csv"
APP_STAGES_CSV = PROJECT_ROOT / "backend" / "data" / "network" / "stages.csv"
APP_PATHS_CSV = PROJECT_ROOT / "backend" / "data" / "network" / "paths.csv"
APP_TERMINALS_CSV = PROJECT_ROOT / "backend" / "data" / "corrections" / "terminals.csv"
APP_RESEARCH_CSV = PROJECT_ROOT / "backend" / "data" / "research" / "all_routes_saccos.csv"

# Canonical CBD Terminals
CBD_TERMINALS = {
    "odeon": ["odeon", "odeon terminus", "latema", "tom mboya", "tommboya"],
    "koja": ["koja", "khoja", "nation centre", "ngara flyover"],
    "railways": ["railways", "railway", "railways bus terminus", "haile selassie"],
    "kencom": ["kencom", "ambassadeur", "ambasadeur", "moi avenue", "gpo", "teleposta"],
    "bus station": ["bus station", "busstation", "bs", "machakos country bus"],
    "otc": ["otc", "ladhes road", "tuskys ronald ngala", "ronald ngala", "ronald ngara"],
    "muthurwa": ["muthurwa", "landhies"],
    "commercial": ["commercial", "accra", "accra rd", "tea room"],
    "gikomba": ["gikomba", "kariokor"],
    "knh": ["knh", "kenyatta national hospital"],
    "fig tree": ["fig tree", "figtree", "ngara"],
}

# Known Major Nairobi Corridors
CORRIDORS = {
    "thika_road": ["thika rd", "thika road", "roysambu", "kasarani", "ruiru", "juja", "thika", "kahawa", "allsops", "alsops", "baba dogo", "ngumba", "garden estate"],
    "waiyaki_way": ["waiyaki way", "waiyakiway", "westlands", "kangemi", "uthiru", "kinoo", "regen", "kikuyu", "zambezi", "limuru", "wangige"],
    "ngong_road": ["ngong road", "ngong rd", "adams", "adams arcade", "junction", "karen", "dagoretti", "kawangware", "ngong", "kiserian", "lenana"],
    "jogoo_road": ["jogoo road", "jogoo rd", "buruburu", "donholm", "outering", "outering rd", "umoja", "jericho", "makadara", "hamza", "city stadium"],
    "mombasa_road": ["mombasa road", "mombasa rd", "nyayo stadium", "cabanas", "city cabanas", "syokimau", "mlolongo", "kitengela", "athi river", "imara daima"],
    "langata_road": ["langata road", "langata rd", "wilson", "t-mall", "tmall", "highrise", "dam estate", "bomas", "ongata rongai", "rongai", "kiserian"],
    "kangundo_road": ["kangundo road", "kangundo rd", "kayole", "dandora", "saika", "komarock", "ruai", "kamulu", "joska", "malaa", "tala"],
    "kiambu_road": ["kiambu road", "kiambu rd", "muthaiga", "ridgeways", "fourways", "thindigua", "kiambu", "ndumberi", "githunguri"],
    "limuru_road": ["limuru road", "limuru rd", "parklands", "city park", "muthaiga", "gigiri", "un", "ruaka", "banana", "ndenderu", "mucatha", "karura"],
    "juja_road": ["juja road", "juja rd", "eastleigh", "mlango kubwa", "mathare", "huruma", "kariobangi"],
}

# Words to ignore when matching metropolitan commuter routes (intercity/upcountry)
INTERCITY_INDICATORS = [
    "mombasa", "kisumu", "nakuru", "eldoret", "nyeri", "embu", "meru", "kitui", 
    "mwingi", "machakos", "namanga", "taveta", "naivasha", "narok", "kakamega",
    "kisii", "homabay", "migori", "busia", "malindi", "garissa", "voi", "bungoma"
]
