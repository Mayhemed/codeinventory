const { app, BrowserWindow, ipcMain } = require('electron');
const path = require('path');
const { spawn } = require('child_process');

let mainWindow;
let pythonProcess;

function createWindow() {
  mainWindow = new BrowserWindow({
    width: 1200,
    height: 800,
    webPreferences: {
      nodeIntegration: true,
      contextIsolation: false
    }
  });

  mainWindow.loadFile('dashboard/index.html');
  
  // Start Python backend
  pythonProcess = spawn('python', ['-m', 'codeinventory.api'], {
    cwd: path.join(__dirname, '..')
  });
  
  pythonProcess.stdout.on('data', (data) => {
    console.log(`Python: ${data}`);
  });
}

app.whenReady().then(createWindow);

app.on('window-all-closed', () => {
  if (pythonProcess) {
    pythonProcess.kill();
  }
  if (process.platform !== 'darwin') {
    app.quit();
  }
});

app.on('activate', () => {
  if (BrowserWindow.getAllWindows().length === 0) {
    createWindow();
  }
});

// Handle API calls from renderer
ipcMain.handle('api-call', async (event, endpoint, method = 'GET', data = null) => {
  const fetch = require('node-fetch');
  const url = `http://localhost:8000${endpoint}`;
  
  const options = {
    method,
    headers: {
      'Content-Type': 'application/json'
    }
  };
  
  if (data) {
    options.body = JSON.stringify(data);
  }
  
  try {
    const response = await fetch(url, options);
    return response.json();
  } catch (error) {
    console.error('API call failed:', error);
    throw error;
  }
});
