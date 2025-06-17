#!/usr/bin/env python3

from pymongo import MongoClient
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Connect to MongoDB
mongo_uri = os.getenv('MONGO_URI')
db_name = os.getenv('DB_NAME')

client = MongoClient(mongo_uri)
db = client[db_name]

# Print all users
print('Users in database:')
for user in db.users.find():
    print(f"- {user.get('email')} (User ID: {user.get('user_id')})")

# Print collections
print('\nCollections in database:')
collections = db.list_collection_names()
for collection in collections:
    print(f"- {collection}")
