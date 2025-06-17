const fs = require('fs-extra');
const path = require('path');
const { execSync } = require('child_process');

// Paths
const rootDir = path.join(__dirname, '..');
const frontendDir = path.join(rootDir, 'frontend');
const frontendBuildDir = path.join(frontendDir, 'build');
const electronDir = __dirname;

// Directories to copy from project root to electron directory
const dirsToCopy = [
  { src: 'frontend/build', dest: 'frontend/build' },
  { src: 'backend', dest: 'backend', exclude: ['__pycache__', '*.pyc'] },
  { src: 'rag', dest: 'rag', exclude: ['__pycache__', '*.pyc'] },
  { src: 'data', dest: 'data' },
  { src: 'models', dest: 'models' },
  { src: 'logs', dest: 'logs' },
  { src: 'pending_responses', dest: 'pending_responses' },
  { src: 'scripts', dest: 'scripts', exclude: ['__pycache__', '*.pyc'] }
];

// Files to copy from project root to electron directory
const filesToCopy = [
  { src: '.env', dest: '.env' },
  { src: '.env.production', dest: '.env.production' }
];

// Ensure the frontend is built
console.log('Building React frontend...');
try {
  execSync('npm run build', { cwd: frontendDir, stdio: 'inherit' });
  console.log('Frontend build completed successfully.');
} catch (error) {
  console.error('Failed to build frontend:', error);
  process.exit(1);
}

// Create necessary directories and copy files
console.log('Copying project files to electron directory...');

// Helper function to copy directory with exclusions
function copyDirWithExclusions(src, dest, excludePatterns = []) {
  // Ensure the destination directory exists
  fs.ensureDirSync(dest);
  
  // Get all files in the source directory
  const entries = fs.readdirSync(src, { withFileTypes: true });
  
  for (const entry of entries) {
    const srcPath = path.join(src, entry.name);
    const destPath = path.join(dest, entry.name);
    
    // Check if the entry should be excluded
    const shouldExclude = excludePatterns.some(pattern => {
      if (pattern.endsWith('*')) {
        const extension = pattern.slice(0, -1);
        return entry.name.endsWith(extension);
      }
      return entry.name === pattern;
    });
    
    if (shouldExclude) {
      console.log(`Skipping excluded item: ${srcPath}`);
      continue;
    }
    
    if (entry.isDirectory()) {
      // Recursively copy subdirectories
      copyDirWithExclusions(srcPath, destPath, excludePatterns);
    } else {
      // Copy files
      fs.copyFileSync(srcPath, destPath);
    }
  }
}

// Copy directories
for (const dir of dirsToCopy) {
  const srcDir = path.join(rootDir, dir.src);
  const destDir = path.join(electronDir, dir.dest);
  
  if (fs.existsSync(srcDir)) {
    console.log(`Copying ${dir.src} to ${destDir}`);
    fs.ensureDirSync(path.dirname(destDir));
    copyDirWithExclusions(srcDir, destDir, dir.exclude || []);
    console.log(`Finished copying ${dir.src}`);
  } else {
    console.log(`Warning: Source directory ${srcDir} does not exist, creating empty directory`);
    fs.ensureDirSync(destDir);
  }
}

// Copy files
for (const file of filesToCopy) {
  const srcFile = path.join(rootDir, file.src);
  const destFile = path.join(electronDir, file.dest);
  
  if (fs.existsSync(srcFile)) {
    console.log(`Copying ${file.src} to ${destFile}`);
    fs.copyFileSync(srcFile, destFile);
  } else {
    console.log(`Warning: Source file ${srcFile} does not exist, skipping`);
  }
}

// Build the Electron app
console.log('Building Electron app...');
try {
  execSync('npm run build', { cwd: electronDir, stdio: 'inherit' });
  console.log('Electron app built successfully.');
} catch (error) {
  console.error('Failed to build Electron app:', error);
  process.exit(1);
}

console.log('Build process completed successfully!');
