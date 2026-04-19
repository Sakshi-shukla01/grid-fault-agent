import { Router } from 'express';
import Episode from '../models/Episode.js';

const router = Router();

router.get('/', async (req, res, next) => {
  try {
    const { taskId, difficulty } = req.query;
    const match = { completed: true };
    if (taskId)     match.taskId     = taskId;
    if (difficulty) match.difficulty = difficulty;

    const board = await Episode.aggregate([
      { $match: match },
      {
        $group: {
          _id:          '$modelName',
          avgScore:     { $avg: '$finalScore' },
          avgRecall:    { $avg: '$recall' },
          avgPrecision: { $avg: '$precision' },
          avgEfficiency:{ $avg: '$efficiency' },
          bestScore:    { $max: '$finalScore' },
          totalRuns:    { $sum: 1 }
        }
      },
      { $sort: { avgScore: -1 } },
      { $limit: 20 },
      {
        $project: {
          _id:          0,
          modelName:    '$_id',
          avgScore:     { $round: ['$avgScore',    3] },
          avgRecall:    { $round: ['$avgRecall',   3] },
          avgPrecision: { $round: ['$avgPrecision',3] },
          avgEfficiency:{ $round: ['$avgEfficiency',3] },
          bestScore:    { $round: ['$bestScore',   3] },
          totalRuns:    1
        }
      }
    ]);

    res.json(board);
  } catch (err) {
    next({ status: 500, message: err.message });
  }
});

export default router;