// common.js - общие функции

const API_BASE = '/api';

function showToast(message, type = 'error') {
    const toast = document.createElement('div');
    toast.className = `toast toast-${type}`;
    toast.textContent = message;
    document.body.appendChild(toast);
    setTimeout(() => toast.remove(), 3000);
}

function saveToken(token) {
    localStorage.setItem('token', token);
}
function getToken() {
    return localStorage.getItem('token');
}

function saveRole(role) {
    localStorage.setItem('role', role ? role.toUpperCase() : '');
}

function getRole() {
    return localStorage.getItem('role');
}

function logout() {
    localStorage.removeItem('token');
    localStorage.removeItem('role');
    window.location.href = '/login/'
}