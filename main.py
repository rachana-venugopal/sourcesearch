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

# Choose your database and collection (element to belong to database)
db = client["my_database"]
collection = db["my_collection"]

# checks if a github token exists, and if it does, the github token is taken in and authorized
headers = {}
if github_token:
    headers['Authorization'] = f'token {github_token}'

# tests whether a document can be created, if it is added to a collection, and mongo db stores that collection
def test_mongo_connection():
    # Insert a test document
    doc = {"name": "Juhi", "project": "SourceSearch"}
    collection.insert_one(doc)

    # Print all documents
    # for doc in collection.find():
       # print(doc)

# this method is meant to collect all the open source repositores on github, formatted into 2 pages 
def fetch_open_source_repos(pages=2):
    # an array that will hold in all the repos 
    all_repos = []
    for page in range(1, pages + 1):
        print(f"Fetching page {page} from GitHub")
        # collects all the repositories on the specified page in the loop 
        url = f"https://api.github.com/search/repositories?q=topic:open-source&sort=stars&order=desc&per_page=100&page={page}"
        # receives data from the given url for the particular page
        response = requests.get(url, headers=headers)
        if response.status_code != 200:
            print("GitHub API error:", response.status_code, response.text)
            break
            # formats all the data in a JSON file 
        data =response.json() 
        # extract all repositories from the items key from JSON file, otherwise return empty list
        repos = data.get("items", [])
        # adds the repositories to all_repos
        all_repos.extend(repos)
        time.sleep(2)  # be nice to API (avoid rate limiting)
    return all_repos

# takes in all the repositories collected from the previous method and saves them to the mongo db database 
def save_repos_to_mongo(repos):
    # iterates through all the repositories 
    for repo in repos:
        # creates a dictionary in which different key/value pairs are created, representing attributes of each repository
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
    # prints out each individual dictionary of repository data
        print(doc)
        # Upsert to avoid duplicates
        collection.update_one({"id": doc["id"]}, {"$set": doc}, upsert=True)

if __name__ == "__main__":
    test_mongo_connection()
    # retrieves repositories by page 
    repos = fetch_open_source_repos(pages=2)  # adjust pages as needed
    # prints a statement saying how many repositories were retrieved
    print(f"Fetched {len(repos)} repos")
    # adds repositories to mongo db database
    save_repos_to_mongo(repos)
    print("Saved repos to MongoDB")