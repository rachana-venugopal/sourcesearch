from pymongo import MongoClient
from dotenv import load_dotenv
import os
import requests
import time 

# Load .env file
load_dotenv()

# Get the URI and token from environment
mongo_uri = os.getenv("MONGO_URI")
github_token = os.getenv("GITHUB_TOKEN")

# Connect to MongoDB
client = MongoClient(mongo_uri)

# Choose your database and collection
db = client["my_database"]
collection = db["my_collection"]

headers = {}
if github_token:
    headers['Authorization'] = f'token {github_token}'

def test_mongo_connection():
    # Insert a test document
    doc = {"name": "Juhi", "project": "SourceSearch"}
    collection.insert_one(doc)

    # Print all documents
    for doc in collection.find():
        print(doc)

def fetch_open_source_repos(pages=2):
    all_repos = []
    for page in range(1, pages + 1):
        print(f"Fetching page {page} from GitHub")
        url = f"https://api.github.com/search/repositories?q=topic:open-source&sort=stars&order=desc&per_page=100&page={page}"
        response = requests.get(url, headers=headers)
        if response.status_code != 200:
            print("GitHub API error:", response.status_code, response.text)
            break
        data = response.json()
        repos = data.get("items", [])
        all_repos.extend(repos)
        time.sleep(2)  # be nice to API (avoid rate limiting)
    return all_repos

def save_repos_to_mongo(repos):
    for repo in repos:
        doc = {
            "id": repo["id"],
            "name": repo["name"],
            "full_name": repo["full_name"],
            "html_url": repo["html_url"],
            "description": repo["description"],
            "stars": repo["stargazers_count"],
            "language": repo["language"],
            "created_at": repo["created_at"],
            "updated_at": repo["updated_at"],
            "topics": repo.get("topics", []),
        }
        # Upsert to avoid duplicates
        collection.update_one({"id": doc["id"]}, {"$set": doc}, upsert=True)

if __name__ == "__main__":
    test_mongo_connection()
    repos = fetch_open_source_repos(pages=2)  # adjust pages as needed
    print(f"Fetched {len(repos)} repos")
    save_repos_to_mongo(repos)
    print("Saved repos to MongoDB")