# Store Provisioning API

Backend API for provisioning WooCommerce stores on Kubernetes.

## Setup

```powershell
# Create virtual environment
python -m venv venv

# Activate
.\venv\Scripts\Activate.ps1

# Install dependencies
pip install -r requirements.txt
```

## Run

```powershell
# Development mode (auto-reload)
uvicorn app.main:app --reload

# Production mode
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

## API Endpoints

- `GET /` - API status
- `GET /health` - Health check
- `POST /stores` - Create new store
- `GET /stores` - List all stores
- `DELETE /stores/{store_name}` - Delete store

## API Documentation

Visit http://localhost:8000/docs for interactive API documentation.

## Test Endpoints

```powershell
# Create store
curl -X POST http://localhost:8000/stores -H "Content-Type: application/json" -d '{\"store_name\": \"alice\", \"owner_email\": \"alice@example.com\"}'

# List stores
curl http://localhost:8000/stores

# Delete store
curl -X DELETE http://localhost:8000/stores/alice
```
