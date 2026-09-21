# On-Premise Production Server Setup Guide (`192.168.1.183`)

This guide explains how to configure your local server at `192.168.1.183` to automatically receive deployments whenever code is merged into the `main` branch.

---

## 1. Prerequisites on `192.168.1.183`

### If Server is Linux (Ubuntu / Debian):
Install Docker Engine & Docker Compose plugin:
```bash
sudo apt update
sudo apt install -y docker.io docker-compose-v2 curl git

# Allow current user to run Docker without sudo
sudo usermod -aG docker $USER
newgrp docker
```

### If Server is Windows:
1. Install [Docker Desktop for Windows](https://www.docker.com/products/docker-desktop/).
2. Ensure Docker Desktop is running and WSL2 backend is enabled.

---

## 2. Register GitHub Self-Hosted Runner (3 Minutes)

GitHub Self-Hosted Runner establishes an **outbound HTTPS connection** to GitHub. It does **not** require opening any router ports or having a public IP.

### Step 1: Get the Runner Token from GitHub
1. Open your GitHub repository in your browser:
   `https://github.com/jasminbabariya22-eng/WorkFlow-Automation`
2. Go to **Settings** $\rightarrow$ **Actions** $\rightarrow$ **Runners**.
3. Click **New self-hosted runner**.
4. Select your Server OS (Linux or Windows).

### Step 2: Run the Commands on `192.168.1.183`

#### For Linux Server:
```bash
# Create a folder for the runner
mkdir -p ~/actions-runner && cd ~/actions-runner

# Download the latest runner package (follow version shown in GitHub UI)
curl -o actions-runner-linux-x64.tar.gz -L https://github.com/actions/runner/releases/download/v2.321.0/actions-runner-linux-x64-2.321.0.tar.gz
tar xzf ./actions-runner-linux-x64.tar.gz

# Configure the runner (paste the exact config command with token from your GitHub UI)
./config.sh --url https://github.com/jasminbabariya22-eng/WorkFlow-Automation --token <YOUR_TOKEN>

# Install and start as a background system service (runs automatically on boot)
sudo ./svc.sh install
sudo ./svc.sh start
```

#### For Windows Server:
Open PowerShell as Administrator:
```powershell
# Create a folder
mkdir C:\actions-runner; cd C:\actions-runner

# Download and extract runner
Invoke-WebRequest -Uri https://github.com/actions/runner/releases/download/v2.321.0/actions-runner-win-x64-2.321.0.zip -OutFile actions-runner.zip
Expand-Archive -Path actions-runner.zip -DestinationPath .

# Configure with your token
.\config.cmd --url https://github.com/jasminbabariya22-eng/WorkFlow-Automation --token <YOUR_TOKEN>

# Install and run as Windows Service
.\actions-runner\svc.bat install
.\actions-runner\svc.bat start
```

---

## 3. How Automated Deployment Works

1. **You develop on branch `development`**:
   - Make code changes, run tests locally.
2. **You create a Pull Request to `main`**:
   - GitHub Actions automatically runs `ci.yml` (Pytest, Vite Build, Docker Build, Trivy Security Scan).
3. **You merge the PR into `main`**:
   - GitHub triggers `deploy-production.yml` on the self-hosted runner at `192.168.1.183`.
   - The runner executes `docker compose up -d --build`.
   - Your updated application is instantly live across your local network at:
     - **Web UI:** `http://192.168.1.183` or `http://192.168.1.183:3000`
     - **API Docs:** `http://192.168.1.183:8000/docs`
     - **Health Check:** `http://192.168.1.183:8000/health`

---

## 4. Manual / Direct Deployment on `192.168.1.183` (Optional)

If you ever want to run or test the Docker stack manually without GitHub:
```bash
# Clone or pull code
git clone https://github.com/jasminbabariya22-eng/WorkFlow-Automation.git
cd WorkFlow-Automation

# Start the stack
docker compose up -d --build

# View real-time logs
docker compose logs -f

# Check status
docker compose ps
```
