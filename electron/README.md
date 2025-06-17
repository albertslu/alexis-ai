# AI Clone Desktop App

This is the desktop application for AI Clone, allowing users to auto-respond to messages and emails using their personalized AI clone.

## Features

- **iMessage Auto-Response**: Automatically respond to incoming messages using your AI clone
- **Email Auto-Response**: Automatically respond to emails using your AI clone
- **User-Friendly Interface**: Manage your AI clone and auto-response settings
- **System Tray Integration**: Control auto-response features from the menu bar
- **Permission Management**: Guided setup for required macOS permissions

## Development Setup

1. Install dependencies:
```bash
cd electron
npm install
```

2. Build the React frontend:
```bash
cd ../frontend
npm install
npm run build
```

3. Run the Electron app in development mode:
```bash
cd ../electron
npm run dev
```

## Building the App

To build the app for distribution:

```bash
# First build the React frontend
cd frontend
npm run build

# Then build the Electron app
cd ../electron
npm run dist
```

This will create a distributable macOS app in the `dist` folder.

## Required macOS Permissions

The app requires the following permissions:

- **Full Disk Access**: To read the Messages database
- **Automation**: To control the Messages app for sending responses

The app will guide users through setting up these permissions during first launch.

## Architecture

- **Electron Main Process**: Manages the app lifecycle and background processes
- **Backend Flask Server**: Handles AI processing and API requests
- **Message Listener**: Monitors the Messages database for new messages
- **Email Listener**: Monitors Gmail for new emails
- **React Frontend**: User interface for managing the AI clone

## Troubleshooting

If you encounter issues:

1. Check the app logs in the Console app
2. Ensure all required permissions are granted
3. Verify that Python and required packages are installed
4. Check that the Messages app is properly configured with your Apple ID
