// Global variables
let token = '';
const API_URL = window.location.origin;

// DOM Elements
const loginForm = document.getElementById('loginForm');
const dashboard = document.getElementById('dashboard');
const accountsTable = document.getElementById('accountsTable');
const transactionsTable = document.getElementById('transactionsTable');
const usersTable = document.getElementById('usersTable');
const saveAccountBtn = document.getElementById('saveAccountBtn');
const saveTransactionBtn = document.getElementById('saveTransactionBtn');
const saveUserBtn = document.getElementById('saveUserBtn');
const addEntryBtn = document.getElementById('addEntryBtn');

// Event Listeners
document.addEventListener('DOMContentLoaded', () => {
    // Check if token exists in localStorage
    const storedToken = localStorage.getItem('token');
    if (storedToken) {
        token = storedToken;
        showDashboard();
    }

    // Login form submission
    loginForm.addEventListener('submit', handleLogin);

    // Tab change events to load data
    document.getElementById('accounts-tab').addEventListener('click', loadAccounts);
    document.getElementById('transactions-tab').addEventListener('click', loadTransactions);
    document.getElementById('users-tab').addEventListener('click', loadUsers);

    // Logout button event
    document.getElementById('logout-btn').addEventListener('click', handleLogout);

    // Save buttons for modals
    saveAccountBtn.addEventListener('click', saveAccount);
    saveTransactionBtn.addEventListener('click', saveTransaction);
    saveUserBtn.addEventListener('click', saveUser);

    // Add entry button for transaction form
    addEntryBtn.addEventListener('click', addTransactionEntry);

    // Initial entry row event listeners
    setupEntryRowListeners(document.querySelector('.entry-row'));
});

// Authentication Functions
async function handleLogin(e) {
    e.preventDefault();

    const username = document.getElementById('username').value;
    const password = document.getElementById('password').value;

    try {
        const response = await fetch(`${API_URL}/auth/token`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/x-www-form-urlencoded',
            },
            body: new URLSearchParams({
                'username': username,
                'password': password,
            }),
        });

        console.log('Login response status:', response.status);

        if (!response.ok) {
            const errorData = await response.json().catch(() => ({}));
            console.error('Login error details:', errorData);
            throw new Error('Login failed: ' + (errorData.detail || 'Unknown error'));
        }

        const data = await response.json();
        console.log('Login successful, token received');
        token = data.access_token;

        // Save token to localStorage
        localStorage.setItem('token', token);

        // Show dashboard and load accounts
        showDashboard();
    } catch (error) {
        console.error('Login error:', error);
        showToast('Login failed. Please check your credentials.', 'error');
    }
}

async function handleLogout() {
    try {
        // Call the logout endpoint
        await fetch(`${API_URL}/auth/logout`, {
            method: 'POST',
            headers: {
                'Authorization': `Bearer ${token}`,
                'Content-Type': 'application/json',
            },
        });
        
        // Clear token from localStorage
        localStorage.removeItem('token');
        token = '';
        
        // Redirect to login page
        window.location.reload();
        showToast('Logged out successfully', 'success');
    } catch (error) {
        console.error('Logout error:', error);
        // Even if the server request fails, we should still log out locally
        localStorage.removeItem('token');
        token = '';
        window.location.reload();
    }
}

function showDashboard() {
    loginForm.closest('.card').style.display = 'none';
    dashboard.style.display = 'block';
    loadAccounts();
}

// API Request Helper
async function apiRequest(endpoint, method = 'GET', body = null) {
    const headers = {
        'Authorization': `Bearer ${token}`,
        'Content-Type': 'application/json',
    };

    const options = {
        method,
        headers,
    };

    if (body && (method === 'POST' || method === 'PUT')) {
        options.body = JSON.stringify(body);
    }

    try {
        const response = await fetch(`${API_URL}${endpoint}`, options);

        if (response.status === 401) {
            // Token expired or invalid
            localStorage.removeItem('token');
            window.location.reload();
            return null;
        }

        if (!response.ok) {
            const errorData = await response.json();
            throw new Error(errorData.detail || 'API request failed');
        }

        if (response.status === 204) {
            return true; // No content but successful
        }

        return await response.json();
    } catch (error) {
        showToast(error.message, 'error');
        return null;
    }
}

// Account Functions
async function loadAccounts() {
    accountsTable.innerHTML = '<tr><td colspan="6" class="text-center">Loading...</td></tr>';

    const accounts = await apiRequest('/accounts/');

    if (accounts) {
        accountsTable.innerHTML = '';

        accounts.forEach(account => {
            const row = document.createElement('tr');

            const balanceClass = parseFloat(account.balance) >= 0 ? 'balance-positive' : 'balance-negative';

            row.innerHTML = `
                <td>${account.id}</td>
                <td>${account.name}</td>
                <td>${account.account_type}</td>
                <td>${account.description || '-'}</td>
                <td class="${balanceClass}">${formatCurrency(account.balance)}</td>
                <td>
                    <button class="btn btn-sm btn-info view-account" data-id="${account.id}">View</button>
                    <button class="btn btn-sm btn-danger delete-account" data-id="${account.id}">Delete</button>
                </td>
            `;

            accountsTable.appendChild(row);
        });

        // Add event listeners to buttons
        document.querySelectorAll('.delete-account').forEach(btn => {
            btn.addEventListener('click', (e) => deleteAccount(e.target.dataset.id));
        });

        // Also update account selects in transaction modal
        updateAccountSelects();
    }
}

