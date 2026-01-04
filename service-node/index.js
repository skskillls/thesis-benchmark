const express = require('express');
const app = express();

app.get('/', (req, res) => res.send('Hello from Node!'));

// Only start server if this file is run directly (not imported for testing)
if (require.main === module) {
    app.listen(3000, () => console.log('Server ready on port 3000'));
}

module.exports = app;