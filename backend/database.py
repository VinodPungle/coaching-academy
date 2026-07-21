# Single shared MongoDB connection for the whole app.
# Every router imports `db` from here (e.g. `from database import db`) and
# calls collections on it directly, e.g. `db.courses.find_one(...)` —
# there's no ORM/schema layer, so this file is the entire "data access setup".
import os
from pathlib import Path
from dotenv import load_dotenv
from motor.motor_asyncio import AsyncIOMotorClient  # async MongoDB driver

load_dotenv(Path(__file__).parent / '.env')

# MONGO_URL: connection string (local mongodb://localhost:27017 in dev,
# mongodb+srv://... Atlas URI in production — see MONGO_URL secret on the
# Azure Container App).
client = AsyncIOMotorClient(os.environ['MONGO_URL'])
# DB_NAME: logical database name within the cluster (e.g. "coaching_academy").
db = client[os.environ['DB_NAME']]
