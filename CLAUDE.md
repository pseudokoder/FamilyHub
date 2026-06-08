# Project: FamilyHub Lite

## About the Project
FamilyHub Lite is a portfolio web app for a geopraphically distributed 
family (Spring Hill TN + Las Vegas NV). Core features
- Family geneology and family tree where each family member gets an 
about page in the form of a wiki like entry.  To be structured to mimic 
Wikipedia pages with links to photos and other enteries
- Authenticaed family members may add/edit entries to wiki pages
- Family photo albums
- Announcement/bulletin board
- Simple user authentication (per-family member accounts)
- Lightweight - SQLite backend, no heavy infractructure
- Built as a learning project alongside WGU SE degree
- Planned v2 rewrite in Java/Spring Boot after Python version complete
- Development environment will live at https://familyhub.pseudokoder.com
- Completed project will live at https://family.leiters.org

## About the Developer
- WGU BS Software Engineering student, expected Fall 2027
- Currently in Python Intro - beginner to intermediate skill level
- Background in C/C++ (rusty), returning to coding after ~8 years gap
- ADHD - prefer concise explanations, concrete examples, no rabbit holes

## Project Stack
- Python 3, Flask, Blueprint structure, SQLite, SQLAlchemy, Bootstrap
- Virtual environment: venv (activated before running claude)
- IDE: PyCharm

## How I Want You to Help
- Explain what you're doing and why - I'm learning, not just shipping
- Flag when I'm doing something that would cause problems at scale
- Suggest best practices a junior SE would be expected to know
- Keep suggestions focused on the current task - don't refactor everything
- When I'm stuck, give me the smallest hint first before the full answer

## Current Status
- Day 2 skeleton complete with Blueprint structure
- Day 3 complete: config + database setup
  - `Config` class in app/config.py reads SECRET_KEY and DATABASE_URL from env
  - `.env` loaded explicitly (since `python run.py` doesn't auto-load it)
  - `.env` untracked from git; committed `.env.example` template instead
  - SQLAlchemy wired into the app factory via `db.init_app(app)`
  - First model: `FamilyMember` (app/models/family_member.py)
  - DB defaults to SQLite at instance/familyhub.db (gitignored)
  - Fixed dependency: Flask-Bootstrap -> Bootstrap-Flask (provides Bootstrap5)
- Day 4 next: `flask init-db` command, then auth blueprint
  - Note: db.create_all() won't alter existing tables; Flask-Migrate later
