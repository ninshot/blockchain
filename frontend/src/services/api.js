import axios from 'axios';

const API_BASE_URL = 'http://localhost:5002';

const api = axios.create({
    baseURL: API_BASE_URL,
    headers:{
        'Content-Type': 'application/json',
    },
});

export const createWallet = async () => {
    try{
        
        const response = await api.post('/wallet/create');
        
        return response.data;
    }catch (error) {
        console.error('Error creating wallet:', error);
        throw error;
    }
}
export default api;
//#022dd8