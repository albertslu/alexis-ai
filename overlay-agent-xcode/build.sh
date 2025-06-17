#!/bin/bash

echo "Building Alexis AI Overlay Agent..."

# Create directories if they don't exist
mkdir -p build
mkdir -p ../electron/resources

# Define app bundle path
APP_BUNDLE="../electron/resources/overlay-agent.app"
CONTENTS_DIR="$APP_BUNDLE/Contents"
MACOS_DIR="$CONTENTS_DIR/MacOS"
RESOURCES_DIR="$CONTENTS_DIR/Resources"

# Clean up previous build if it exists
rm -rf "$APP_BUNDLE"

echo "Creating Xcode project..."

# Create app bundle structure
mkdir -p "$MACOS_DIR"
mkdir -p "$RESOURCES_DIR"

# Copy Info.plist
cp Info.plist "$CONTENTS_DIR/"

echo "Compiling Swift files..."

# Compile Swift files
swiftc -o build/overlay-agent \
    AppDelegate.swift \
    OverlayWindow.swift \
    WebSocketServer.swift \
    main.swift \
    -framework Cocoa \
    -framework WebKit

if [ $? -ne 0 ]; then
    echo "Error: Failed to compile Swift files."
    exit 1
fi

echo "Creating app bundle..."

# Copy executable to app bundle
cp build/overlay-agent "$MACOS_DIR/"

echo "Copying app bundle to resources directory..."

# Set executable permissions
chmod +x "$MACOS_DIR/overlay-agent"

echo "Build completed successfully!"
echo "Overlay agent app bundle is located at: $(cd "$(dirname "$APP_BUNDLE")"; pwd)/$(basename "$APP_BUNDLE")"
