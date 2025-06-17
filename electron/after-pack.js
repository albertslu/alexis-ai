const fs = require('fs');
const fsPromises = require('fs').promises;
const path = require('path');

/**
 * This script runs after the app is packed by electron-builder.
 * It modifies the HTML files to use relative paths instead of absolute paths.
 */
exports.default = async function(context) {
  const { appOutDir, packager, electronPlatformName } = context;
  
  console.log('Running after-pack script...');
  console.log(`App output directory: ${appOutDir}`);
  console.log(`Platform: ${electronPlatformName}`);
  
  // Update path to match where electron-builder copies the frontend build
  // For macOS, the resources are in a different location than for Windows/Linux
  const frontendBuildPath = electronPlatformName === 'darwin' 
    ? path.join(appOutDir, 'Alexis AI.app', 'Contents', 'Resources', 'frontend', 'build')
    : path.join(appOutDir, 'resources', 'frontend', 'build');
  
  // Check if the frontend build directory exists
  if (!fs.existsSync(frontendBuildPath)) {
    console.error(`Frontend build directory not found at: ${frontendBuildPath}`);
    return;
  }
  
  // Path to the index.html file
  const indexHtmlPath = path.join(frontendBuildPath, 'index.html');
  
  // Check if the index.html file exists
  if (!fs.existsSync(indexHtmlPath)) {
    console.error(`index.html not found at: ${indexHtmlPath}`);
    return;
  }
  
  // Read the index.html file
  let indexHtml = fs.readFileSync(indexHtmlPath, 'utf8');
  
  // Replace absolute paths with relative paths
  indexHtml = indexHtml.replace(/href="\//g, 'href="./');
  indexHtml = indexHtml.replace(/src="\//g, 'src="./');
  
  // Add a base tag to ensure all relative paths are resolved correctly
  indexHtml = indexHtml.replace(/<head>/, '<head>\n  <base href="./">');
  
  // Write the modified index.html file
  fs.writeFileSync(indexHtmlPath, indexHtml);
  
  console.log('Successfully modified index.html to use relative paths');
};
