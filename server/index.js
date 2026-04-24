import 'dotenv/config';
import express from 'express';
import { createServer } from 'http';
import { Server } from 'socket.io';
import mongoose from 'mongoose';
import cors from 'cors';
import { createClient } from 'redis';

import envRoutes from './routes/env.js';
import episodeRoutes from './routes/episodes.js';
import leaderboardRoutes from './routes/leaderboard.js';
import errorHandler from './middleware/errorHandler.js';

const app = express();
const server = createServer(app);
const io = new Server(server, {
  cors: {
    origin: ['http://localhost:3000', 'http://localhost:5173'],
    methods: ['GET', 'POST']
  }
});

const PORT = process.env.PORT || 5000;

// ✅ Declare clients
let redisClient;
let subscriberClient;

// 🚀 START SERVER
const startServer = async () => {
  try {
    // ✅ MAIN REDIS CLIENT
    redisClient = createClient({
      url: process.env.REDIS_URL || 'redis://redis:6379'
    });

    redisClient.on('error', (err) => {
      console.error('Redis Error:', err);
    });

    await redisClient.connect();
    console.log('✅ Redis connected');

    // ✅ SEPARATE SUBSCRIBER CLIENT
    subscriberClient = redisClient.duplicate();
    await subscriberClient.connect();
    console.log('✅ Redis subscriber connected');

    // ✅ SUBSCRIPTIONS (correct way)
    await subscriberClient.subscribe('env:steps', (message) => {
      io.emit('env_step', JSON.parse(message));
    });

    await subscriberClient.subscribe('episodes:complete', (message) => {
      io.emit('episode_complete', JSON.parse(message));
    });

    // ✅ MongoDB
    await mongoose.connect(process.env.MONGO_URI);
    console.log('✅ MongoDB connected');

    // ✅ Middleware AFTER init
    app.use(cors({ origin: ['http://localhost:3000', 'http://localhost:5173'] }));
    app.use(express.json());

    app.use((req, _res, next) => {
      req.io = io;
      req.redis = redisClient;
      next();
    });

    // Routes
    app.use('/api/env', envRoutes);
    app.use('/api/episodes', episodeRoutes);
    app.use('/api/leaderboard', leaderboardRoutes);

    app.get('/health', (_req, res) => {
      res.json({ status: 'healthy', service: 'dashboard' });
    });

    app.use(errorHandler);

    // ✅ START SERVER LAST
    server.listen(PORT, () => {
      console.log(`🚀 Dashboard running on port ${PORT}`);
    });

    io.on('connection', (socket) => {
      console.log(`Client connected: ${socket.id}`);
    });

  } catch (err) {
    console.error('❌ Startup error:', err);
    process.exit(1);
  }
};

startServer();