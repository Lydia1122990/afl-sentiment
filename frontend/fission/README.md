# Installation - Fission Function Deployment Guide

## Table of Contents
1. [Prerequisites](#-prerequisites)
2. [Deployment Steps](#-deployment-steps)
3. [Monitoring & Testing](#-monitoring--testing)
4. [Directory Structure](#-directory-structure)

## Prerequisites

### 1. Environment Setup
```bash
# Verify Python 3.9 environment exists
fission env list | grep python39

# If missing, create the environment
fission env create --name python39 \
  --image fission/python-env:3.9 \
  --builder fission/python-builder:3.9
```

### 2. Required Files
Ensure your function directory contains:
- `requirements.txt` - Python dependencies
- `build.sh` - Build script
- `scriptname.py` - Main program (must contain `main()` function)
- `__init__.py` - Python package initializer

## Deployment Steps

### 1. Prepare Zip Archive
```bash
cd frontend/fission/functions/afl_sentiment_reddit

# Create archive with cleanup
zip -r afl_sentiment_reddit.zip .
zip -d afl_sentiment_reddit.zip '*.DS_Store'  # Remove macOS artifacts
mv afl_sentiment_reddit.zip ..
cd ..
```

### 2. Create Package
```bash
fission pkg create \
  --sourcearchive afl_sentiment_reddit.zip \
  --env python39 \
  --name afl-sentiment-reddit-pkg \
  --buildcmd './build.sh'
```

### 3. Verify Package
```bash
fission pkg info --name afl-sentiment-reddit-pkg
```
Expected output should show status as `succeeded`.

### 4. Create Function
```bash
fission fn create \
  --name afl-sentiment-reddit \
  --pkg afl-sentiment-reddit-pkg \
  --env python39 \
  --entrypoint "afl_sentiment_reddit.main" \
  --specializationtimeout 180 \
  --secret elastic-secret
```

### 5. Create Route
```bash
fission route create \
  --name afl-sentiment-reddit-route \
  --function afl-sentiment-reddit \
  --method GET \
  --url /afl/sentiment/reddit \
  --createingress
```

## Monitoring & Testing

### Three-Terminal Setup

| Terminal Window 1          | Terminal Window 2               | Terminal Window 3          |
|----------------------------|----------------------------------|----------------------------|
| **Port Forwarding**        | **Log Monitoring**              | **API Testing**           |
| `kubectl port-forward service/router -n fission 8080:80` | `fission fn log --f --name afl-sentiment-reddit` | `curl -k http://localhost:8080/afl/sentiment/reddit \| jq` |

### Expected Responses
1. **Successful Execution**:
```json
{
  "all_teams_count_reddit": 18,
  "all_teams_reddit": [
    {
      "avg_sentiment_reddit": 0.2230832333139276,
      "doc_count_reddit": 4157,
      "name": "weareportadelaide",
      "total_sentiment_reddit": 927.357000885997
    }
  ]
}
```

2. **Error Response**:
```
curl: (7) Failed to connect to localhost port 8080 after 1 ms: Couldn't connect to server
```

## Directory Structure
```
frontend/fission/functions/
└── afl_sentiment_reddit/
    ├── __init__.py
    ├── afl_sentiment_reddit.py
    ├── build.sh
    └── requirements.txt
```

## Appendix: Quick Command Reference
```bash
# List all functions
fission fn list

# Get function details
fission fn info --name afl-sentiment-reddit

# Delete function
fission fn delete --name afl-sentiment-reddit

# Test with sample data
echo '{"team":"collingwood"}' | fission fn test --name afl-sentiment-reddit
```