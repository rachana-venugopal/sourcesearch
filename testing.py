from pymongo import MongoClient
from dotenv import load_dotenv
import os
import requests
import time
import re
import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity


# Load .env
load_dotenv()


# Retrieves the mongo uri and github PAT from env file. Loads MongoDB database into existence, and creates the collection which it will be added to DB.
mongo_uri = os.getenv("MONGO_URI")
github_token = os.getenv("GITHUB_TOKEN")

client = MongoClient(mongo_uri)
db = client["my_database"]
collection = db["my_collection"]

# inputs the Github PAT
headers = {}
if github_token:
   headers['Authorization'] = f'token {github_token}'


# takes in input text and cleans it by removing non alphanumeric characters and whitespace
def clean_text(text):
   if not text:
       return ""
   text = re.sub(r'[`*#\-]+', '', text)
   text = re.sub(r'\s+', ' ', text)
   return text.strip()


# creates chunks (groups of information that will be analyzed and acted on to get meaningful results) -- a chunk will be a repository's info
def create_chunk_text(repo):
   # the information that will be returned as a chunk
   return f"""
   Repository Name: {repo.get('name', '')}
   Description: {clean_text(repo.get('description', ''))}
   Language: {repo.get('language', 'Unknown')}
   Topics: {', '.join(repo.get('topics', []))}
   URL: {repo.get('html_url', '')}
   """


# TF-IDF vector for a single text (kept function name to minimize changes)
def get_embedding(text):
   if not text or not text.strip():
       return None
   vectorizer = TfidfVectorizer(stop_words="english", max_features=5000)
   vec = vectorizer.fit_transform([text]).toarray()[0]
   return vec.tolist()


# retrieves the information needed to be chunked from user given input
def get_repo_info_from_url(url):
   # checks the validity of the user's provided url
   match = re.match(r'https://github\.com/([^/]+)/([^/]+)', url)
   if not match:
       print("Invalid GitHub repo URL.")
       return None
   # groups the information needed from the url and inputs it into the api url format
   owner, repo = match.groups()
   api_url = f"https://api.github.com/repos/{owner}/{repo}"
   # retrieves the information given by the github API for the input url
   response = requests.get(api_url, headers=headers)
   if response.status_code != 200:
       print("GitHub API error:", response.status_code)
       return None
   # returns a JSON file of the info associated with the user link
   return response.json()


# gets the "embedding" for the user url (now returns user chunk text)
def get_user_repo_embedding(repo_url):
   # gets the repo info from the url
   repo = get_repo_info_from_url(repo_url)
   if not repo:
       return None, None
   # create chunk text; TF-IDF will be computed against corpus later
   chunk = create_chunk_text(repo)
   return repo, chunk


# the method that finds the 5 most similar repositories to the user given repository using TF-IDF
def find_top_similar_repos(user_text, language=None, topics=None, top_k=5):
   # first searches on languages and topics
   query = {}
   if language:
       query["language"] = language
   if topics:
       query["topics"] = {"$in": topics}

   cursor = list(collection.find(query))

   # fallback if no results found in the db
   if not cursor:
       print("⚠️ No filtered matches found, falling back to all repos.")
       cursor = list(collection.find({}))

   print(f"🔎 Comparing against {len(cursor)} candidate repos from MongoDB...")

   repo_texts = [create_chunk_text(doc) for doc in cursor]
   vectorizer = TfidfVectorizer(stop_words="english", max_features=5000)

   tfidf = vectorizer.fit_transform(repo_texts + [user_text])
   repo_vecs = tfidf[:-1]
   user_vec = tfidf[-1]

   sims = cosine_similarity(user_vec, repo_vecs)[0]
   scored_repos = list(zip(sims, cursor))
   scored_repos.sort(key=lambda x: x[0], reverse=True)

   return scored_repos[:top_k]


# retrieves open source repositories from github and adds them to mongo db database
def fetch_open_source_repos(pages=2):
   all_repos = []
   for page in range(1, pages + 1):
       print(f"🔄 Fetching GitHub page {page}")
       url = f"https://api.github.com/search/repositories?q=topic:open-source&sort=stars&order=desc&per_page=100&page={page}"
       response = requests.get(url, headers=headers)
       if response.status_code != 200:
           print("GitHub API error:", response.status_code)
           break
       data = response.json()
       repos = data.get("items", [])
       all_repos.extend(repos)
       time.sleep(2)
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
           "topics": repo.get("topics", [])
       }
       collection.update_one({"id": doc["id"]}, {"$set": doc}, upsert=True)


# --- CONTROL FLOW ---
if __name__ == "__main__":
   print("📌 Choose a mode:")
   print("1. Load open-source repos to MongoDB (only run once)")
   print("2. Match a GitHub repo to similar open-source repos\n")
   mode = input("Enter 1 or 2: ").strip()

   if mode == "1":
       pages = input("How many GitHub pages to load? (default 2): ").strip()
       pages = int(pages) if pages.isdigit() else 2
       repos = fetch_open_source_repos(pages=pages)
       print(f"✅ Fetched {len(repos)} repos.")
       save_repos_to_mongo(repos)
       print("✅ Saved all repos to MongoDB.\n")

   elif mode == "2":
       user_repo_url = input("\nEnter a GitHub repo URL: ").strip()
       user_repo, user_embedding = get_user_repo_embedding(user_repo_url)

       if user_embedding is None:
           print("❌ Failed to process user repo.")
       else:
           print(f"\n🔍 Finding repos similar to: {user_repo['full_name']}")
           print(f"📄 Description: {user_repo.get('description')}")
           print(f"🧠 Language: {user_repo.get('language')}")
           print(f"🏷️ Topics: {user_repo.get('topics', [])}")
           print(f"🔗 URL: {user_repo['html_url']}\n")

           language = user_repo.get("language")
           topics = user_repo.get("topics", [])

           top_repos = find_top_similar_repos(user_embedding, language=language, topics=topics)

           print("✨ Top 5 most similar open-source repositories:\n")
           for i, (score, repo) in enumerate(top_repos, start=1):
               print(f"{i}. {repo['full_name']} (Similarity Score: {score:.4f})")
               print(f"   📄 {repo.get('description')}")
               print(f"   🧠 Language: {repo.get('language')}")
               print(f"   🔗 {repo['html_url']}\n")

   else:
       print("❌ Invalid input. Please enter 1 or 2.")
