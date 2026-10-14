#!/bin/bash
gcloud run deploy social-security-optimizer \
  --source . \
  --region us-east1 \
  --allow-unauthenticated