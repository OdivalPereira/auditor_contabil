import React, { useState, useEffect } from 'react';
import api from '../api/client';
import { useApp } from '../hooks/useApp';
import { Upload, FolderSearch, CheckCircle, AlertCircle, FolderOpen, FileSpreadsheet, File as FileIcon, Trash2, Play, Receipt, UserCog, Landmark, FileText, FileCode } from 'lucide-react';

// Tab configuration for each conciliation mode
const CONCILIATION_MODES = [
    { id: 'bancaria', label: 'Bancária', icon: Landmark, color: '#6366f1', bgColor: 'rgba(99, 102, 241, 0.15)' },
    { id: 'fiscal', label: 'Fiscal', icon: Receipt, color: '#10b981', bgColor: 'rgba(16, 185, 129, 0.15)' },
    { id: 'folha', label: 'Folha', icon: UserCog, color: '#f59e0b', bgColor: 'rgba(245, 158, 11, 0.15)' },
];

const UploadPage = () => {
    const {
        ledgerFile, setLedgerFile,
        bankFiles, setBankFiles,
        setReconcileResults,
        uploadStatus, refreshUploadStatus,
        lastTolerance,
        clearAll
    } = useApp();

    // Active conciliation mode
    const [activeMode, setActiveMode] = useState('bancaria');

    // Fiscal files state (UI only - no backend logic)
    const [nfeFiles, setNfeFiles] = useState([]);
    const [spedFile, setSpedFile] = useState(null);

    // Folha files state (UI only - no backend logic)
    const [folhaFiles, setFolhaFiles] = useState([]);
    const [guiasFiles, setGuiasFiles] = useState([]);

    const [dragActive, setDragActive] = useState({ ledger: false, bank: false, nfe: false, sped: false, folha: false, guias: false });

    //Scan State
    const [scanning, setScanning] = useState(false);
    const [folderPath, setFolderPath] = useState('');
    const [scannedFiles, setScannedFiles] = useState([]);
    const [selectedScanFiles, setSelectedScanFiles] = useState([]);

    // Processing State
    const [processing, setProcessing] = useState(false);

    // Global Status
    const [status, setStatus] = useState({ type: '', msg: '' });

    // On mount, check if backend has data
    useEffect(() => {
        refreshUploadStatus();
    }, []);

    // Get current mode config
    const currentMode = CONCILIATION_MODES.find(m => m.id === activeMode);

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
            const files = Array.from(e.dataTransfer.files);
            switch (type) {
                case 'ledger':
                    setLedgerFile(e.dataTransfer.files[0]);
                    break;
                case 'bank':
                    setBankFiles(prev => [...prev, ...files]);
                    break;
                case 'nfe':
                    setNfeFiles(prev => [...prev, ...files]);
                    break;
                case 'sped':
                    setSpedFile(e.dataTransfer.files[0]);
                    break;
                case 'folha':
                    setFolhaFiles(prev => [...prev, ...files]);
                    break;
                case 'guias':
                    setGuiasFiles(prev => [...prev, ...files]);
                    break;
            }
        }
    };

    // UNIFIED PROCESSING FUNCTION (only works for bancaria mode currently)
    const handleProcessReconciliation = async () => {
        if (activeMode !== 'bancaria') {
            setStatus({ type: 'info', msg: `O processamento para Conciliação ${currentMode.label} ainda está em desenvolvimento.` });
            return;
        }

        if (!ledgerFile && uploadStatus.ledger_count === 0) {
            setStatus({ type: 'error', msg: 'Selecione o Livro Diário primeiro.' });
            return;
        }
        if (bankFiles.length === 0 && uploadStatus.bank_count === 0) {
            setStatus({ type: 'error', msg: 'Selecione pelo menos um Extrato Bancário.' });
            return;
        }

        setProcessing(true);
        setStatus({ type: 'info', msg: '📤 Preparando arquivos...' });

        try {
            // Step 1: Upload Ledger (if new file selected)
            if (ledgerFile) {
                setStatus({ type: 'info', msg: '📤 Enviando Diário...' });
                const ledgerFormData = new FormData();
                ledgerFormData.append('file', ledgerFile);
                await api.post('/upload/ledger', ledgerFormData);
            }

            // Step 2: Upload Bank Statements (if new files selected)
            if (bankFiles.length > 0) {
                setStatus({ type: 'info', msg: '📤 Enviando Extratos...' });
                const bankFormData = new FormData();
                bankFiles.forEach(file => {
                    bankFormData.append('files', file);
                });
                await api.post('/upload/bank', bankFormData);
            }

            setStatus({ type: 'info', msg: '🔄 Processando conciliação...' });

            // Step 3: Run Reconciliation
            const reconcileRes = await api.post(`/reconcile/?tolerance=${lastTolerance}`);

            // Sync status
            await refreshUploadStatus();

            // Save results to context
            setReconcileResults(reconcileRes.data);

            const metrics = reconcileRes.data.metrics;
            const rows = reconcileRes.data.rows;
            const bankRows = rows.filter(r => r.source === 'Banco');
            const matchedRows = rows.filter(r => r.status?.includes('Conciliado'));

            // Calculate rate purely from bank perspective if possible, or just use metrics
            const matchRate = metrics.bank_total > 0
                ? ((matchedRows.filter(r => r.source === 'Banco').length / metrics.bank_total) * 100).toFixed(1)
                : 0;

            setStatus({
                type: 'success',
                msg: `✅ Conciliação concluída! Taxa de conciliação: ${matchRate}%. Veja os resultados na aba "Conciliação Bancária".`
            });

            // Clear local file selection after successful upload/process
            setLedgerFile(null);
            setBankFiles([]);

        } catch (error) {
            console.error(error);
            const msg = error.response?.data?.detail || 'Erro ao processar conciliação.';
            setStatus({ type: 'error', msg: msg });
        } finally {
            setProcessing(false);
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
            await refreshUploadStatus();
            setStatus({
                type: 'success',
                msg: `Sucesso! ${ingestRes.data.count} transações carregadas.`
            });
        } catch (error) {
            setStatus({ type: 'error', msg: 'Erro ao importar arquivos selecionados.' });
        }
    };

    const onClear = async () => {
        if (window.confirm("Isso irá remover todos os dados carregados nesta sessão. Continuar?")) {
            try {
                await clearAll();
                // Clear local page specific state
                setFolderPath('');
                setScannedFiles([]);
                setSelectedScanFiles([]);
                setNfeFiles([]);
                setSpedFile(null);
                setFolhaFiles([]);
                setGuiasFiles([]);
                setStatus({ type: 'success', msg: 'Todos os dados foram limpos com sucesso!' });
            } catch (error) {
                console.error("Error during manual clear:", error);
                setStatus({ type: 'error', msg: 'Erro ao limpar dados. Tente novamente.' });
            }
        }
    };

    // Reusable DropZone component
    const DropZone = ({ type, title, description, accept, multiple, files, setFiles, icon: Icon, color }) => (
        <div
            style={{
                background: dragActive[type] ? `${color}33` : 'rgba(0,0,0,0.2)',
                padding: '20px',
                borderRadius: '12px',
                border: dragActive[type] ? `2px dashed ${color}` : '2px dashed #ffffff11',
                transition: 'all 0.2s',
                position: 'relative'
            }}
            onDragEnter={(e) => handleDrag(e, type, true)}
            onDragLeave={(e) => handleDrag(e, type, false)}
            onDragOver={(e) => handleDrag(e, type, true)}
            onDrop={(e) => handleDrop(e, type)}
        >
            <h4 style={{ marginTop: 0, display: 'flex', alignItems: 'center', gap: 8 }}>
                <Icon size={20} style={{ color }} />
                {title}
            </h4>
            <p style={{ color: 'var(--text-secondary)', fontSize: '0.85rem', margin: '8px 0 15px' }}>{description}</p>

            <input
                type="file"
                accept={accept}
                multiple={multiple}
                id={`${type}-input`}
                onChange={(e) => {
                    if (multiple) {
                        setFiles(prev => [...prev, ...Array.from(e.target.files)]);
                    } else {
                        setFiles(e.target.files[0]);
                    }
                }}
                style={{ display: 'none' }}
            />
            <label htmlFor={`${type}-input`} style={{
                display: 'block',
                textAlign: 'center',
                background: 'rgba(255,255,255,0.08)',
                padding: '10px',
                borderRadius: '8px',
                cursor: 'pointer',
                border: `1px solid ${color}44`,
                color: color,
                fontSize: '0.9rem',
                transition: 'all 0.2s'
            }}>
                {multiple ? 'Adicionar Arquivos...' : 'Selecionar Arquivo'}
            </label>

            {((multiple && files.length > 0) || (!multiple && files)) && (
                <div style={{ marginTop: 10, fontSize: '0.8rem', color: '#10b981', background: 'rgba(0,0,0,0.2)', padding: '8px 10px', borderRadius: 5, maxHeight: 80, overflowY: 'auto' }}>
                    {multiple ? (
                        files.map((f, i) => <div key={i}><CheckCircle size={12} style={{ verticalAlign: -2 }} /> {f.name}</div>)
                    ) : (
                        <div><CheckCircle size={12} style={{ verticalAlign: -2 }} /> {files.name}</div>
                    )}
                </div>
            )}

            {multiple && files.length > 0 && (
                <button onClick={() => setFiles([])} style={{ background: 'none', border: 'none', color: '#fca5a5', fontSize: '0.8rem', cursor: 'pointer', width: '100%', marginTop: 5 }}>
                    Limpar seleção
                </button>
            )}
        </div>
    );

    return (
        <div className="glass-panel" style={{ padding: '30px' }}>
            {/* Header */}
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '20px' }}>
                <h2 style={{ margin: 0 }}>📂 Importação de Dados</h2>
                <div style={{ display: 'flex', alignItems: 'center', gap: 20 }}>
                    {uploadStatus.ledger_count > 0 && (
                        <div style={{ fontSize: '0.85rem', color: '#6ee7b7', background: 'rgba(16, 185, 129, 0.1)', padding: '5px 12px', borderRadius: '20px', border: '1px solid #10b98144' }}>
                            <CheckCircle size={14} style={{ verticalAlign: -2, marginRight: 5 }} />
                            Dados carregados ({uploadStatus.ledger_count + uploadStatus.bank_count} itens)
                        </div>
                    )}
                    <button
                        onClick={onClear}
                        style={{
                            background: 'rgba(239, 68, 68, 0.1)',
                            color: '#fca5a5',
                            border: '1px solid rgba(239, 68, 68, 0.2)',
                            padding: '8px 16px',
                            borderRadius: '8px',
                            display: 'flex',
                            alignItems: 'center',
                            gap: '8px',
                            cursor: 'pointer',
                            fontSize: '0.9rem',
                            transition: 'all 0.2s'
                        }}
                    >
                        <Trash2 size={16} /> Limpar Dados
                    </button>
                </div>
            </div>

            {/* Mode Tabs */}
            <div style={{ display: 'flex', gap: '10px', marginBottom: '25px', borderBottom: '1px solid rgba(255,255,255,0.1)', paddingBottom: '15px' }}>
                {CONCILIATION_MODES.map(mode => {
                    const Icon = mode.icon;
                    const isActive = activeMode === mode.id;
                    return (
                        <button
                            key={mode.id}
                            onClick={() => setActiveMode(mode.id)}
                            style={{
                                background: isActive ? mode.bgColor : 'transparent',
                                border: isActive ? `1px solid ${mode.color}` : '1px solid rgba(255,255,255,0.1)',
                                color: isActive ? mode.color : '#94a3b8',
                                padding: '12px 24px',
                                borderRadius: '10px',
                                cursor: 'pointer',
                                display: 'flex',
                                alignItems: 'center',
                                gap: '10px',
                                fontSize: '1rem',
                                fontWeight: isActive ? 600 : 400,
                                transition: 'all 0.2s'
                            }}
                        >
                            <Icon size={20} />
                            Conciliação {mode.label}
                        </button>
                    );
                })}
            </div>

            {/* Status Message */}
            {status.msg && (
                <div style={{
                    padding: '15px',
                    borderRadius: '8px',
                    marginBottom: '20px',
                    backgroundColor: status.type === 'error' ? 'rgba(239, 68, 68, 0.2)' : (status.type === 'info' ? 'rgba(99, 102, 241, 0.2)' : 'rgba(16, 185, 129, 0.2)'),
                    color: status.type === 'error' ? '#fca5a5' : (status.type === 'info' ? '#a5b4fc' : '#6ee7b7'),
                    border: `1px solid ${status.type === 'error' ? '#ef4444' : (status.type === 'info' ? '#6366f1' : '#10b981')}`
                }}>
                    {status.type === 'error' ? <AlertCircle size={18} style={{ verticalAlign: 'middle', marginRight: 8 }} /> : <CheckCircle size={18} style={{ verticalAlign: 'middle', marginRight: 8 }} />}
                    {status.msg}
                </div>
            )}

            {/* Ledger Section - Common to all modes */}
            <div style={{ marginBottom: 25 }}>
                <div
                    style={{
                        background: dragActive.ledger ? 'rgba(99, 102, 241, 0.2)' : 'rgba(0,0,0,0.2)',
                        padding: '20px',
                        borderRadius: '12px',
                        border: dragActive.ledger ? '2px dashed #6366f1' : '2px dashed #ffffff11',
                        transition: 'all 0.2s',
                        position: 'relative'
                    }}
                    onDragEnter={(e) => handleDrag(e, 'ledger', true)}
                    onDragLeave={(e) => handleDrag(e, 'ledger', false)}
                    onDragOver={(e) => handleDrag(e, 'ledger', true)}
                    onDrop={(e) => handleDrop(e, 'ledger')}
                >
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
                        <div>
                            <h3 style={{ marginTop: 0, display: 'flex', alignItems: 'center', gap: 8 }}>
                                <FileSpreadsheet size={20} />
                                1. Livro Diário
                            </h3>
                            <p style={{ color: 'var(--text-secondary)', margin: 0 }}>Arraste o PDF ou CSV aqui.</p>
                        </div>
                        <div style={{
                            display: 'flex',
                            alignItems: 'center',
                            gap: 8,
                            padding: '6px 14px',
                            borderRadius: '20px',
                            background: currentMode.bgColor,
                            border: `1px solid ${currentMode.color}44`
                        }}>
                            <currentMode.icon size={16} style={{ color: currentMode.color }} />
                            <span style={{ fontSize: '0.85rem', color: currentMode.color, fontWeight: 500 }}>
                                Para: Conciliação {currentMode.label}
                            </span>
                        </div>
                    </div>

                    <div style={{ textAlign: 'center', margin: '20px 0', opacity: 0.5 }}>
                        <FileSpreadsheet size={40} />
                    </div>

                    <input
                        type="file"
                        accept=".pdf,.csv"
                        id="ledger-input"
                        onChange={(e) => setLedgerFile(e.target.files[0])}
                        style={{ display: 'none' }}
                    />
                    <label htmlFor="ledger-input" className="btn-primary" style={{ display: 'block', textAlign: 'center', background: 'rgba(255,255,255,0.1)', cursor: 'pointer' }}>
                        {ledgerFile ? 'Trocar Arquivo' : (uploadStatus.ledger_count > 0 ? 'Já carregado. Trocar?' : 'Selecionar Arquivo')}
                    </label>

                    {(ledgerFile || uploadStatus.ledger_name) && (
                        <div style={{ marginTop: 10, fontSize: '0.8rem', color: '#10b981', background: 'rgba(0,0,0,0.2)', padding: '5px 10px', borderRadius: 5 }}>
                            <CheckCircle size={12} style={{ verticalAlign: -2 }} /> {ledgerFile ? ledgerFile.name : `Atual: ${uploadStatus.ledger_name}`}
                        </div>
                    )}
                </div>
            </div>

            {/* Mode-specific sections */}
            <div style={{ marginBottom: 30 }}>
                {/* BANCÁRIA MODE */}
                {activeMode === 'bancaria' && (
                    <div style={{ display: 'grid', gridTemplateColumns: '1fr', gap: '20px' }}>
                        <div
                            style={{
                                background: dragActive.bank ? 'rgba(16, 185, 129, 0.2)' : 'rgba(0,0,0,0.2)',
                                padding: '20px',
                                borderRadius: '12px',
                                border: dragActive.bank ? '2px dashed #10b981' : '2px dashed #ffffff11',
                                transition: 'all 0.2s'
                            }}
                            onDragEnter={(e) => handleDrag(e, 'bank', true)}
                            onDragLeave={(e) => handleDrag(e, 'bank', false)}
                            onDragOver={(e) => handleDrag(e, 'bank', true)}
                            onDrop={(e) => handleDrop(e, 'bank')}
                        >
                            <h3 style={{ marginTop: 0, display: 'flex', alignItems: 'center', gap: 8 }}>
                                <Landmark size={20} style={{ color: '#6366f1' }} />
                                2. Extratos Bancários
                            </h3>
                            <p style={{ color: 'var(--text-secondary)' }}>Arraste vários PDFs ou OFXs aqui.</p>

                            <div style={{ textAlign: 'center', margin: '20px 0', opacity: 0.5 }}>
                                <FileIcon size={40} />
                            </div>

                            <input
                                type="file"
                                multiple
                                accept=".pdf,.ofx"
                                id="bank-input"
                                onChange={(e) => setBankFiles(prev => [...prev, ...Array.from(e.target.files)])}
                                style={{ display: 'none' }}
                            />
                            <label htmlFor="bank-input" className="btn-primary" style={{ display: 'block', textAlign: 'center', background: 'rgba(255,255,255,0.1)', cursor: 'pointer' }}>
                                Adicionar Arquivos...
                            </label>

                            {(bankFiles.length > 0 || uploadStatus.bank_count > 0) && (
                                <>
                                    <div style={{ marginTop: 10, marginBottom: 10, maxHeight: 100, overflowY: 'auto', fontSize: '0.8rem', color: '#94a3b8', background: 'rgba(0,0,0,0.2)', padding: '5px 10px', borderRadius: 4 }}>
                                        {bankFiles.length > 0 ? (
                                            bankFiles.map((f, i) => <div key={i}>{f.name}</div>)
                                        ) : (
                                            <div>{uploadStatus.bank_count} arquivos já no servidor</div>
                                        )}
                                    </div>
                                    {bankFiles.length > 0 && <button onClick={() => setBankFiles([])} style={{ background: 'none', border: 'none', color: '#fca5a5', fontSize: '0.8rem', cursor: 'pointer', width: '100%' }}>
                                        Limpar seleção local
                                    </button>}
                                </>
                            )}
                        </div>
                    </div>
                )}

                {/* FISCAL MODE */}
                {activeMode === 'fiscal' && (
                    <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '20px' }}>
                        <DropZone
                            type="nfe"
                            title="2. XMLs de NFe"
                            description="Notas fiscais de entrada e saída (.xml)"
                            accept=".xml"
                            multiple={true}
                            files={nfeFiles}
                            setFiles={setNfeFiles}
                            icon={FileCode}
                            color="#10b981"
                        />
                        <DropZone
                            type="sped"
                            title="3. SPED Fiscal (Opcional)"
                            description="Arquivo SPED EFD (.txt)"
                            accept=".txt"
                            multiple={false}
                            files={spedFile}
                            setFiles={setSpedFile}
                            icon={FileText}
                            color="#10b981"
                        />
                    </div>
                )}

                {/* FOLHA MODE */}
                {activeMode === 'folha' && (
                    <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '20px' }}>
                        <DropZone
                            type="folha"
                            title="2. Folha de Pagamento"
                            description="Relatórios da folha (.pdf, .csv)"
                            accept=".pdf,.csv"
                            multiple={true}
                            files={folhaFiles}
                            setFiles={setFolhaFiles}
                            icon={FileSpreadsheet}
                            color="#f59e0b"
                        />
                        <DropZone
                            type="guias"
                            title="3. Guias FGTS/INSS"
                            description="DARFs e guias de recolhimento (.pdf)"
                            accept=".pdf"
                            multiple={true}
                            files={guiasFiles}
                            setFiles={setGuiasFiles}
                            icon={FileText}
                            color="#f59e0b"
                        />
                    </div>
                )}
            </div>

            {/* UNIFIED PROCESS BUTTON */}
            <div style={{ textAlign: 'center', marginBottom: 40, background: 'rgba(255,255,255,0.02)', padding: '30px', borderRadius: '15px', border: '1px solid rgba(255,255,255,0.05)' }}>
                <button
                    className="btn-primary"
                    onClick={handleProcessReconciliation}
                    disabled={processing || (activeMode !== 'bancaria')}
                    style={{
                        fontSize: '1.2rem',
                        padding: '18px 45px',
                        background: activeMode === 'bancaria'
                            ? 'linear-gradient(135deg, #6366f1 0%, #a855f7 100%)'
                            : `linear-gradient(135deg, ${currentMode.color} 0%, ${currentMode.color}aa 100%)`,
                        boxShadow: `0 10px 20px -5px ${currentMode.color}66`,
                        opacity: (processing || activeMode !== 'bancaria') ? 0.5 : 1,
                        cursor: (activeMode !== 'bancaria') ? 'not-allowed' : 'pointer',
                        display: 'inline-flex',
                        alignItems: 'center',
                        gap: '12px',
                        border: 'none'
                    }}
                >
                    {processing ? (
                        <>Processando...</>
                    ) : (
                        <>
                            <Play size={22} fill="currentColor" />
                            🚀 Processar Conciliação {currentMode.label}
                        </>
                    )}
                </button>
                <div style={{ marginTop: 15, fontSize: '0.9rem', color: '#94a3b8' }}>
                    {activeMode === 'bancaria' ? (
                        <>A conciliação será realizada cruzando todos os dados carregados usando tolerância de <strong>{lastTolerance} dias</strong>.</>
                    ) : (
                        <>⚠️ O processamento para Conciliação {currentMode.label} estará disponível em breve.</>
                    )}
                </div>
            </div>

            {/* Scan Section - Only for Bancária mode */}
            {activeMode === 'bancaria' && (
                <div style={{ background: 'rgba(0,0,0,0.2)', padding: '20px', borderRadius: '12px' }}>
                    <h3 style={{ marginTop: 0 }}>📁 Escanear Pasta de Extratos</h3>
                    <div style={{ display: 'flex', gap: '10px', marginBottom: '20px' }}>
                        <div style={{ flex: 1, display: 'flex', gap: 5 }}>
                            <input
                                type="text"
                                placeholder="C:\\Caminho\\Para\\Extratos"
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
            )}
        </div>
    );
};

export default UploadPage;
