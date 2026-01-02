const API_URL = "http://127.0.0.1:8000";

document.addEventListener('DOMContentLoaded', async () => {
    // Check local storage for session
    const stored = await chrome.storage.local.get("email");

    if (stored && stored.email) {
        showStatus(stored.email);
    } else {
        showLogin();
    }

    document.getElementById('loginBtn').addEventListener('click', handleLogin);
    document.getElementById('toggleBtn').addEventListener('click', handleToggle);
    document.getElementById('logout').addEventListener('click', handleLogout);
    document.getElementById('saveSettings').addEventListener('click', handleSettings);

    document.getElementById('helpLink').addEventListener('click', () => {
        chrome.tabs.create({ url: "https://myaccount.google.com/apppasswords" });
    });
});

async function handleSettings() {
    const stored = await chrome.storage.local.get("email");
    if (!stored.email) return;

    const interval = parseInt(document.getElementById('intervalSelect').value);

    setLoading(true);
    try {
        const res = await fetch(`${API_URL}/settings`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ email: stored.email, interval: interval })
        });
        if (res.ok) {
            showMessage("Settings saved!");
            showStatus(stored.email); // Refresh view
        } else {
            const err = await res.json();
            showMessage(err.detail || "Failed to save settings.");
        }
    } catch (e) {
        showMessage("Failed to save settings.");
    } finally {
        setLoading(false);
    }
}

async function handleLogin() {
    const email = document.getElementById('email').value.trim();
    const appPass = document.getElementById('app_password').value.trim().replace(/\s/g, '');
    const apiKey = document.getElementById('api_key').value.trim();

    if (!email || !appPass || !apiKey) {
        showMessage("Please fill all fields.");
        return;
    }

    setLoading(true);
    try {
        const res = await fetch(`${API_URL}/login`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                email: email,
                app_password: appPass,
                openrouter_key: apiKey
            })
        });

        const data = await res.json();

        if (res.ok) {
            await chrome.storage.local.set({ email: email });
            showStatus(email);
        } else {
            showMessage(data.detail || "Login failed. Check credentials.");
        }
    } catch (err) {
        showMessage("Could not connect to backend server. Make sure python main.py is running.");
    } finally {
        setLoading(false);
    }
}

async function handleToggle() {
    const stored = await chrome.storage.local.get("email");
    if (!stored.email) return;

    const btn = document.getElementById('toggleBtn');
    // If it currently says "Stop", we want to stop (active=false)
    // If it says "Start", we want to start (active=true)
    const isCurrentlyRunning = btn.innerText.includes("Stop");
    const newState = !isCurrentlyRunning;

    setLoading(true);
    try {
        const res = await fetch(`${API_URL}/toggle`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ email: stored.email, active: newState })
        });
        if (res.ok) {
            // Re-fetch full status to update timers and UI correctly
            showStatus(stored.email);
        } else if (res.status === 404) {
            // User deleted from server, force re-login
            showMessage("Session expired. Please login again.");
            await handleLogout();
        } else {
            const err = await res.json();
            showMessage(err.detail || "Error toggling state");
        }
    } catch (err) {
        showMessage("Server connection failed.");
    } finally {
        setLoading(false);
    }
}

async function handleLogout() {
    await chrome.storage.local.remove("email");
    showLogin();
}

async function showStatus(email) {
    document.getElementById('loginForm').style.display = 'none';
    document.getElementById('statusCard').style.display = 'block';
    document.getElementById('userDisplay').innerText = email;

    // Fetch current status
    try {
        const res = await fetch(`${API_URL}/status?email=${encodeURIComponent(email)}`, { method: 'POST' });
        if (res.status === 404) {
            // Invalid session
            console.log("User not found on server, logging out.");
            await handleLogout();
            return;
        }
        const data = await res.json();
        updateStatusUI(data);
    } catch (e) {
        document.getElementById('statusText').innerText = "Server Disconnected";
    }
}

function updateStatusUI(data) {
    const isActive = data.active;
    const statusText = document.getElementById('statusText');
    const btn = document.getElementById('toggleBtn');

    // Update Timers
    document.getElementById('lastRun').innerText = data.last_run ? new Date(data.last_run).toLocaleTimeString() : "Never";
    document.getElementById('nextRun').innerText = data.next_run || "--";
    document.getElementById('intervalSelect').value = data.interval || 30;

    if (isActive) {
        statusText.innerHTML = '<span class="status-active">● RUNNING</span>';
        btn.innerText = "Stop Agent";
        btn.style.backgroundColor = "#dc3545";
    } else {
        statusText.innerHTML = '<span class="status-inactive">● STOPPED</span>';
        btn.innerText = "Start Agent";
        btn.style.backgroundColor = "#198754";
    }
}

function showLogin() {
    document.getElementById('loginForm').style.display = 'flex';
    document.getElementById('statusCard').style.display = 'none';
    document.getElementById('email').value = '';
    document.getElementById('app_password').value = '';
    document.getElementById('api_key').value = '';
    showMessage("");
}

function setLoading(isLoading) {
    document.getElementById('spinner').style.display = isLoading ? 'block' : 'none';
    document.getElementById('message').innerText = "";
}

function showMessage(msg) {
    document.getElementById('message').innerText = msg;
}
