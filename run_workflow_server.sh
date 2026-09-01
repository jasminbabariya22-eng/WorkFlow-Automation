#!/bin/bash
echo "======================================================================="
echo "         ENTERPRISE WORKFLOW PLATFORM - AUTO DEPLOYMENT (LINUX)"
echo "======================================================================="

# Navigate to script directory
cd "$(dirname "$0")"

# 1. Check Python
if ! command -v python3 &> /dev/null; then
    echo "[ERROR] python3 is not installed! Please run: sudo apt install python3 python3-venv python3-pip"
    exit 1
fi

# 2. Check Node
if ! command -v npm &> /dev/null; then
    echo "[ERROR] npm is not installed! Please install Node.js 18+ and npm."
    exit 1
fi

# 3. Setup Python venv & dependencies
if [ ! -f "backend/.venv/bin/python" ]; then
    echo "[INFO] Setting up Python virtual environment..."
    python3 -m venv backend/.venv
    source backend/.venv/bin/activate
    pip install --upgrade pip
    pip install -r backend/requirements.txt
    echo "[SUCCESS] Backend dependencies installed!"
else
    echo "[OK] Backend virtual environment verified."
    source backend/.venv/bin/activate
fi

# 4. Setup Frontend node_modules
if [ ! -d "frontend/node_modules" ]; then
    echo "[INFO] Installing frontend node_modules..."
    cd frontend && npm install && cd ..
    echo "[SUCCESS] Frontend dependencies installed!"
else
    echo "[OK] Frontend node_modules verified."
fi

echo "======================================================================="
echo " Starting Backend on 0.0.0.0:8000 and Frontend on 0.0.0.0:5173..."
echo "======================================================================="

# 5. Run Backend in background
cd backend
python3 -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload &
BACKEND_PID=$!
cd ..

# 6. Run Frontend
cd frontend
npm run dev -- --host 0.0.0.0 --port 5173
