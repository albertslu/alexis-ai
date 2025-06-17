const path = require('path');
const fs = require('fs');

// This script checks paths in the production app
console.log('Checking production paths...');

// Simulate app.getAppPath() in production
const simulatedAppPath = '/Applications/Alexis AI.app/Contents/Resources/app.asar';
console.log(`Simulated app path: ${simulatedAppPath}`);

// Check our fixed path resolution
const fixedPath = path.join(path.dirname(simulatedAppPath), 'resources', 'overlay-agent.app', 'Contents', 'MacOS', 'overlay-agent');
console.log(`Fixed path: ${fixedPath}`);

// Check if the path exists
try {
  if (fs.existsSync(fixedPath)) {
    console.log('✅ Fixed path exists!');
    
    // Check if executable
    try {
      fs.accessSync(fixedPath, fs.constants.X_OK);
      console.log('✅ Agent is executable!');
    } catch (err) {
      console.log(`❌ Agent is NOT executable: ${err.message}`);
    }
  } else {
    console.log('❌ Fixed path does NOT exist');
  }
} catch (err) {
  console.log(`Error checking path: ${err.message}`);
}

// List resources directory to see what's actually there
try {
  const resourcesDir = path.join(path.dirname(simulatedAppPath), 'resources');
  console.log(`\nContents of ${resourcesDir}:`);
  const items = fs.readdirSync(resourcesDir);
  items.forEach(item => {
    console.log(`- ${item}`);
  });
} catch (err) {
  console.log(`Error listing directory: ${err.message}`);
}
