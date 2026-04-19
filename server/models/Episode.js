import mongoose from 'mongoose';

const StepSchema = new mongoose.Schema({
  stepNumber:  { type: Number,  required: true },
  action:      { type: Object,  required: true },
  observation: { type: Object,  required: true },
  reward:      { type: Number,  required: true },
  feedback:    { type: String,  default: '' },
  timestamp:   { type: Date,    default: Date.now }
});

const EpisodeSchema = new mongoose.Schema({
  episodeId:   { type: String,  required: true, unique: true },
  taskId:      { type: String,  required: true },
  difficulty:  { type: String,  enum: ['easy', 'medium', 'hard'], default: 'easy' },
  modelName:   { type: String,  required: true },
  steps:       [StepSchema],
  finalScore:  { type: Number,  default: 0 },
  recall:      { type: Number,  default: 0 },
  precision:   { type: Number,  default: 0 },
  efficiency:  { type: Number,  default: 0 },
  faultsFound: { type: Number,  default: 0 },
  totalFaults: { type: Number,  default: 0 },
  completed:   { type: Boolean, default: false },
  createdAt:   { type: Date,    default: Date.now }
});

const Episode = mongoose.model('Episode', EpisodeSchema);
export default Episode;