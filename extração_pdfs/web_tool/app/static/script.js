const dropZone = document.getElementById('drop-zone');
const fileInput = document.getElementById('file-input');
const browseBtn = document.getElementById('browse-btn');
const fileInfo = document.getElementById('file-info');
const filenameSpan = document.getElementById('filename');
const convertBtn = document.getElementById('convert-btn');
const statusDiv = document.getElementById('status');
const resultDiv = document.getElementById('result');
const downloadLink = document.getElementById('download-link');
const errorDiv = document.getElementById('error');
const errorMsg = document.querySelector('.error-msg');
const retryBtn = document.getElementById('retry-btn');
const resetBtn = document.getElementById('reset-btn');

let selectedFile = null;

// Drag & Drop
dropZone.addEventListener('dragover', (e) => {
    e.preventDefault();
    dropZone.classList.add('dragover');
});

dropZone.addEventListener('dragleave', () => {
    dropZone.classList.remove('dragover');
});

dropZone.addEventListener('drop', (e) => {
    e.preventDefault();
    dropZone.classList.remove('dragover');
    handleFile(e.dataTransfer.files[0]);
});

// Click to browse
browseBtn.addEventListener('click', () => fileInput.click());
fileInput.addEventListener('change', (e) => handleFile(e.target.files[0]));

const bankInput = document.getElementById('bank-id');
const branchInput = document.getElementById('branch-id');
const acctInput = document.getElementById('acct-id');

function handleFile(file) {
    if (file && file.type === 'application/pdf') {
        selectedFile = file;
        filenameSpan.textContent = file.name;
        dropZone.classList.add('hidden');
        fileInfo.classList.remove('hidden');
        errorDiv.classList.add('hidden');

        // Analyze file to pre-fill inputs
        analyzeFile(file);
    } else {
        showError('Por favor, selecione um arquivo PDF válido.');
    }
}

async function analyzeFile(file) {
    const formData = new FormData();
    formData.append('file', file);

    try {
        const response = await fetch('/analyze', {
            method: 'POST',
            body: formData
        });

        if (response.ok) {
            const data = await response.json();
            bankInput.value = data.bank_id || '';
            branchInput.value = data.branch_id || '';
            acctInput.value = data.acct_id || '';
        }
    } catch (e) {
        console.error("Analysis failed", e);
    }
}

// Convert
convertBtn.addEventListener('click', async () => {
    if (!selectedFile) return;

    fileInfo.classList.add('hidden');
    statusDiv.classList.remove('hidden');

    const formData = new FormData();
    formData.append('file', selectedFile);
    formData.append('bank_id', bankInput.value);
    formData.append('branch_id', branchInput.value);
    formData.append('acct_id', acctInput.value);

    try {
        const response = await fetch('/convert', {
            method: 'POST',
            body: formData
        });

        if (!response.ok) {
            const err = await response.json();
            throw new Error(err.detail || 'Erro na conversão');
        }

        const blob = await response.blob();
        const url = window.URL.createObjectURL(blob);
        const filename = selectedFile.name.replace('.pdf', '.ofx');

        downloadLink.href = url;
        downloadLink.download = filename;

        statusDiv.classList.add('hidden');
        resultDiv.classList.remove('hidden');

    } catch (err) {
        statusDiv.classList.add('hidden');
        showError(err.message);
    }
});

function showError(msg) {
    errorMsg.textContent = msg;
    errorDiv.classList.remove('hidden');
    dropZone.classList.add('hidden');
    fileInfo.classList.add('hidden');
}

// Reset
[retryBtn, resetBtn].forEach(btn => {
    btn.addEventListener('click', () => {
        selectedFile = null;
        fileInput.value = '';
        resultDiv.classList.add('hidden');
        errorDiv.classList.add('hidden');
        fileInfo.classList.add('hidden');
        dropZone.classList.remove('hidden');
    });
});