async function saveAccount() {
    const name = document.getElementById('accountName').value;
    const account_type = document.getElementById('accountType').value;
    const description = document.getElementById('accountDescription').value;

    const accountData = {
        name,
        account_type,
        description
    };

    const result = await apiRequest('/accounts/', 'POST', accountData);

    if (result) {
        showToast('Account created successfully!', 'success');
        loadAccounts();

        // Close modal and reset form
        const modal = bootstrap.Modal.getInstance(document.getElementById('addAccountModal'));
        modal.hide();
        document.getElementById('addAccountForm').reset();
    }
}

async function deleteAccount(id) {
    if (confirm('Are you sure you want to delete this account?')) {
        const result = await apiRequest(`/accounts/${id}`, 'DELETE');

        if (result) {
            showToast('Account deleted successfully!', 'success');
            loadAccounts();
        }
    }
}

// Transaction Functions
async function loadTransactions() {
    transactionsTable.innerHTML = '<tr><td colspan="6" class="text-center">Loading...</td></tr>';

    const transactions = await apiRequest('/transactions/');

    if (transactions) {
        transactionsTable.innerHTML = '';

        transactions.forEach(transaction => {
            const row = document.createElement('tr');

            // Calculate total amount (sum of all entries)
            let totalAmount = 0;
            transaction.entries.forEach(entry => {
                if (entry.entry_type === 'debit') {
                    totalAmount += parseFloat(entry.amount);
                }
            });

            row.innerHTML = `
                <td>${transaction.id}</td>
                <td>${transaction.reference_number}</td>
                <td>${transaction.description || '-'}</td>
                <td>${formatDate(transaction.date)}</td>
                <td>${formatCurrency(totalAmount)}</td>
                <td>
                    <button class="btn btn-sm btn-info view-transaction" data-id="${transaction.id}">View</button>
                    <button class="btn btn-sm btn-danger delete-transaction" data-id="${transaction.id}">Delete</button>
                </td>
            `;

            transactionsTable.appendChild(row);
        });

        // Add event listeners to buttons
        document.querySelectorAll('.delete-transaction').forEach(btn => {
            btn.addEventListener('click', (e) => deleteTransaction(e.target.dataset.id));
        });
    }
}

async function saveTransaction() {
    const reference_number = document.getElementById('transactionReference').value;
    const description = document.getElementById('transactionDescription').value;
    const date = document.getElementById('transactionDate').value;

    // Get entries
    const entryRows = document.querySelectorAll('.entry-row');
    const entries = [];

    let totalDebit = 0;
    let totalCredit = 0;

    entryRows.forEach(row => {
        const accountId = row.querySelector('.account-select').value;
        const entryType = row.querySelector('.entry-type').value;
        const amount = parseFloat(row.querySelector('.entry-amount').value);

        if (accountId && amount > 0) {
            entries.push({
                account_id: parseInt(accountId),
                entry_type: entryType,
                amount: amount
            });

            if (entryType === 'debit') {
                totalDebit += amount;
            } else {
                totalCredit += amount;
            }
        }
    });

    // Validate double-entry bookkeeping
    if (Math.abs(totalDebit - totalCredit) > 0.001) {
        showToast('Total debits must equal total credits for double-entry bookkeeping.', 'error');
        return;
    }

    if (entries.length < 2) {
        showToast('A transaction must have at least two entries.', 'error');
        return;
    }

    const transactionData = {
        reference_number,
        description,
        date,
        entries
    };

    const result = await apiRequest('/transactions/', 'POST', transactionData);

    if (result) {
        showToast('Transaction created successfully!', 'success');
        loadTransactions();

        // Close modal and reset form
        const modal = bootstrap.Modal.getInstance(document.getElementById('addTransactionModal'));
        modal.hide();
        document.getElementById('addTransactionForm').reset();

        // Reset entries to just one
        const entriesContainer = document.getElementById('entriesContainer');
        entriesContainer.innerHTML = '';
        addTransactionEntry();
    }
}

async function deleteTransaction(id) {
    if (confirm('Are you sure you want to delete this transaction?')) {
        const result = await apiRequest(`/transactions/${id}`, 'DELETE');

        if (result) {
            showToast('Transaction deleted successfully!', 'success');
            loadTransactions();
        }
    }
}

