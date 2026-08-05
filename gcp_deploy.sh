#!/bin/bash
gcloud run deploy social-security-optimizer \
  --source . \
  --region us-central1 \
  --allow-unauthenticated