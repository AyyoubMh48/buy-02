const dbName = process.env.MONGO_DATABASE;
const username = process.env.MONGO_USERNAME;
const password = process.env.MONGO_PASSWORD;

if (dbName && username && password) {
  const targetDb = db.getSiblingDB(dbName);
  const existingUser = targetDb.getUser(username);

  if (!existingUser) {
    targetDb.createUser({
      user: username,
      pwd: password,
      roles: [
        { role: 'readWrite', db: dbName },
        { role: 'dbAdmin', db: dbName }
      ]
    });
  }
}
