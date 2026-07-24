# AGENTS.md

## Cursor Cloud specific instructions

### What this repo is
CiviSpec is a civil-engineering web app that generates IDF (Intensity-Duration-Frequency)
rainfall curves. The **active** stack is:

- **Backend:** Flask app at `server/app.py` (port 5000). This is the deployed backend
  (see `.github/workflows/deploy-cloud-run.yml`). It also serves the built React app from
  `server/build` in production.
- **Frontend:** React (Create React App) in `client/` (port 3000).
- **Database:** MongoDB on `localhost:27017`.

The root `index.js` / `routes/`, `server/index.js`, and `archive-node-backend/` are legacy
Node backends and are **not** run for local dev.

### Environment already provisioned in the snapshot
- Python 3.12 venv lives at `/workspace/.venv` (deps from `server/requirements.txt`).
- `client/node_modules` installed via npm.
- System packages `python3.12-venv` and `mongodb-org` (MongoDB 8.0) are installed.
- The update script only refreshes pip/npm deps; it does **not** start services.

### Starting the services (do this manually each session; run in tmux)
MongoDB does not auto-start. Start it first:
```
sudo mkdir -p /data/db && sudo chown -R "$(whoami)" /data/db
mongod --dbpath /data/db --bind_ip 127.0.0.1 --port 27017
```

Backend (Flask). It does **not** load `.env`, so pass env vars inline. Use a **local**
Mongo URI, not the committed Atlas URI (which points at real/prod data):
```
cd server
MONGO_URI="mongodb://localhost:27017/civispec" \
JWT_SECRET_KEY="dev-secret" \
ADMIN_EMAIL="admin@civispec.com" \
FRONTEND_ORIGINS="http://localhost:3000" \
PORT=5000 \
/workspace/.venv/bin/python app.py
```

Frontend (CRA dev server). `client/.env` sets `REACT_APP_API_BASE_URL` to a **production**
URL; override it to empty so the app uses the CRA proxy (`client/package.json` -> `proxy`)
to the local backend on :5000:
```
cd client
REACT_APP_API_BASE_URL= BROWSER=none PORT=3000 npm start
```

### Lint / test / build
- There are **no automated tests** (CRA `npm test` reports 0 matches).
- Lint runs as part of the CRA build. Build with:
  `cd client && REACT_APP_API_BASE_URL=/api npx react-scripts build`

### Access-control gotcha for testing IDF generation
IDF endpoints (`/api/idf/curves`, `/api/v2/idf/curves`) require an active
subscription/trial. New signups get `subscriptionStatus: trial_pending` and are blocked
(HTTP 402) behind Stripe card verification, which is not configured locally. **Admins
bypass this gate.** Register the admin email (matches `ADMIN_EMAIL`) to test the full
flow, e.g. `admin@civispec.com`. The `/api/v2/idf/curves` endpoint needs a `stationId`
(get one from `/api/nearest-station?lat=..&lon=..`).
