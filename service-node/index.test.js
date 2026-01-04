const request = require('supertest');
const app = require('./index');

describe('GET /', () => {
    it('should return 200 OK', async () => {
        const response = await request(app).get('/');
        expect(response.statusCode).toBe(200);
    });

    it('should return Hello from Node!', async () => {
        const response = await request(app).get('/');
        expect(response.text).toContain('Hello from Node!');
    });
});
