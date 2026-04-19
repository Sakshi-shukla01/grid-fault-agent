// server/testDb.js
require('dotenv').config();
const mongoose = require('mongoose');

async function testConnection() {
  try {
    console.log('Connecting to Atlas...');
    await mongoose.connect(process.env.MONGO_URI);
    console.log('SUCCESS: Connected to MongoDB Atlas!');
    console.log('DB name:', mongoose.connection.db.databaseName);
    await mongoose.disconnect();
    process.exit(0);
  } catch (err) {
    console.error('FAILED:', err.message);
    process.exit(1);
  }
}

testConnection();