#!/bin/bash

# Set notarization environment variables
export APPLE_ID="lualbert356@gmail.com"
export APPLE_APP_SPECIFIC_PASSWORD="rded-xorx-nvkv-pypm"
export APPLE_TEAM_ID="K3P5JT6XR9"

echo "🔨 Building and notarizing app..."
npm run dmg-only

if [ $? -eq 0 ]; then
    echo "✅ Build successful! Uploading to S3..."
    
    # Upload to S3
    aws s3 cp "dist/Alexis AI-1.0.0.dmg" s3://aiclone-downloads/downloads/
    aws s3 cp "dist/Alexis AI-1.0.0.dmg" s3://aiclone-downloads/updates/
    aws s3 cp "dist/latest-mac.yml" s3://aiclone-downloads/updates/
    
    echo "🚀 Upload complete! Your notarized app is now live."
else
    echo "❌ Build failed!"
fi 