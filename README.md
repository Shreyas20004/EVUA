# EVUA

## Overview

EVUA is a full-stack web application with a modern React frontend (using Vite) and a FastAPI-powered Python backend. This document explains the project structure and provides setup instructions to help contributors get started quickly.

---

## Project Structure

```
EVUA/ 
├── frontend/ # Vite + React frontend application 
│ └── ... # Frontend source code, components, assets, etc. 
├── backend/ # FastAPI backend application 
│ ├── app/ # Main FastAPI app files (routes, main.py, etc.) 
│ ├── model/ # Python models (Pydantic schemas, DB models, etc.) 
│ └── requirements.txt# Python dependencies for backend (venv setup) 
│ └── README.md # Project documentation (this file)
```

---

## Frontend

- **Location:** `frontend/`
- **Tech:** Vite + React
- **Description:** Contains all frontend code, UI components, pages, and static assets.

### Running the Frontend

1. Open a terminal and navigate to the `frontend` folder:
    ```sh
    cd frontend
    ```
2. Install dependencies:
    ```sh
    npm install
    ```
3. Start the development server:
    ```sh
    npm run dev
    ```
4. The app will usually be available at `http://localhost:5173` (or as specified in the console).

---

## Backend

- **Location:** `backend/`
- **Tech:** FastAPI (Python)
- **Description:** Contains backend code (API routes, business logic, models).

### Backend Structure

- `app/` – FastAPI application files (routes, main, etc.)
- `model/` – Pydantic & database models
- `requirements.txt` – Python package dependencies

### Running the Backend

1. Open a terminal and navigate to the `backend` folder:
    ```sh
    cd backend
    ```
2. Create and activate a Python virtual environment:
    ```sh
    python -m venv venv
    source venv/bin/activate        # On Linux/macOS
    venv\Scripts\activate           # On Windows
    ```
3. Install dependencies:
    ```sh
    pip install -r requirements.txt
    ```
4. Start the FastAPI server (assuming main application file is `app/main.py`):
    ```sh
    fastapi dev main.py
    ```
5. The API will be available at `http://localhost:8000` by default.

---

## Contributing

1. create a new branch for your feature or bugfix.
2. Make your changes and commit them with clear messages.
3. Open a Pull Request describing your changes.

