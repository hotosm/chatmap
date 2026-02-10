import express from 'express';
import path from 'path';
import { fileURLToPath } from 'url';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

const app = express();
const PORT = 3000;

app.use(express.static(path.join(__dirname, 'public')));

// Fallback for React Router
app.get('/', (req, res) => {
  res.sendFile(path.join(__dirname, 'public', 'index.html'));
});

// Start an Express server for the ChatMap UI
export async function startServer() {
  return new Promise((resolve) => {
    app.listen(PORT, () => {
      console.log(`Express server running on http://localhost:${PORT}`);
      resolve();
    });
  });
}
