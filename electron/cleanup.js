/**
 * Cleanup script to remove duplicated project files from the electron directory
 * This is a one-time script to clean up after our build experiments
 */

const fs = require('fs-extra');
const path = require('path');

// Directories to remove
const dirsToRemove = [
  'frontend',
  'backend',
  'rag',
  'data',
  'models',
  'logs',
  'pending_responses',
  'scripts'
];

// Files to remove
const filesToRemove = [
  '.env',
  '.env.production'
];

console.log('Starting cleanup of duplicated files...');

// Remove directories
for (const dir of dirsToRemove) {
  const dirPath = path.join(__dirname, dir);
  
  if (fs.existsSync(dirPath)) {
    console.log(`Removing directory: ${dirPath}`);
    try {
      fs.removeSync(dirPath);
      console.log(`Successfully removed ${dirPath}`);
    } catch (error) {
      console.error(`Error removing ${dirPath}: ${error.message}`);
    }
  } else {
    console.log(`Directory not found, skipping: ${dirPath}`);
  }
}

// Remove files
for (const file of filesToRemove) {
  const filePath = path.join(__dirname, file);
  
  if (fs.existsSync(filePath)) {
    console.log(`Removing file: ${filePath}`);
    try {
      fs.removeSync(filePath);
      console.log(`Successfully removed ${filePath}`);
    } catch (error) {
      console.error(`Error removing ${filePath}: ${error.message}`);
    }
  } else {
    console.log(`File not found, skipping: ${filePath}`);
  }
}

console.log('Cleanup completed!');
