import 'dotenv/config';
import express          from 'express';
import { createServer } from 'http';
import { Server }       from 'socket.io';
import mongoose         from 'mongoose';
import cors             from 'cors';
import { createClient } from 'redis';

import envRoutes         from './routes/env.js';
import episodeRoutes     from './routes/episodes.js';
import leaderboardRoutes from './routes/leaderboard.js';
import errorHandler      from './middleware/errorHandler.js';

const app    = express();
const server = createServer(app);
const io     = new Server(server, {
  cors: { origin: ['http://localhost:3000','http://localhost:5173'], methods: ['GET','POST'] }
});

const redis = createClient({ url: process.env.REDIS_URL || 'redis://localhost:6379' });
await redis.connect();
console.log('Redis connected');

redis.subscribe('env:steps', (message) => {
  const data = JSON.parse(message);
  io.emit('env_step', data);
});

redis.subscribe('episodes:complete', (message) => {
  const data = JSON.parse(message);
  io.emit('episode_complete', data);
});

app.use(cors({ origin: ['http://localhost:3000','http://localhost:5173'] }));
app.use(express.json());
app.use((req, _res, next) => { req.io = io; req.redis = redis; next(); });

app.use('/api/env',         envRoutes);
app.use('/api/episodes',    episodeRoutes);
app.use('/api/leaderboard', leaderboardRoutes);
app.get('/health', (_req, res) => res.json({ status: 'healthy', service: 'dashboard' }));
app.use(errorHandler);

await mongoose.connect(process.env.MONGO_URI);
console.log('MongoDB Atlas connected');

const PORT = process.env.PORT || 5000;
server.listen(PORT, () => console.log(`Dashboard service on port ${PORT}`));

io.on('connection', (socket) => {
  console.log(`Client connected: ${socket.id}`);
  socket.on('disconnect', () => console.log(`Client disconnected: ${socket.id}`));
});