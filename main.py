from pymongo import MongoClient
from dotenv import load_dotenv
import os

# Load .env file
load_dotenv()

# Get the URI from the environment
mongo_uri = os.getenv("MONGO_URI")

# Connect to MongoDB
client = MongoClient(mongo_uri)

# Choose your database and collection
db = client["my_database"]
collection = db["my_collection"]

def test_mongo_connection():
    # creating a python dictionary to enter into the mongo collection
    doc = {"name": "Juhi", "project": "SourceSearch"}
    collection.insert_one(doc)

    # test if it was added by printing contents of mongo collection
    for doc in collection.find():
        print(doc)

#run the test function if python3 main.py is called
if __name__ == "__main__":
    test_mongo_connection()
