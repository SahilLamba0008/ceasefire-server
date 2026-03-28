# Worker Service (Python)

## Run In Docker
From repo root:
```bash
docker-compose -f infra/docker-compose.yml up --build worker
```

Note: this also starts `postgres` and `rabbitmq` (via `depends_on`).

## Run Locally
Prerequisite:
- Python 3.12

From repo root:
```bash
docker-compose -f infra/docker-compose.yml up -d postgres rabbitmq
cd services/worker
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

PowerShell env + run:
```powershell
$env:DB_HOST="localhost"
$env:RABBITMQ_HOST="localhost"
python main.py
```

## Dependencies
- `pip install -r requirements.txt`

## Expected Logs
- `Worker started...`
- `Polling for jobs...`
