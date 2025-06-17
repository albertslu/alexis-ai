#!/bin/bash

# Create iconset directory
mkdir -p /Users/albertlu/Documents/GitHub/ai-clone/electron/assets/AppIcon.iconset

# Generate different icon sizes
sips -z 16 16     /Users/albertlu/Documents/GitHub/ai-clone/electron/assets/app-icon.png --out /Users/albertlu/Documents/GitHub/ai-clone/electron/assets/AppIcon.iconset/icon_16x16.png
sips -z 32 32     /Users/albertlu/Documents/GitHub/ai-clone/electron/assets/app-icon.png --out /Users/albertlu/Documents/GitHub/ai-clone/electron/assets/AppIcon.iconset/icon_16x16@2x.png
sips -z 32 32     /Users/albertlu/Documents/GitHub/ai-clone/electron/assets/app-icon.png --out /Users/albertlu/Documents/GitHub/ai-clone/electron/assets/AppIcon.iconset/icon_32x32.png
sips -z 64 64     /Users/albertlu/Documents/GitHub/ai-clone/electron/assets/app-icon.png --out /Users/albertlu/Documents/GitHub/ai-clone/electron/assets/AppIcon.iconset/icon_32x32@2x.png
sips -z 128 128   /Users/albertlu/Documents/GitHub/ai-clone/electron/assets/app-icon.png --out /Users/albertlu/Documents/GitHub/ai-clone/electron/assets/AppIcon.iconset/icon_128x128.png
sips -z 256 256   /Users/albertlu/Documents/GitHub/ai-clone/electron/assets/app-icon.png --out /Users/albertlu/Documents/GitHub/ai-clone/electron/assets/AppIcon.iconset/icon_128x128@2x.png
sips -z 256 256   /Users/albertlu/Documents/GitHub/ai-clone/electron/assets/app-icon.png --out /Users/albertlu/Documents/GitHub/ai-clone/electron/assets/AppIcon.iconset/icon_256x256.png
sips -z 512 512   /Users/albertlu/Documents/GitHub/ai-clone/electron/assets/app-icon.png --out /Users/albertlu/Documents/GitHub/ai-clone/electron/assets/AppIcon.iconset/icon_256x256@2x.png
sips -z 512 512   /Users/albertlu/Documents/GitHub/ai-clone/electron/assets/app-icon.png --out /Users/albertlu/Documents/GitHub/ai-clone/electron/assets/AppIcon.iconset/icon_512x512.png
sips -z 1024 1024 /Users/albertlu/Documents/GitHub/ai-clone/electron/assets/app-icon.png --out /Users/albertlu/Documents/GitHub/ai-clone/electron/assets/AppIcon.iconset/icon_512x512@2x.png

# Convert iconset to icns
iconutil -c icns /Users/albertlu/Documents/GitHub/ai-clone/electron/assets/AppIcon.iconset -o /Users/albertlu/Documents/GitHub/ai-clone/electron/assets/icon.icns

# Also copy the icon to be used as tray icon
cp /Users/albertlu/Documents/GitHub/ai-clone/electron/assets/AppIcon.iconset/icon_32x32.png /Users/albertlu/Documents/GitHub/ai-clone/electron/assets/tray-icon.png

echo "Icon conversion complete!"
