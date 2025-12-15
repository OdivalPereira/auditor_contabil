import React, { useState } from 'react';
import api from '../api/client';
import { Upload, FolderSearch, CheckCircle, AlertCircle } from 'lucide-react';

const UploadPage = () => {
    const [ledgerFile, setLedgerFile] = useState(null);
    const [bankFiles, setBankFiles] = useState([]);
    const [scanning, setScanning] = useState(false);
    const [folderPath, setFolderPath] = useState('');
    const [status, setStatus] = useState({ type: '', msg: '' });

    const handleLedgerUpload = async () => {
        if (!ledgerFile) return;
        const formData = new FormData();
        formData.append('file', ledgerFile);

        try {
            setStatus({ type: 'info', msg: 'Enviando Diário...' });
            await api.post('/upload/ledger', formData);
            setStatus({ type: 'success', msg: 'Livro Diário processado com sucesso!' });
        } catch (error) {
            setStatus({ type: 'error', msg: 'Erro ao enviar Diário.' });
        }
    };

    const handleBankUpload = async () => {
        if (bankFiles.length === 0) return;
        const formData = new FormData();
        Array.from(bankFiles).forEach(file => {
            formData.append('files', file);
        });

        try {
            setStatus({ type: 'info', msg: 'Enviando Extratos...' });
            await api.post('/upload/bank', formData);
            setStatus({ type: 'success', msg: 'Extratos bancários processados!' });
        } catch (error) {
            setStatus({ type: 'error', msg: 'Erro ao enviar Extratos.' });
        }
    };

    const handleScan = async () => {
        if (!folderPath) return;
        setScanning(true);
        try {
            const res = await api.post('/scan/', { path: folderPath });
            // For now, just auto-ingest found files or notify
            setStatus({ type: 'success', msg: `Encontrados ${res.data.files.length} arquivos. (Auto-ingestão pendente nesta demo)` });

            // Auto ingest logic could vary, for now let's assume we want to ingest them all
            const filePaths = res.data.files.map(f => f.path);
            if (filePaths.length > 0) {
                await api.post('/scan/ingest', filePaths);
                setStatus({ type: 'success', msg: `Escaneados e processados ${filePaths.length} arquivos com sucesso!` });
            }

        } catch (error) {
            setStatus({ type: 'error', msg: 'Erro ao escanear pasta.' });
        } finally {
            setScanning(false);
        }
    };

    return (
        <div className="glass-panel" style={{ padding: '30px' }}>
            <h2 style={{ marginBottom: '20px' }}>📂 Importação de Dados</h2>

            {status.msg && (
                <div style={{
                    padding: '15px',
                    borderRadius: '8px',
                    marginBottom: '20px',
                    backgroundColor: status.type === 'error' ? 'rgba(239, 68, 68, 0.2)' : 'rgba(16, 185, 129, 0.2)',
                    color: status.type === 'error' ? '#fca5a5' : '#6ee7b7',
                    border: `1px solid ${status.type === 'error' ? '#ef4444' : '#10b981'}`
                }}>
                    {status.type === 'error' ? <AlertCircle size={18} style={{ verticalAlign: 'middle', marginRight: 8 }} /> : <CheckCircle size={18} style={{ verticalAlign: 'middle', marginRight: 8 }} />}
                    {status.msg}
                </div>
            )}

            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '30px' }}>
                {/* Ledger Section */}
                <div style={{ background: 'rgba(0,0,0,0.2)', padding: '20px', borderRadius: '12px' }}>
                    <h3 style={{ marginTop: 0 }}>1. Livro Diário</h3>
                    <p style={{ color: 'var(--text-secondary)' }}>Upload do arquivo PDF ou CSV do sistema contábil.</p>

                    <input
                        type="file"
                        accept=".pdf,.csv"
                        onChange={(e) => setLedgerFile(e.target.files[0])}
                        style={{ margin: '15px 0', width: '100%' }}
                    />

                    <button
                        className="btn-primary"
                        onClick={handleLedgerUpload}
                        disabled={!ledgerFile}
                        style={{ width: '100%', opacity: !ledgerFile ? 0.5 : 1 }}
                    >
                        <Upload size={16} style={{ marginRight: 8 }} />
                        Processar Diário
                    </button>
                </div>

                {/* Bank Section */}
                <div style={{ background: 'rgba(0,0,0,0.2)', padding: '20px', borderRadius: '12px' }}>
                    <h3 style={{ marginTop: 0 }}>2. Extratos Bancários</h3>
                    <p style={{ color: 'var(--text-secondary)' }}>Upload de arquivos PDF ou OFX.</p>

                    <div style={{ marginBottom: '20px' }}>
                        <input
                            type="file"
                            multiple
                            accept=".pdf,.ofx"
                            onChange={(e) => setBankFiles(e.target.files)}
                            style={{ margin: '15px 0', width: '100%' }}
                        />
                        <button
                            className="btn-primary"
                            onClick={handleBankUpload}
                            disabled={!bankFiles.length}
                            style={{ width: '100%', opacity: !bankFiles.length ? 0.5 : 1 }}
                        >
                            <Upload size={16} style={{ marginRight: 8 }} />
                            Processar Extratos
                        </button>
                    </div>

                    <div style={{ borderTop: '1px solid rgba(255,255,255,0.1)', paddingTop: '15px' }}>
                        <h4 style={{ margin: '0 0 10px 0' }}>Ou Escanear Pasta Local</h4>
                        <div style={{ display: 'flex', gap: '10px' }}>
                            <input
                                type="text"
                                placeholder="C:\Caminho\Para\Extratos"
                                value={folderPath}
                                onChange={(e) => setFolderPath(e.target.value)}
                                style={{
                                    flex: 1,
                                    padding: '8px',
                                    borderRadius: '6px',
                                    border: '1px solid rgba(255,255,255,0.2)',
                                    background: 'rgba(0,0,0,0.3)',
                                    color: 'white'
                                }}
                            />
                            <button
                                className="btn-primary"
                                onClick={handleScan}
                                disabled={scanning || !folderPath}
                                style={{ padding: '8px 12px' }}
                            >
                                {scanning ? '...' : <FolderSearch size={18} />}
                            </button>
                        </div>
                    </div>
                </div>
            </div>
        </div>
    );
};

export default UploadPage;
