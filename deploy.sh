#!/bin/bash
# deploy.sh - Deploy Meeting Coach to Google Cloud Run
# This script satisfies the hackathon bonus: "automated Cloud Deployment using scripts"

set -euo pipefail

# ---- Preflight Checks ----

# Check gcloud CLI is installed
if ! command -v gcloud &>/dev/null; then
    echo "ERROR: gcloud CLI is not installed."
    echo "Install it from: https://cloud.google.com/sdk/docs/install"
    exit 1
fi

# Check GOOGLE_CLOUD_PROJECT is set
if [ -z "${GOOGLE_CLOUD_PROJECT:-}" ]; then
    echo "ERROR: GOOGLE_CLOUD_PROJECT environment variable is not set."
    echo "Run: export GOOGLE_CLOUD_PROJECT=your-project-id"
    exit 1
fi

# Configuration
PROJECT_ID="$GOOGLE_CLOUD_PROJECT"
REGION="${GOOGLE_CLOUD_LOCATION:-us-central1}"
SERVICE_NAME="meeting-coach"

echo "=== Meeting Coach - Cloud Run Deployment ==="
echo "Project:  $PROJECT_ID"
echo "Region:   $REGION"
echo "Service:  $SERVICE_NAME"
echo ""

# Ensure gcloud is configured
gcloud config set project "$PROJECT_ID"

# Enable required APIs
echo "Ensuring required APIs are enabled..."
REQUIRED_APIS=(
    "run.googleapis.com"
    "firestore.googleapis.com"
    "secretmanager.googleapis.com"
    "artifactregistry.googleapis.com"
)
for api in "${REQUIRED_APIS[@]}"; do
    if ! gcloud services list --enabled --filter="name:$api" --format="value(name)" --project="$PROJECT_ID" 2>/dev/null | grep -q "$api"; then
        echo "  Enabling $api..."
        gcloud services enable "$api" --project="$PROJECT_ID"
    else
        echo "  $api already enabled."
    fi
done
echo ""

# Create the API key secret if it doesn't exist
if ! gcloud secrets describe GOOGLE_API_KEY --project="$PROJECT_ID" &>/dev/null; then
    echo "Creating GOOGLE_API_KEY secret..."
    echo "Enter your Google API key:"
    read -s API_KEY
    echo "$API_KEY" | gcloud secrets create GOOGLE_API_KEY \
        --data-file=- \
        --project="$PROJECT_ID"
    echo "Secret created."
fi

# Deploy to Cloud Run
echo ""
echo "Deploying to Cloud Run..."
gcloud run deploy "$SERVICE_NAME" \
    --source . \
    --region "$REGION" \
    --project "$PROJECT_ID" \
    --allow-unauthenticated \
    --set-env-vars="GOOGLE_CLOUD_PROJECT=$PROJECT_ID" \
    --set-secrets="GOOGLE_API_KEY=GOOGLE_API_KEY:latest" \
    --timeout=3600 \
    --session-affinity \
    --min-instances=1 \
    --max-instances=5 \
    --memory=1Gi \
    --cpu=2

# Get the service URL
SERVICE_URL=$(gcloud run services describe "$SERVICE_NAME" \
    --region "$REGION" \
    --project "$PROJECT_ID" \
    --format="value(status.url)")

echo ""
echo "=== Deployment Complete ==="
echo "Service URL: $SERVICE_URL"
echo ""
echo "Open $SERVICE_URL in your browser to start coaching!"
