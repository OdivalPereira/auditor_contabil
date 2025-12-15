import axios from 'axios';

const api = axios.create({
    baseURL: '/api', // Proxy handles request to http://127.0.0.1:8000
});

export default api;
