from pymongo import MongoClient
from dotenv import load_dotenv
import os
import requests
import time
import google.generativeai as genai
import re
import numpy as np


# Load .env
load_dotenv()


# Retrieves the mongo uri, github PAT, and gemini API key from env file. Loads MongoDB database into existence, and creates the collection which it will be added to DB.
mongo_uri = os.getenv("MONGO_URI")
github_token = os.getenv("GITHUB_TOKEN")
genai.configure(api_key=os.getenv("GEMINI_API_KEY"))
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
# gets the list of floats (vectors) the numerical value associated with a repository
def get_embedding(text):
   try:
       # checks if the text inputted is valid to be fed to the embedding model
       if not text.strip():
           return None
           # embeds the text into the gemini model
       result = genai.embed_content(
           model="models/embedding-001",
           content=text,
           task_type="retrieval_document"
       )
       # returns an array of the floating points associated with the repository
       return result['embedding']
   except Exception as e:
       print("Embedding error:", e)
       return None


# retrieves the information needed to be chunked and embedded from user given input
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


# gets the numerical value of the user url by feeding it to the embedding model
def get_user_repo_embedding(repo_url):
   # gets the repo info from the url
   repo = get_repo_info_from_url(repo_url)
   if not repo:
       return None, None
       # creates the chunk text and embedding, and returns the embedding
   chunk = create_chunk_text(repo)
   embedding = get_embedding(chunk)
   return repo, embedding


# performs cosine similarity on 2 vectors, to determine how similar 2 repositories are
# one vector will be a repository in the MongoDB database, the other will be the user repo
def cosine_similarity(vec1, vec2):
   v1 = np.array(vec1)
   v2 = np.array(vec2)
   if np.linalg.norm(v1) == 0 or np.linalg.norm(v2) == 0:
       return 0
   return np.dot(v1, v2) / (np.linalg.norm(v1) * np.linalg.norm(v2))


# the method that find the 5 most similar repositories to the user given repository
def find_top_similar_repos(user_embedding, language=None, topics=None, top_k=5):
   # first searches on languages and topics
   query = {"embedding": {"$exists": True}}
   if language:
       query["language"] = language
   if topics:
       query["topics"] = {"$in": topics}
   # adds the repositories to scored_repos, finds them in db, turns them into a list
   scored_repos = []
   cursor = list(collection.find(query))
  
   # fallback if no results found in the db
   if not cursor:
       print("⚠️ No filtered matches found, falling back to all embeddings.")
       # looks through all valid repositories stored in the database
       cursor = list(collection.find({"embedding": {"$exists": True}}))


   print(f"🔎 Comparing against {len(cursor)} candidate repos from MongoDB...")


   scored_repos = []
   for doc in cursor:
       # retrieves the embedding for each repository
       repo_embedding = doc.get("embedding")
       if not repo_embedding:
           continue
       # performs cosine similarity on the user embedding and the current repo embedding
       score = cosine_similarity(user_embedding, repo_embedding)
       # adds the scores to scored_repos
       scored_repos.append((score, doc))
   # sorts the array from highest score to lowest score and returns the top k scores (set to 5)
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
   for i, repo in enumerate(repos):
       print(f"💾 Embedding repo {i+1}/{len(repos)}: {repo['full_name']}")
       chunk = create_chunk_text(repo)
       embedding = get_embedding(chunk)
       if embedding:
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
               "embedding": embedding
           }
           collection.update_one({"id": doc["id"]}, {"$set": doc}, upsert=True)
       else:
           print("⚠️ Skipped due to failed embedding.")


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
           print("❌ Failed to embed user repo.")
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
