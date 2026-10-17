# CareerPath (core build)
## Setup
1. `python -m venv venv && source venv/bin/activate && pip install -r requirements.txt`
2. `mysql -u root -p < schema.sql && mysql -u root -p < migration.sql` and create a MySQL user with access to `careerpath`
3. `cp .env.example .env` and fill in values (never commit `.env`)
4. `flask --app app create-demo` creates test student `demo@example.com` / `Demo@1234` (non-production)
5. `flask --app app create-admin` creates `admin@example.com` / `Admin@1234` (non-production)
6. `flask --app app run`
## Manual test checklist
Register, take quiz, see matches, open a roadmap, save/unsave a course, search/filter/sort courses, log out, delete account.
## Deployment
Use `gunicorn app:app` behind HTTPS, set `SESSION_COOKIE_SECURE=True`, a strong `SECRET_KEY`, and a least-privilege DB user.
## API (JSON)
GET /api/courses, /api/courses/<id>, /api/careers, /api/careers/<id>, /api/scholarships, /api/recommendations (login required); POST /api/chat with header `X-CSRF`.
## Not yet built
Live AI model for the chatbot (current chat is rule-based over your own data), chat history storage, extra tables (skills, exams, colleges), career editing in admin, automated tests.
