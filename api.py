from flask import Flask, request, jsonify
from flask_cors import CORS

from testing import (
    get_repo_info_from_url,
    create_chunk_text,
    find_top_similar_repos
)

app = Flask(__name__)
CORS(app)

@app.route("/api/similar", methods=["GET"])
def similar():
    url = request.args.get("url")
    if not url:
        return jsonify({"error": "Missing ?url parameter"}), 400

    # Fetch repo from GitHub
    user_repo = get_repo_info_from_url(url)
    if not user_repo:
        return jsonify({"error": "Invalid GitHub repo URL"}), 400

    # Convert repo to text for TF-IDF
    user_text = create_chunk_text(user_repo)

    # Your function likely returns [(score, mongo_doc), ...]
    raw_results = find_top_similar_repos(
        user_text,
        language=user_repo.get("language"),
        topics=user_repo.get("topics", []),
        top_k=5
    )

    cleaned_results = []

    for item in raw_results:
        # Case 1: (score, doc)
        if isinstance(item, tuple) and len(item) == 2:
            score, doc = item
        else:
            # Case 2: already a dict
            score, doc = None, item

        # Remove Mongo ObjectId
        if isinstance(doc, dict):
            doc.pop("_id", None)

        cleaned_results.append({
            "score": float(score) if score is not None else None,
            "full_name": doc.get("full_name"),
            "description": doc.get("description"),
            "language": doc.get("language"),
            "topics": doc.get("topics", []),
            "html_url": doc.get("html_url"),
            "stars": doc.get("stars"),
        })

    return jsonify({
        "query_repo": {
            "full_name": user_repo.get("full_name"),
            "description": user_repo.get("description"),
            "language": user_repo.get("language"),
            "topics": user_repo.get("topics", []),
            "html_url": user_repo.get("html_url"),
        },
        "results": cleaned_results
    })

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
