/**
 * Utility functions for the Electron app
 */
const path = require('path');
const fs = require('fs');
const { app } = require('electron');

// Path to project root
const PROJECT_ROOT = app.isPackaged 
  ? path.join(app.getAppPath(), '..', '..') 
  : path.join(__dirname, '..');

/**
 * Get resource path based on whether we're in development or production
 * @returns {string} Path to Python executable
 */
function findPythonPath() {
  // Check for environment variable first
  if (process.env.PYTHON_PATH) {
    return process.env.PYTHON_PATH;
  }
  
  // In development, try to find Python in the virtual environment
  const venvPythonPath = path.join(PROJECT_ROOT, 'venv', 'bin', 'python');
  if (fs.existsSync(venvPythonPath)) {
    return venvPythonPath;
  }
  
  // Fall back to system Python
  return 'python3';
}

/**
 * Get the path to a resource file, handling both development and production environments
 * @param {string} relativePath - Path relative to the project root
 * @returns {string} Absolute path to the resource
 */
function getResourcePath(relativePath) {
  const appPath = app.getAppPath();
  const isAsar = appPath.includes('app.asar');
  
  if (isAsar) {
    // In production, resources are outside the asar archive
    // Check if relativePath already starts with 'resources/' to avoid duplication
    if (relativePath.startsWith('resources/')) {
      // Remove the 'resources/' prefix to avoid duplication
      const cleanPath = relativePath.replace('resources/', '');
      return path.join(path.dirname(appPath), 'resources', cleanPath);
    } else {
      return path.join(path.dirname(appPath), 'resources', relativePath);
    }
  } else {
    // In development
    return path.join(PROJECT_ROOT, relativePath);
  }
}

module.exports = {
  PROJECT_ROOT,
  findPythonPath,
  getResourcePath
};
