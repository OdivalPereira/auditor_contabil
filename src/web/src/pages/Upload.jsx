import React, { useState } from 'react';
import api from '../api/client';
import { Upload, FolderSearch, CheckCircle, AlertCircle, FolderOpen, MousePointer2, FileSpreadsheet, File as FileIcon } from 'lucide-react';

const UploadPage = () => {
    const [ledgerFile, setLedgerFile] = useState(null);
    const [bankFiles, setBankFiles] = useState([]);
    const [dragActive, setDragActive] = useState({ ledger: false, bank: false });

    // Scan State
    const [scanning, setScanning] = useState(false);
    const [folderPath, setFolderPath] = useState('');
    const [scannedFiles, setScannedFiles] = useState([]); // List of found files
    const [selectedScanFiles, setSelectedScanFiles] = useState([]); // List of paths to ingest

    // Global Status
    const [status, setStatus] = useState({ type: '', msg: '' });

    // --- Drag & Drop Handlers ---
    const handleDrag = (e, type, active) => {
        e.preventDefault();
        e.stopPropagation();
        setDragActive(prev => ({ ...prev, [type]: active }));
    };

    const handleDrop = (e, type) => {
        e.preventDefault();
        e.stopPropagation();
        setDragActive(prev => ({ ...prev, [type]: false }));

        if (e.dataTransfer.files && e.dataTransfer.files.length > 0) {
            if (type === 'ledger') {
                setLedgerFile(e.dataTransfer.files[0]);
            } else if (type === 'bank') {
                setBankFiles(prev => [...prev, ...Array.from(e.dataTransfer.files)]);
            }
        }
    };

    const handleLedgerUpload = async () => {
        if (!ledgerFile) return;
        const formData = new FormData();
        formData.append('file', ledgerFile);

        try {
            setStatus({ type: 'info', msg: 'Enviando Diário...' });
            await api.post('/upload/ledger', formData);
            setStatus({ type: 'success', msg: 'Livro Diário processado com sucesso!' });
        } catch (error) {
            console.error(error);
            const msg = error.response?.data?.detail || 'Erro ao enviar Diário.';
            setStatus({ type: 'error', msg: msg });
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
            console.error(error);
            const msg = error.response?.data?.detail || 'Erro ao enviar Extratos.';
            setStatus({ type: 'error', msg: msg });
        }
    };

    const handleBrowseRequest = async () => {
        try {
            const res = await api.post('/scan/browse');
            if (res.data.path) {
                setFolderPath(res.data.path);
            }
        } catch (e) {
            console.error(e);
            setStatus({ type: 'error', msg: 'Não foi possível abrir o seletor. Digite o caminho manualmente.' });
        }
    };

    const handleScan = async () => {
        if (!folderPath) return;
        setScanning(true);
        setStatus({ type: 'info', msg: 'Escaneando pasta...' });
        try {
            const res = await api.post('/scan/', { path: folderPath });
            const files = res.data.files || [];
            if (files.length > 0) {
                setScannedFiles(files);
                // Auto-select all by default
                setSelectedScanFiles(files.map(f => f.path));
                setStatus({
                    type: 'success',
                    msg: `Encontrados ${files.length} arquivos. Selecione abaixo quais deseja importar.`
                });
            } else {
                setScannedFiles([]);
                setStatus({ type: 'info', msg: 'Nenhum arquivo compatível encontrado na pasta.' });
            }
        } catch (error) {
            setStatus({ type: 'error', msg: 'Erro ao escanear pasta.' });
        } finally {
            setScanning(false);
        }
    };

    const toggleScanFile = (path) => {
        setSelectedScanFiles(prev =>
            prev.includes(path) ? prev.filter(p => p !== path) : [...prev, path]
        );
    };

    const handleIngestSelected = async () => {
        if (selectedScanFiles.length === 0) return;

        setStatus({ type: 'info', msg: `Importando ${selectedScanFiles.length} arquivos...` });
        try {
            const ingestRes = await api.post('/scan/ingest', selectedScanFiles);
            setStatus({
                type: 'success',
                msg: `Sucesso! ${ingestRes.data.count} transações carregadas.`
            });
            // Clear selection or keep? Keep shows success.
        } catch (error) {
            setStatus({ type: 'error', msg: 'Erro ao importar arquivos selecionados.' });
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

            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '30px', marginBottom: 30 }}>
                {/* Ledger Section with DnD */}
                <div
                    style={{
                        background: dragActive.ledger ? 'rgba(99, 102, 241, 0.2)' : 'rgba(0,0,0,0.2)',
                        padding: '20px',
                        borderRadius: '12px',
                        border: dragActive.ledger ? '2px dashed #6366f1' : '2px dashed transparent',
                        transition: 'all 0.2s'
                    }}
                    onDragEnter={(e) => handleDrag(e, 'ledger', true)}
                    onDragLeave={(e) => handleDrag(e, 'ledger', false)}
                    onDragOver={(e) => handleDrag(e, 'ledger', true)}
                    onDrop={(e) => handleDrop(e, 'ledger')}
                >
                    <h3 style={{ marginTop: 0 }}>1. Livro Diário</h3>
                    <p style={{ color: 'var(--text-secondary)' }}>Arraste o PDF ou CSV aqui.</p>

                    <div style={{ textAlign: 'center', margin: '30px 0', opacity: 0.6 }}>
                        <FileSpreadsheet size={48} />
                    </div>

                    <input
                        type="file"
                        accept=".pdf,.csv"
                        id="ledger-input"
                        onChange={(e) => setLedgerFile(e.target.files[0])}
                        style={{ display: 'none' }}
                    />
                    <label htmlFor="ledger-input" className="btn-primary" style={{ display: 'block', textAlign: 'center', marginBottom: 10, background: 'rgba(255,255,255,0.1)' }}>
                        {ledgerFile ? 'Trocar Arquivo' : 'Selecionar Arquivo'}
                    </label>

                    <button
                        className="btn-primary"
                        onClick={handleLedgerUpload}
                        disabled={!ledgerFile}
                        style={{ width: '100%', opacity: !ledgerFile ? 0.5 : 1 }}
                    >
                        <Upload size={16} style={{ marginRight: 8 }} />
                        Processar Diário
                    </button>

                    {ledgerFile && <div style={{ marginTop: 10, fontSize: '0.9rem', color: '#10b981' }}><CheckCircle size={14} style={{ verticalAlign: -2 }} /> {ledgerFile.name}</div>}
                </div>

                {/* Bank Section with DnD */}
                <div
                    style={{
                        background: dragActive.bank ? 'rgba(16, 185, 129, 0.2)' : 'rgba(0,0,0,0.2)',
                        padding: '20px',
                        borderRadius: '12px',
                        border: dragActive.bank ? '2px dashed #10b981' : '2px dashed transparent',
                        transition: 'all 0.2s'
                    }}
                    onDragEnter={(e) => handleDrag(e, 'bank', true)}
                    onDragLeave={(e) => handleDrag(e, 'bank', false)}
                    onDragOver={(e) => handleDrag(e, 'bank', true)}
                    onDrop={(e) => handleDrop(e, 'bank')}
                >
                    <h3 style={{ marginTop: 0 }}>2. Extratos Bancários</h3>
                    <p style={{ color: 'var(--text-secondary)' }}>Arraste vários PDFs ou OFXs aqui.</p>

                    <div style={{ textAlign: 'center', margin: '30px 0', opacity: 0.6 }}>
                        <FileIcon size={48} />
                    </div>

                    <input
                        type="file"
                        multiple
                        accept=".pdf,.ofx"
                        id="bank-input"
                        onChange={(e) => setBankFiles(prev => [...prev, ...Array.from(e.target.files)])}
                        style={{ display: 'none' }}
                    />
                    <label htmlFor="bank-input" className="btn-primary" style={{ display: 'block', textAlign: 'center', marginBottom: 10, background: 'rgba(255,255,255,0.1)' }}>
                        Adicionar Arquivos...
                    </label>

                    {bankFiles.length > 0 && (
                        <div style={{ marginBottom: 10, maxHeight: 100, overflowY: 'auto', fontSize: '0.85rem', color: '#94a3b8', background: 'rgba(0,0,0,0.2)', padding: 5, borderRadius: 4 }}>
                            {bankFiles.map((f, i) => <div key={i}>{f.name}</div>)}
                        </div>
                    )}

                    <button
                        className="btn-primary"
                        onClick={handleBankUpload}
                        disabled={!bankFiles.length}
                        style={{ width: '100%', opacity: !bankFiles.length ? 0.5 : 1 }}
                    >
                        <Upload size={16} style={{ marginRight: 8 }} />
                        Processar {bankFiles.length} Extratos
                    </button>

                    {bankFiles.length > 0 && (
                        <button onClick={() => setBankFiles([])} style={{ background: 'none', border: 'none', color: '#fca5a5', fontSize: '0.8rem', marginTop: 5, cursor: 'pointer', width: '100%' }}>
                            Limpar seleção
                        </button>
                    )}
                </div>
            </div>

            {/* Scan Section Full Width */}
            <div style={{ background: 'rgba(0,0,0,0.2)', padding: '20px', borderRadius: '12px' }}>
                <h3 style={{ marginTop: 0 }}>3. Escanear Pasta de Extratos</h3>
                <div style={{ display: 'flex', gap: '10px', marginBottom: '20px' }}>
                    <div style={{ flex: 1, display: 'flex', gap: 5 }}>
                        <input
                            type="text"
                            placeholder="C:\Caminho\Para\Extratos"
                            value={folderPath}
                            onChange={(e) => setFolderPath(e.target.value)}
                            style={{
                                flex: 1,
                                padding: '10px',
                                borderRadius: '6px',
                                border: '1px solid rgba(255,255,255,0.2)',
                                background: 'rgba(0,0,0,0.3)',
                                color: 'white'
                            }}
                        />
                        <button
                            title="Selecionar Pasta"
                            onClick={handleBrowseRequest}
                            style={{
                                background: 'rgba(255,255,255,0.1)',
                                border: '1px solid rgba(255,255,255,0.2)',
                                borderRadius: '6px',
                                cursor: 'pointer',
                                color: 'white',
                                padding: '0 12px'
                            }}
                        >
                            <FolderOpen size={18} />
                        </button>
                    </div>

                    <button
                        className="btn-primary"
                        onClick={handleScan}
                        disabled={scanning || !folderPath}
                        style={{ padding: '8px 16px' }}
                    >
                        {scanning ? '...' : <FolderSearch size={18} style={{ marginRight: 6 }} />}
                        Escanear
                    </button>
                </div>

                {/* Scan Results Table */}
                {scannedFiles.length > 0 && (
                    <div style={{ marginTop: '20px', animation: 'fadeIn 0.5s' }}>
                        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 10 }}>
                            <h4 style={{ margin: 0 }}>Arquivos Encontrados ({selectedScanFiles.length} selecionados)</h4>
                            <button className="btn-primary" onClick={handleIngestSelected} style={{ background: '#10b981' }}>
                                Importar Selecionados
                            </button>
                        </div>

                        <div style={{ maxHeight: '300px', overflowY: 'auto', border: '1px solid rgba(255,255,255,0.1)', borderRadius: 8 }}>
                            <table className="data-table" style={{ marginTop: 0 }}>
                                <thead style={{ position: 'sticky', top: 0, background: '#1e293b', zIndex: 1 }}>
                                    <tr>
                                        <th style={{ width: 40 }}>
                                            <input
                                                type="checkbox"
                                                checked={selectedScanFiles.length === scannedFiles.length}
                                                onChange={(e) => {
                                                    if (e.target.checked) setSelectedScanFiles(scannedFiles.map(f => f.path));
                                                    else setSelectedScanFiles([]);
                                                }}
                                            />
                                        </th>
                                        <th>Arquivo</th>
                                        <th>Banco</th>
                                        <th>Período</th>
                                    </tr>
                                </thead>
                                <tbody>
                                    {scannedFiles.map((file, idx) => (
                                        <tr key={idx} style={{ background: selectedScanFiles.includes(file.path) ? 'rgba(99, 102, 241, 0.1)' : 'transparent' }}>
                                            <td>
                                                <input
                                                    type="checkbox"
                                                    checked={selectedScanFiles.includes(file.path)}
                                                    onChange={() => toggleScanFile(file.path)}
                                                />
                                            </td>
                                            <td>{file.filename}</td>
                                            <td>{file.bank}</td>
                                            <td>{file.period}</td>
                                        </tr>
                                    ))}
                                </tbody>
                            </table>
                        </div>
                    </div>
                )}
            </div>
        </div>
    );
};

export default UploadPage;