function addTransactionEntry() {
    const entriesContainer = document.getElementById('entriesContainer');

    const entryRow = document.createElement('div');
    entryRow.className = 'row entry-row mb-2';

    entryRow.innerHTML = `
        <div class="col-md-4">
            <select class="form-control account-select" required>
                <option value="">Select Account</option>
                <!-- Accounts will be loaded here -->
            </select>
        </div>
        <div class="col-md-3">
            <select class="form-control entry-type" required>
                <option value="debit">Debit</option>
                <option value="credit">Credit</option>
            </select>
        </div>
        <div class="col-md-3">
            <input type="number" class="form-control entry-amount" placeholder="Amount" required>
        </div>
        <div class="col-md-2">
            <button type="button" class="btn btn-danger btn-sm remove-entry">Remove</button>
        </div>
    `;

    entriesContainer.appendChild(entryRow);

    // Setup event listeners for the new row
    setupEntryRowListeners(entryRow);

    // Update account options
    updateAccountSelects();
}

function setupEntryRowListeners(row) {
    const removeBtn = row.querySelector('.remove-entry');
    if (removeBtn) {
        removeBtn.addEventListener('click', function() {
            // Only remove if there's more than one entry
            if (document.querySelectorAll('.entry-row').length > 1) {
                row.remove();
            } else {
                showToast('At least one entry is required.', 'error');
            }
        });
    }
}

async function updateAccountSelects() {
    const accounts = await apiRequest('/accounts/');

    if (accounts) {
        const accountSelects = document.querySelectorAll('.account-select');

        accountSelects.forEach(select => {
            // Save current value
            const currentValue = select.value;

            // Clear options except the first one
            select.innerHTML = '<option value="">Select Account</option>';

            // Add account options
            accounts.forEach(account => {
                const option = document.createElement('option');
                option.value = account.id;
                option.textContent = `${account.name} (${account.account_type})`;
                select.appendChild(option);
            });

            // Restore selected value if it exists
            if (currentValue) {
                select.value = currentValue;
            }
        });
    }
}

// User Functions
async function loadUsers() {
    usersTable.innerHTML = '<tr><td colspan="4" class="text-center">Loading...</td></tr>';

    try {
        // First get current user info
        const currentUser = await apiRequest('/users/me');
        
        if (currentUser) {
            usersTable.innerHTML = '';
            
            const row = document.createElement('tr');
            row.innerHTML = `
                <td>${currentUser.id}</td>
                <td>${currentUser.username}</td>
                <td>${currentUser.email}</td>
                <td>
                    <button class="btn btn-sm btn-info view-user" data-id="${currentUser.id}">View</button>
                </td>
            `;
            
            usersTable.appendChild(row);
        }
    } catch (error) {
        console.error('Error loading users:', error);
        usersTable.innerHTML = '<tr><td colspan="4" class="text-center text-danger">Error loading user data</td></tr>';
    }
}

async function saveUser() {
    const username = document.getElementById('userName').value;
    const email = document.getElementById('userEmail').value;
    const password = document.getElementById('userPassword').value;

    const userData = {
        username,
        email,
        password
    };

    const result = await apiRequest('/users/', 'POST', userData);

    if (result) {
        showToast('User created successfully!', 'success');
        loadUsers();

        // Close modal and reset form
        const modal = bootstrap.Modal.getInstance(document.getElementById('addUserModal'));
        modal.hide();
        document.getElementById('addUserForm').reset();
    }
}

// Utility Functions
function formatCurrency(amount) {
    return new Intl.NumberFormat('en-US', {
        style: 'currency',
        currency: 'USD'
    }).format(amount);
}

function formatDate(dateString) {
    const date = new Date(dateString);
    return date.toLocaleDateString();
}

function showToast(message, type = 'info') {
    // Create toast container if it doesn't exist
    let toastContainer = document.querySelector('.toast-container');
    if (!toastContainer) {
        toastContainer = document.createElement('div');
        toastContainer.className = 'toast-container';
        document.body.appendChild(toastContainer);
    }

    // Create toast element
    const toastEl = document.createElement('div');
    toastEl.className = `toast ${type === 'error' ? 'toast-error' : type === 'success' ? 'toast-success' : ''}`;
    toastEl.setAttribute('role', 'alert');
    toastEl.setAttribute('aria-live', 'assertive');
    toastEl.setAttribute('aria-atomic', 'true');

    toastEl.innerHTML = `
        <div class="toast-header">
            <strong class="me-auto">${type === 'error' ? 'Error' : 'Notification'}</strong>
            <button type="button" class="btn-close" data-bs-dismiss="toast" aria-label="Close"></button>
        </div>
        <div class="toast-body">
            ${message}
        </div>
    `;

    toastContainer.appendChild(toastEl);

    // Initialize and show the toast
    const toast = new bootstrap.Toast(toastEl, {
        autohide: true,
        delay: 5000
    });
    toast.show();

    // Remove toast after it's hidden
    toastEl.addEventListener('hidden.bs.toast', function() {
        toastEl.remove();
    });
}
