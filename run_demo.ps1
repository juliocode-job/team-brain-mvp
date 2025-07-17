# =================================================================
# TeamBrain MVP - Automated Demo Script
# =================================================================

# Function to print a fancy header

function Print-Header { ... }
    param($message)
    Write-Host " "
    Write-Host "=================================================================" -ForegroundColor Cyan
    Write-Host "➡️  $message" -ForegroundColor Cyan
    Write-Host "================================================================="


# --- Step 1: Start Backend Services ---
Print-Header "Step 1: Starting ChromaDB database container..."
docker compose up -d chroma
Write-Host "✅ Database container started."

# --- Step 2: Ingest Data ---
Print-Header "Step 2: Running data ingestion script..."
& .\.venv\Scripts\python.exe ingest.py
Write-Host "✅ Data ingestion complete."

# --- Step 3: Start the API Server in the Background ---
Print-Header "Step 3: Starting the TeamBrain API server..."
# Start the Flask app as a background job
Start-Process -FilePath ".\.venv\Scripts\python.exe" -ArgumentList "app.py" -WindowStyle Hidden
Write-Host "✅ API server is starting in the background."
Write-Host "⏳ Waiting 10 seconds for the server to initialize..."
Start-Sleep -Seconds 10

# --- Step 4: Run Automated Tests ---
Print-Header "Step 4: Running automated tests..."

# Test 1: Alice asks about an engineering document (should succeed)
Write-Host "`n🧪 Test 1: Alice asks about 'deployment guide' (should succeed)" -ForegroundColor Yellow
$response_alice = Invoke-WebRequest -Uri http://localhost:5000/chat -Method POST -Headers @{"Content-Type"="application/json"} -Body '{"user_id": "user-1-alice", "message": "What is the deployment guide?"}' -UseBasicParsing
Write-Host "    - Response from server:"
$response_alice.Content | ConvertFrom-Json

# Test 2: Charlie asks about an engineering document (should fail)
Write-Host "`n🧪 Test 2: Charlie asks about 'deployment guide' (should be denied)" -ForegroundColor Yellow
$response_charlie = Invoke-WebRequest -Uri http://localhost:5000/chat -Method POST -Headers @{"Content-Type"="application/json"} -Body '{"user_id": "user-3-charlie", "message": "What is the deployment guide?"}' -UseBasicParsing
Write-Host "    - Response from server:"
$response_charlie.Content | ConvertFrom-Json

# --- Step 5: Shut Down ---
Print-Header "Step 5: Demo complete. Shutting down services..."
# Find the background process for the Flask app and stop it
Get-Process | Where-Object { $_.ProcessName -eq 'python' -and $_.Path -like "*team-brain-mvp\.venv*" } | Stop-Process -Force
# Stop the docker container
docker compose down
Write-Host "✅ All services have been stopped."
Write-Host " "