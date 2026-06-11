#!/bin/bash

echo "Fetching secrets from AWS Parameter Store..."

DATABASE_URL=$(aws ssm get-parameter \
  --name "/webhook/production/database_url" \
  --with-decryption \
  --query "Parameter.Value" \
  --output text \
  --region ap-south-1)

REDIS_URL=$(aws ssm get-parameter \
  --name "/webhook/production/redis_url" \
  --with-decryption \
  --query "Parameter.Value" \
  --output text \
  --region ap-south-1)

POSTGRES_USER=$(aws ssm get-parameter \
  --name "/webhook/production/postgres_user" \
  --with-decryption \
  --query "Parameter.Value" \
  --output text \
  --region ap-south-1)

POSTGRES_PASSWORD=$(aws ssm get-parameter \
  --name "/webhook/production/postgres_password" \
  --with-decryption \
  --query "Parameter.Value" \
  --output text \
  --region ap-south-1)

POSTGRES_DB=$(aws ssm get-parameter \
  --name "/webhook/production/postgres_db" \
  --with-decryption \
  --query "Parameter.Value" \
  --output text \
  --region ap-south-1)

GRAFANA_PASSWORD=$(aws ssm get-parameter \
  --name "/webhook/production/grafana_password" \
  --with-decryption \
  --query "Parameter.Value" \
  --output text \
  --region ap-south-1)

cat > .env << EOF
DATABASE_URL=${DATABASE_URL}
REDIS_URL=${REDIS_URL}
POSTGRES_USER=${POSTGRES_USER}
POSTGRES_PASSWORD=${POSTGRES_PASSWORD}
POSTGRES_DB=${POSTGRES_DB}
GRAFANA_PASSWORD=${GRAFANA_PASSWORD}
EOF

echo "Secrets written to .env"