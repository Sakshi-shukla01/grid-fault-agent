import { Router } from 'express';
import axios from 'axios';
import Episode from '../models/Episode.js';

const router  = Router();
const ENV_URL = process.env.ENV_BASE_URL || 'http://localhost:7860';

router.post('/reset', async (req, res, next) => {
  try {
    const { data } = await axios.post(`${ENV_URL}/reset`, req.body);
    req.io.emit('env_reset', data);
    res.json(data);
  } catch (err) {
    next({ status: 502, message: 'Python env unreachable', detail: err.message });
  }
});

router.post('/step', async (req, res, next) => {
  try {
    const { data } = await axios.post(`${ENV_URL}/step`, req.body);
    req.io.emit('env_step', data);

    if (data.done) {
      req.io.emit('episode_complete', data);

      const episode = await Episode.findOneAndUpdate(
        { episodeId: data.metadata?.episode_id },
        {
          $push: {
            steps: {
              stepNumber:  data.step_number,
              action:      req.body,
              observation: data,
              reward:      data.reward,
              feedback:    data.feedback
            }
          },
          $set: {
            finalScore:  data.metadata?.final_score  ?? 0,
            recall:      data.metadata?.recall        ?? 0,
            precision:   data.metadata?.precision     ?? 0,
            efficiency:  data.metadata?.efficiency    ?? 0,
            completed:   true
          }
        },
        { upsert: true, new: true }
      );

      req.io.emit('episode_saved', { episodeId: episode.episodeId });
    } else {
      await Episode.findOneAndUpdate(
        { episodeId: data.metadata?.episode_id },
        {
          $push: {
            steps: {
              stepNumber:  data.step_number,
              action:      req.body,
              observation: data,
              reward:      data.reward,
              feedback:    data.feedback
            }
          }
        },
        { upsert: true }
      );
    }

    res.json(data);
  } catch (err) {
    next({ status: 502, message: 'Python env unreachable', detail: err.message });
  }
});

router.get('/state', async (req, res, next) => {
  try {
    const { data } = await axios.get(`${ENV_URL}/state`);
    res.json(data);
  } catch (err) {
    next({ status: 502, message: 'Python env unreachable', detail: err.message });
  }
});

router.get('/health', async (req, res, next) => {
  try {
    const { data } = await axios.get(`${ENV_URL}/health`);
    res.json(data);
  } catch (err) {
    next({ status: 502, message: 'Python env unreachable', detail: err.message });
  }
});

export default router;