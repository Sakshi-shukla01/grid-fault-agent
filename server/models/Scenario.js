import mongoose from 'mongoose';

const ScenarioSchema = new mongoose.Schema({
  scenarioId:   { type: String, required: true, unique: true },
  name:         { type: String, required: true },
  difficulty:   { type: String, enum: ['easy', 'medium', 'hard'] },
  description:  { type: String },
  totalFaults:  { type: Number },
  maxSteps:     { type: Number },
  createdAt:    { type: Date, default: Date.now }
});

const Scenario = mongoose.model('Scenario', ScenarioSchema);
export default Scenario;