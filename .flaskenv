# Public (non-secret) Flask CLI settings — safe to commit, unlike .env.
#
# TEACHING NOTE: The `flask` command needs to know which file creates your
# app. Because python-dotenv is installed, the Flask CLI automatically reads
# this file from the project root. Convention: secrets go in .env
# (git-ignored), harmless settings like this go in .flaskenv (committed).
FLASK_APP=run.py
