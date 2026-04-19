import { Router } from 'express';
import Episode from '../models/Episode.js';

const router = Router();

router.post('/', async (req, res, next) => {
  try {
    const episode = new Episode(req.body);
    await episode.save();
    res.status(201).json(episode);
  } catch (err) {
    next({ status: 400, message: err.message });
  }
});

router.get('/', async (req, res, next) => {
  try {
    const { taskId, modelName, difficulty, limit = 20, page = 1 } = req.query;
    const filter = {};
    if (taskId)     filter.taskId     = taskId;
    if (modelName)  filter.modelName  = modelName;
    if (difficulty) filter.difficulty = difficulty;

    const skip = (parseInt(page) - 1) * parseInt(limit);

    const [episodes, total] = await Promise.all([
      Episode.find(filter)
        .sort({ createdAt: -1 })
        .skip(skip)
        .limit(parseInt(limit))
        .select('-steps'),
      Episode.countDocuments(filter)
    ]);

    res.json({ episodes, total, page: parseInt(page), limit: parseInt(limit) });
  } catch (err) {
    next({ status: 500, message: err.message });
  }
});

router.get('/:id', async (req, res, next) => {
  try {
    const episode = await Episode.findById(req.params.id);
    if (!episode) return res.status(404).json({ error: 'Episode not found' });
    res.json(episode);
  } catch (err) {
    next({ status: 500, message: err.message });
  }
});

router.delete('/:id', async (req, res, next) => {
  try {
    await Episode.findByIdAndDelete(req.params.id);
    res.json({ message: 'Deleted successfully' });
  } catch (err) {
    next({ status: 500, message: err.message });
  }
});

export default router;