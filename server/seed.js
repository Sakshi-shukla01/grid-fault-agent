import 'dotenv/config';
import mongoose from 'mongoose';
import Scenario from './models/Scenario.js';

const scenarios = [
  {
    scenarioId:  "radial_fault",
    name:        "Radial distribution fault",
    difficulty:  "easy",
    description: "14-bus radial grid. Single phase-to-ground fault on LINE_3_7 causes BUS_7 blackout. 6 planted faults.",
    totalFaults: 6,
    maxSteps:    10
  },
  {
    scenarioId:  "cascade_ring",
    name:        "Ring grid cascade",
    difficulty:  "medium",
    description: "20-bus ring grid. Relay maloperation triggers cascade trip of 3 healthy lines. 10 planted faults.",
    totalFaults: 10,
    maxSteps:    14
  },
  {
    scenarioId:  "storm_mesh",
    name:        "Storm event mesh grid",
    difficulty:  "hard",
    description: "30-bus mesh grid. Simultaneous storm faults across 3 zones + SCADA comms loss + capacitor bank failure. 25 planted faults.",
    totalFaults: 25,
    maxSteps:    20
  }
];

async function seed() {
  try {
    await mongoose.connect(process.env.MONGO_URI);
    console.log('Connected to Atlas');

    await Scenario.deleteMany({});
    const inserted = await Scenario.insertMany(scenarios);
    console.log(`Seeded ${inserted.length} scenarios`);

    for (const s of inserted) {
      console.log(`  ${s.scenarioId} — ${s.difficulty} — ${s.totalFaults} faults`);
    }

    await mongoose.disconnect();
    process.exit(0);
  } catch (err) {
    console.error('Seed failed:', err.message);
    process.exit(1);
  }
}

seed();