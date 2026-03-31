import os
from pathlib import Path
from dotenv import load_dotenv

# Load .env from project root
PROJECT_ROOT = Path(__file__).resolve().parent.parent
load_dotenv(PROJECT_ROOT / ".env")

# Database
DB_HOST = os.getenv("DB_HOST", "localhost")
DB_PORT = os.getenv("DB_PORT", "5432")
DB_NAME = os.getenv("DB_NAME", "exam_papers")
DB_USER = os.getenv("DB_USER", "postgres")
DB_PASSWORD = os.getenv("DB_PASSWORD", "postgres")

DATABASE_URL = f"postgresql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"

# Paths
DATA_DIR = PROJECT_ROOT / "data"
RAW_PDF_DIR = DATA_DIR / "raw_pdfs"
EXTRACTED_TEXT_DIR = DATA_DIR / "extracted_text"
CLEANED_JSON_DIR = DATA_DIR / "cleaned_json"

# Ensure output dirs exist
EXTRACTED_TEXT_DIR.mkdir(parents=True, exist_ok=True)
CLEANED_JSON_DIR.mkdir(parents=True, exist_ok=True)

# Branch mapping: subject code prefix -> (branch short name, program full name)
BRANCH_MAP = {
    "AMC": ("MBA", "MBA"),
    "BAI": ("AI&ML", "B.Tech AI&ML"),
    "BAM": ("AI&ML", "B.Tech AI&ML"),
    "BAP": ("ARCH", "B.Arch"),
    "BAS": ("COMMON", "B.Tech Common"),
    "BCS": ("CSE", "B.Tech CSE"),
    "BEC": ("ECE", "B.Tech ECE"),
    "BIT": ("IT", "B.Tech IT"),
    "BMA": ("MAE", "B.Tech MAE"),
    "BMS": ("BMS", "BBA/BMS"),
    "GEC": ("COMMON", "General Elective"),
    "HMC": ("COMMON", "Humanities Common"),
    "MAI": ("AI&ML", "M.Tech AI"),
    "MAS": ("AI&ML", "M.Tech AI"),
    "MCA": ("MCA", "MCA"),
    "MCS": ("CSE", "M.Tech CSE"),
    "MIS": ("INFOSEC", "M.Tech InfoSec"),
    "MMS": ("MBA", "MBA"),
    "MUP": ("PLANNING", "M.Plan"),
    "MVD": ("VLSI", "M.Tech VLSI"),
    "PHD": ("PHD", "PhD"),
    "ROC": ("COMMON", "Research Common"),
}


def get_branch(subject_code):
    """Derive branch from subject code prefix."""
    if not subject_code:
        return None
    prefix = subject_code[:3].upper()
    entry = BRANCH_MAP.get(prefix)
    return entry[0] if entry else None
