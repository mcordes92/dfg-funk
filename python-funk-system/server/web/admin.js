// API Base URL - use current origin instead of hardcoded localhost
const API_BASE = window.location.origin;

let currentEditUser = null;

// Get auth token
function getAuthToken() {
    return localStorage.getItem('admin_token');
}

// Get auth headers
function getAuthHeaders() {
    const token = getAuthToken();
    return {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${token}`
    };
}

// Check authentication
async function checkAuth() {
    const token = getAuthToken();
    if (!token) {
        window.location.href = '/static/login.html';
        return false;
    }
    
    try {
        const response = await fetch(`${API_BASE}/api/admin/verify`, {
            headers: {
                'Authorization': `Bearer ${token}`
            }
        });
        
        if (!response.ok) {
            localStorage.removeItem('admin_token');
            window.location.href = '/static/login.html';
            return false;
        }
        
        return true;
    } catch (error) {
        console.error('Auth check error:', error);
        window.location.href = '/static/login.html';
        return false;
    }
}

// Logout function
function logout() {
    const token = getAuthToken();
    
    if (token) {
        fetch(`${API_BASE}/api/admin/logout`, {
            method: 'POST',
            headers: {
                'Authorization': `Bearer ${token}`
            }
        }).catch(err => console.error('Logout error:', err));
    }
    
    localStorage.removeItem('admin_token');
    window.location.href = '/static/login.html';
}

// Initialize on page load
document.addEventListener('DOMContentLoaded', async () => {
    // Check authentication first
    const isAuth = await checkAuth();
    if (!isAuth) return;
    
    generateChannelCheckboxes();
    checkServerHealth();
    loadDashboard();
    
    // Auto-refresh every 10 seconds
    setInterval(() => {
        const activeTab = document.querySelector('.tab-pane.active').id;
        if (activeTab === 'dashboard') {
            loadDashboard();
        }
    }, 10000);
});

// Tab switching
function showTab(tabName) {
    // Update tab buttons
    document.querySelectorAll('.nav-tab').forEach(btn => btn.classList.remove('active'));
    event.target.classList.add('active');
    
    // Update tab content
    document.querySelectorAll('.tab-pane').forEach(pane => pane.classList.remove('active'));
    document.getElementById(tabName).classList.add('active');
    
    // Load data for the tab
    switch(tabName) {
        case 'dashboard':
            loadDashboard();
            break;
        case 'users':
            loadUsers();
            break;
        case 'channels':
            loadChannels();
            break;
        case 'logs':
            loadLogs();
            break;
        case 'stats':
            loadStats();
            break;
    }
}

// Check server health
async function checkServerHealth() {
    try {
        const response = await fetch(`${API_BASE}/health`);
        const data = await response.json();
        
        const badge = document.getElementById('statusBadge');
        if (data.status === 'healthy') {
            badge.className = 'status-badge online';
            badge.textContent = '● Server Online';
        } else {
            badge.className = 'status-badge';
            badge.textContent = '● Server Offline';
        }
    } catch (error) {
        const badge = document.getElementById('statusBadge');
        badge.className = 'status-badge';
        badge.textContent = '● Server Offline';
    }
}

// Load dashboard
async function loadDashboard() {
    try {
        // Load active users
        const activeUsersResponse = await fetch(`${API_BASE}/api/stats/active-users`, {
            headers: getAuthHeaders()
        });
        const activeUsersData = await activeUsersResponse.json();
        document.getElementById('activeUsersCount').textContent = activeUsersData.count || 0;
        
        // Load all users
        const usersResponse = await fetch(`${API_BASE}/api/admin/users`, {
            headers: getAuthHeaders()
        });
        const usersData = await usersResponse.json();
        document.getElementById('totalUsersCount').textContent = usersData.count || 0;
        
        // Load connection logs
        const logsResponse = await fetch(`${API_BASE}/api/logs/connections?limit=100`, {
            headers: getAuthHeaders()
        });
        const logsData = await logsResponse.json();
        document.getElementById('connectionsCount').textContent = logsData.count || 0;
        
        // Display active users table
        const tbody = document.querySelector('#activeUsersTable tbody');
        if (activeUsersData.active_users && activeUsersData.active_users.length > 0) {
            tbody.innerHTML = activeUsersData.active_users.map(user => `
                <tr>
                    <td><strong>${user.username}</strong></td>
                    <td>Kanal ${user.current_channel || 'N/A'}</td>
                    <td>${formatDate(user.last_seen)}</td>
                    <td>${user.allowed_channels ? user.allowed_channels.length : 0} Kanäle</td>
                </tr>
            `).join('');
        } else {
            tbody.innerHTML = '<tr><td colspan="4" style="text-align: center; color: #64748b;">Keine aktiven Benutzer</td></tr>';
        }
    } catch (error) {
        console.error('Error loading dashboard:', error);
        showAlert('Fehler beim Laden des Dashboards', 'error');
    }
}

// Load users
async function loadUsers() {
    try {
        const response = await fetch(`${API_BASE}/api/admin/users`, {
            headers: getAuthHeaders()
        });
        const data = await response.json();
        
        const tbody = document.querySelector('#usersTable tbody');
        if (data.users && data.users.length > 0) {
            tbody.innerHTML = data.users.map(user => `
                <tr>
                    <td>${user.id}</td>
                    <td><strong>${user.username}</strong></td>
                    <td>
                        <div class="funk-key-display" style="font-size: 0.85em;">
                            ${user.funk_key}
                        </div>
                    </td>
                    <td>${Array.isArray(user.allowed_channels) ? user.allowed_channels.join(', ') : user.allowed_channels}</td>
                    <td>
                        <span class="badge ${user.is_active ? 'badge-success' : 'badge-danger'}">
                            ${user.is_active ? 'Aktiv' : 'Inaktiv'}
                        </span>
                    </td>
                    <td>${formatDate(user.created_at)}</td>
                    <td class="actions">
                        <button class="btn btn-primary" onclick="editUser('${user.username}')">
                            ✏️ Bearbeiten
                        </button>
                        <button class="btn btn-danger" onclick="deleteUser('${user.username}')">
                            🗑️ Löschen
                        </button>
                    </td>
                </tr>
            `).join('');
        } else {
            tbody.innerHTML = '<tr><td colspan="7" style="text-align: center; color: #64748b;">Keine Benutzer vorhanden</td></tr>';
        }
    } catch (error) {
        console.error('Error loading users:', error);
        showAlert('Fehler beim Laden der Benutzer', 'error');
    }
}

// Load channels
async function loadChannels() {
    try {
        const response = await fetch(`${API_BASE}/api/stats/channel-usage`, {
            headers: getAuthHeaders()
        });
        const data = await response.json();
        
        const usageMap = {};
        if (data.channel_usage) {
            data.channel_usage.forEach(ch => {
                usageMap[ch.id] = ch;
            });
        }
        
        const tbody = document.querySelector('#channelsTable tbody');
        let html = '';
        // Public channels 41-43
        for (let i = 41; i <= 43; i++) {
            const usage = usageMap[i] || { unique_users: 0, total_connections: 0 };
            html += `
                <tr style="background: #e8f5e9;">
                    <td><strong>Kanal ${i}</strong></td>
                    <td>${usage.name || `Kanal ${i} (Allgemein)`} 📢</td>
                    <td>${usage.unique_users || 0}</td>
                    <td>${usage.total_connections || 0}</td>
                    <td>
                        <button onclick="sendTestTone(${i})" class="btn-secondary" title="Test-Ton senden">
                            🔊 Test
                        </button>
                    </td>
                </tr>
            `;
        }
        // Restricted channels 51-69
        for (let i = 51; i <= 69; i++) {
            const usage = usageMap[i] || { unique_users: 0, total_connections: 0 };
            html += `
                <tr>
                    <td><strong>Kanal ${i}</strong></td>
                    <td>${usage.name || `Kanal ${i}`} 🔒</td>
                    <td>${usage.unique_users || 0}</td>
                    <td>${usage.total_connections || 0}</td>
                    <td>
                        <button onclick="sendTestTone(${i})" class="btn-secondary" title="Test-Ton senden">
                            🔊 Test
                        </button>
                    </td>
                </tr>
            `;
        }
        tbody.innerHTML = html;
    } catch (error) {
        console.error('Error loading channels:', error);
        showAlert('Fehler beim Laden der Kanäle', 'error');
    }
}

// Load logs
async function loadLogs() {
    try {
        const response = await fetch(`${API_BASE}/api/logs/connections?limit=100`, {
            headers: getAuthHeaders()
        });
        const data = await response.json();
        
        const tbody = document.querySelector('#logsTable tbody');
        if (data.logs && data.logs.length > 0) {
            tbody.innerHTML = data.logs.map(log => `
                <tr>
                    <td>${formatDate(log.timestamp)}</td>
                    <td><strong>${log.username || 'N/A'}</strong></td>
                    <td>Kanal ${log.channel_id || 'N/A'}</td>
                    <td>
                        <span class="badge badge-success">
                            ${log.action}
                        </span>
                    </td>
                    <td>${log.ip_address || 'N/A'}</td>
                </tr>
            `).join('');
        } else {
            tbody.innerHTML = '<tr><td colspan="5" style="text-align: center; color: #64748b;">Keine Logs vorhanden</td></tr>';
        }
    } catch (error) {
        console.error('Error loading logs:', error);
        showAlert('Fehler beim Laden der Logs', 'error');
    }
}

// Load stats
async function loadStats() {
    try {
        const response = await fetch(`${API_BASE}/api/stats/traffic`, {
            headers: getAuthHeaders()
        });
        const data = await response.json();
        
        if (data.traffic) {
            // 24 hours
            document.getElementById('traffic_24h_in').textContent = data.traffic['24h'].bytes_in_formatted;
            document.getElementById('traffic_24h_out').textContent = data.traffic['24h'].bytes_out_formatted;
            
            // 7 days
            document.getElementById('traffic_7d_in').textContent = data.traffic['7d'].bytes_in_formatted;
            document.getElementById('traffic_7d_out').textContent = data.traffic['7d'].bytes_out_formatted;
            
            // 30 days
            document.getElementById('traffic_30d_in').textContent = data.traffic['30d'].bytes_in_formatted;
            document.getElementById('traffic_30d_out').textContent = data.traffic['30d'].bytes_out_formatted;
        }
    } catch (error) {
        console.error('Error loading stats:', error);
        showAlert('Fehler beim Laden der Statistiken', 'error');
    }
}

// Generate channel checkboxes
function generateChannelCheckboxes() {
    const container = document.getElementById('channelSelection');
    let html = '<div style="margin-bottom: 10px; font-weight: bold; color: #10b981;">📢 Öffentliche Kanäle</div>';
    // Public channels 41-43
    for (let i = 41; i <= 43; i++) {
        html += `
            <div class="channel-checkbox">
                <input type="checkbox" id="ch${i}" value="${i}">
                <label for="ch${i}">${i}</label>
            </div>
        `;
    }
    html += '<div style="grid-column: 1/-1; margin: 15px 0 10px 0; font-weight: bold; color: #667eea;">🔒 Private Kanäle</div>';
    // Restricted channels 51-69
    for (let i = 51; i <= 69; i++) {
        html += `
            <div class="channel-checkbox">
                <input type="checkbox" id="ch${i}" value="${i}">
                <label for="ch${i}">${i}</label>
            </div>
        `;
    }
    container.innerHTML = html;
}

// Show create user modal
function showCreateUserModal() {
    currentEditUser = null;
    document.getElementById('modalTitle').textContent = 'Neuer Benutzer';
    document.getElementById('userForm').reset();
    document.getElementById('isActive').value = 'true';
    
    // Uncheck all channels
    for (let i = 41; i <= 43; i++) {
        const checkbox = document.getElementById(`ch${i}`);
        if (checkbox) checkbox.checked = false;
    }
    for (let i = 51; i <= 69; i++) {
        const checkbox = document.getElementById(`ch${i}`);
        if (checkbox) checkbox.checked = false;
    }
    
    document.getElementById('userModal').classList.add('active');
}

// Edit user
async function editUser(username) {
    try {
        const response = await fetch(`${API_BASE}/api/admin/users/${username}`, {
            headers: getAuthHeaders()
        });
        const user = await response.json();
        
        currentEditUser = username;
        document.getElementById('modalTitle').textContent = 'Benutzer bearbeiten';
        document.getElementById('username').value = user.username;
        document.getElementById('username').disabled = true; // Can't change username
        document.getElementById('funkKey').value = user.funk_key;
        document.getElementById('isActive').value = user.is_active ? 'true' : 'false';
        
        // Check appropriate channels
        for (let i = 41; i <= 43; i++) {
            const checkbox = document.getElementById(`ch${i}`);
            if (checkbox) checkbox.checked = user.allowed_channels && user.allowed_channels.includes(i);
        }
        for (let i = 51; i <= 69; i++) {
            const checkbox = document.getElementById(`ch${i}`);
            if (checkbox) checkbox.checked = user.allowed_channels && user.allowed_channels.includes(i);
        }
        
        document.getElementById('userModal').classList.add('active');
    } catch (error) {
        console.error('Error loading user:', error);
        showAlert('Fehler beim Laden des Benutzers', 'error');
    }
}

// Save user (create or update)
async function saveUser(event) {
    event.preventDefault();
    
    const username = document.getElementById('username').value;
    const funkKey = document.getElementById('funkKey').value;
    const isActive = document.getElementById('isActive').value === 'true';
    
    // Get selected channels
    const allowedChannels = [];
    for (let i = 41; i <= 43; i++) {
        const checkbox = document.getElementById(`ch${i}`);
        if (checkbox && checkbox.checked) {
            allowedChannels.push(i);
        }
    }
    for (let i = 51; i <= 69; i++) {
        const checkbox = document.getElementById(`ch${i}`);
        if (checkbox && checkbox.checked) {
            allowedChannels.push(i);
        }
    }
    
    try {
        let response;
        if (currentEditUser) {
            // Update existing user
            response = await fetch(`${API_BASE}/api/admin/users/${currentEditUser}`, {
                method: 'PUT',
                headers: getAuthHeaders(),
                body: JSON.stringify({
                    allowed_channels: allowedChannels,
                    is_active: isActive
                })
            });
        } else {
            // Create new user
            response = await fetch(`${API_BASE}/api/admin/users`, {
                method: 'POST',
                headers: getAuthHeaders(),
                body: JSON.stringify({
                    username,
                    funk_key: funkKey,
                    allowed_channels: allowedChannels
                })
            });
        }
        
        if (response.ok) {
            showAlert(currentEditUser ? 'Benutzer aktualisiert' : 'Benutzer erstellt', 'success');
            closeModal('userModal');
            loadUsers();
            document.getElementById('username').disabled = false;
        } else {
            const error = await response.json();
            showAlert(error.detail || 'Fehler beim Speichern', 'error');
        }
    } catch (error) {
        console.error('Error saving user:', error);
        showAlert('Fehler beim Speichern des Benutzers', 'error');
    }
}

// Delete user
async function deleteUser(username) {
    if (!confirm(`Benutzer "${username}" wirklich löschen?`)) {
        return;
    }
    
    try {
        const response = await fetch(`${API_BASE}/api/admin/users/${username}`, {
            method: 'DELETE',
            headers: getAuthHeaders()
        });
        
        if (response.ok) {
            showAlert('Benutzer gelöscht', 'success');
            loadUsers();
        } else {
            const error = await response.json();
            showAlert(error.detail || 'Fehler beim Löschen', 'error');
        }
    } catch (error) {
        console.error('Error deleting user:', error);
        showAlert('Fehler beim Löschen des Benutzers', 'error');
    }
}

// Generate random funk key
function generateFunkKey() {
    const chars = '0123456789abcdef';
    let key = '';
    for (let i = 0; i < 32; i++) {
        key += chars[Math.floor(Math.random() * chars.length)];
    }
    document.getElementById('funkKey').value = key;
}

// Close modal
function closeModal(modalId) {
    document.getElementById(modalId).classList.remove('active');
}

// Show alert
function showAlert(message, type = 'success') {
    const container = document.getElementById('alertContainer');
    const alert = document.createElement('div');
    alert.className = `alert alert-${type} show`;
    alert.textContent = message;
    
    container.innerHTML = '';
    container.appendChild(alert);
    
    setTimeout(() => {
        alert.classList.remove('show');
        setTimeout(() => alert.remove(), 300);
    }, 5000);
}

// Format date
function formatDate(dateString) {
    if (!dateString) return 'N/A';
    const date = new Date(dateString);
    return date.toLocaleString('de-DE', {
        year: 'numeric',
        month: '2-digit',
        day: '2-digit',
        hour: '2-digit',
        minute: '2-digit',
        second: '2-digit'
    });
}

// Format bytes
function formatBytes(bytes) {
    if (bytes === 0) return '0 Bytes';
    const k = 1024;
    const sizes = ['Bytes', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return Math.round(bytes / Math.pow(k, i) * 100) / 100 + ' ' + sizes[i];
}

// Close modal when clicking outside
window.onclick = function(event) {
    if (event.target.classList.contains('modal')) {
        event.target.classList.remove('active');
    }
}

// ========================================
// UPDATE SYSTEM FUNCTIONS
// ========================================

// Load current version info
async function loadVersionInfo() {
    try {
        const response = await fetch(`${API_BASE}/api/admin/updates/info`, {
            headers: getAuthHeaders()
        });
        
        if (response.ok) {
            const data = await response.json();
            
            if (data.version_info) {
                document.getElementById('currentVersion').textContent = 'v' + data.version_info.version;
                
                const date = new Date(data.version_info.release_date);
                document.getElementById('versionDate').textContent = 
                    '📅 Veröffentlicht: ' + date.toLocaleDateString('de-DE') + ' um ' + date.toLocaleTimeString('de-DE');
                
                document.getElementById('versionSize').textContent = 
                    '💾 Größe: ' + formatBytes(data.version_info.file_size);
                
                document.getElementById('changelogDisplay').textContent = 
                    data.version_info.changelog || 'Kein Changelog verfügbar';
            } else {
                document.getElementById('currentVersion').textContent = 'Keine Version hochgeladen';
                document.getElementById('versionDate').textContent = '';
                document.getElementById('versionSize').textContent = '';
                document.getElementById('changelogDisplay').textContent = 'Kein Changelog verfügbar';
            }
        }
    } catch (error) {
        console.error('Error loading version info:', error);
    }
}

// Upload new client version
async function uploadUpdate(event) {
    event.preventDefault();
    
    const version = document.getElementById('updateVersion').value;
    const changelog = document.getElementById('updateChangelog').value;
    const fileInput = document.getElementById('updateFile');
    const file = fileInput.files[0];
    
    if (!file) {
        showAlert('Bitte wähle eine EXE-Datei aus', 'warning');
        return;
    }
    
    if (!file.name.endsWith('.exe')) {
        showAlert('Nur .exe Dateien sind erlaubt', 'error');
        return;
    }
    
    // Show progress
    const progressDiv = document.getElementById('uploadProgress');
    const progressBar = document.getElementById('progressBar');
    const uploadStatus = document.getElementById('uploadStatus');
    const uploadBtn = document.getElementById('uploadBtn');
    
    progressDiv.style.display = 'block';
    uploadBtn.disabled = true;
    uploadBtn.textContent = '⏳ Wird hochgeladen...';
    
    try {
        const formData = new FormData();
        formData.append('file', file);
        
        const xhr = new XMLHttpRequest();
        
        // Progress handler
        xhr.upload.addEventListener('progress', (e) => {
            if (e.lengthComputable) {
                const percent = Math.round((e.loaded / e.total) * 100);
                progressBar.style.width = percent + '%';
                progressBar.textContent = percent + '%';
                uploadStatus.textContent = `${formatBytes(e.loaded)} / ${formatBytes(e.total)}`;
            }
        });
        
        // Success handler
        xhr.addEventListener('load', () => {
            if (xhr.status === 200) {
                const response = JSON.parse(xhr.responseText);
                showAlert(`Version ${version} erfolgreich hochgeladen!`, 'success');
                
                // Reset form
                document.getElementById('uploadForm').reset();
                progressDiv.style.display = 'none';
                uploadBtn.disabled = false;
                uploadBtn.textContent = '📤 Version hochladen';
                
                // Reload version info
                loadVersionInfo();
            } else {
                const error = JSON.parse(xhr.responseText);
                showAlert('Fehler beim Upload: ' + (error.detail || 'Unbekannter Fehler'), 'error');
                progressDiv.style.display = 'none';
                uploadBtn.disabled = false;
                uploadBtn.textContent = '📤 Version hochladen';
            }
        });
        
        // Error handler
        xhr.addEventListener('error', () => {
            showAlert('Netzwerkfehler beim Upload', 'error');
            progressDiv.style.display = 'none';
            uploadBtn.disabled = false;
            uploadBtn.textContent = '📤 Version hochladen';
        });
        
        // Send request
        xhr.open('POST', `${API_BASE}/api/admin/updates/upload`);
        xhr.setRequestHeader('Authorization', `Bearer ${getAuthToken()}`);
        xhr.setRequestHeader('version', version);
        if (changelog) {
            xhr.setRequestHeader('changelog', changelog);
        }
        xhr.send(formData);
        
    } catch (error) {
        console.error('Upload error:', error);
        showAlert('Fehler beim Upload: ' + error.message, 'error');
        progressDiv.style.display = 'none';
        uploadBtn.disabled = false;
        uploadBtn.textContent = '📤 Version hochladen';
    }
}

// Send test tone to channel
async function sendTestTone(channelId) {
    try {
        const button = event.target;
        const originalText = button.innerHTML;
        button.disabled = true;
        button.innerHTML = '⏳ Sende...';
        
        const response = await fetch(`${API_BASE}/api/channels/${channelId}/test-tone`, {
            method: 'POST',
            headers: getAuthHeaders()
        });
        
        if (response.ok) {
            const data = await response.json();
            showAlert(`Test-Ton wird an ${data.channel_name} gesendet`, 'success');
            button.innerHTML = '✅ Gesendet';
            setTimeout(() => {
                button.disabled = false;
                button.innerHTML = originalText;
            }, 2000);
        } else {
            const error = await response.json();
            showAlert(error.detail || 'Fehler beim Senden', 'error');
            button.disabled = false;
            button.innerHTML = originalText;
        }
    } catch (error) {
        console.error('Error sending test tone:', error);
        showAlert('Fehler beim Senden des Test-Tons', 'error');
        event.target.disabled = false;
        event.target.innerHTML = '🔊 Test';
    }
}

// Show tab and load data
const originalShowTab = window.showTab;
window.showTab = function(tabName) {
    originalShowTab(tabName);
    
    if (tabName === 'updates') {
        loadVersionInfo();
    }
};
