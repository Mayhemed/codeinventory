const { app, BrowserWindow, ipcMain } = require('electron');
const path = require('path');
const { spawn } = require('child_process');
const fetch = require('node-fetch');

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

  mainWindow.loadFile(path.join(__dirname, 'index.html'));
  
  // Open DevTools to see errors
  mainWindow.webContents.openDevTools();
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
  // Force IPv4 by using 127.0.0.1
  const apiUrl = new URL(endpoint, 'http://127.0.0.1:8001');
  
  console.log(`API call to: ${apiUrl.toString()}`); // Debug log
  
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
    const response = await fetch(apiUrl.toString(), options);
    const result = await response.json();
    console.log(`API response:`, result); // Debug log
    return result;
  } catch (error) {
    console.error('API call failed:', error);
    throw error;
  }
});