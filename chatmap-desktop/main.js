import { app, BrowserWindow } from 'electron';
import { spawn } from 'child_process';
import { fileURLToPath } from 'url';
import { dirname } from 'path';
import { startServer } from './server.js';
import net from 'net';

const __filename = fileURLToPath(import.meta.url);
const __dirname = dirname(__filename);

// Backend apps for ChatMap
const BACKENDS = [
  { name: 'redis-server', cmd: './backend/redis-server --port 6380', port: 6380 },
  { name: 'chatmap-go', cmd: './backend/chatmap-go', port: 8001 },
  { name: 'chatmap-api', cmd: './backend/chatmap-api', port: 8000 },
];

// Wait for process to start, using port as an indicator
function waitForPort(port, timeout = 10000) {
  return new Promise((resolve, reject) => {
    const start = Date.now();

    const check = () => {
      const socket = new net.Socket();
      socket
        .setTimeout(1000)
        .once('error', () => {
          if (Date.now() - start > timeout) {
            reject(new Error(`Timeout waiting for port ${port}`));
          } else {
            setTimeout(check, 500);
          }
        })
        .once('timeout', () => {
          socket.destroy();
          setTimeout(check, 500);
        })
        .connect(port, '127.0.0.1', () => {
          socket.end();
          resolve();
        });
    };

    check();
  });
}

let processes = [];

// Start all backends (redis, chatmap-api, chatmap-go)
async function startBackends() {
  for (const backend of BACKENDS) {
    const proc = spawn(backend.cmd, [], {
      cwd: __dirname,
      shell: true,
      detached: false,
      stdio: 'inherit',
    });

    proc.on('error', (err) => {
      console.error(`Failed to start ${backend.name}:`, err);
    });

    processes.push(proc);

    // Unexpected errors
    proc.on('uncaughtException', (err) => {
      console.error('Uncaught Exception:', err);
      cleanup();
      app.quit();
    });

    proc.on('unhandledRejection', (err) => {
      console.error('Unhandled Rejection:', err);
      cleanup();
      app.quit();
    });

    console.log(`Waiting for ${backend.name} on port ${backend.port}...`);
    await waitForPort(backend.port);
    console.log(`${backend.name} is ready.`);
  }
}

// When app is ready, start backends and create window
app.whenReady().then(async () => {
  try {
    await startBackends();
    await startServer();

    // Create new window for the UI
    const win = new BrowserWindow({
      width: 1000,
      height: 800,
    });

    app.on('ready', async () => {
      const storedSession = await session.defaultSession.getAsyncStoragesSync();
      if (storedSession) {
        storage.setStorageSync('chatmap_access_token', storedSession['chatmap_access_token']);
      }
    });

    await win.loadURL('http://localhost:3000');
  } catch (err) {
    console.error('Startup failed:', err);
    app.quit();
  }
});

// Clean up previously launched process
function cleanup() {
  processes.forEach(proc => {
    try {
      if (!proc.killed) {
        proc.kill('SIGTERM'); // or 'SIGKILL' if needed
      }
    } catch (err) {
      console.error('Error killing process:', err);
    }
  });
  childProcesses.clear();
}

// Normal app quit
app.on('will-quit', () => {
  cleanup();
});

// When all windows are closed, kill all processes
app.on('window-all-closed', () => {
  cleanup();
  app.quit();
});