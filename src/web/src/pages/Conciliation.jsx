import React, { useEffect, useState, useMemo } from 'react';
import api from '../api/client';
import { useApp } from '../AppContext';
import { Search, Download, RefreshCw, Settings, Play, CheckCircle2, XCircle, HelpCircle, Layers, AlertCircle } from 'lucide-react';

const Conciliation = () => {
    const { reconcileResults, setReconcileResults, lastTolerance, setLastTolerance, uploadStatus, refreshUploadStatus } = useApp();
    const [loading, setLoading] = useState(false);
    const [showSettings, setShowSettings] = useState(false);

    // Filters - Now defaults to showing everything!
    const [filterStatus, setFilterStatus] = useState(['Conciliado', 'Apenas no Banco', 'Apenas no Diário']);
    const [searchTerm, setSearchTerm] = useState('');

    const loadData = async (tol) => {
        if (uploadStatus.ledger_count === 0) {
            await refreshUploadStatus();
        }

        setLoading(true);
        try {
            // Use query param as expected by FastAPI @router.post("/") run_reconciliation(tolerance: int = 3)
            const res = await api.post(`/reconcile/?tolerance=${tol}`);
            if (res.data.rows) {
                setReconcileResults(res.data);
            }
        } catch (err) {
            console.error(err);
        } finally {
            setLoading(false);
        }
    };

    useEffect(() => {
        // Only load if we don't have results yet
        if (!reconcileResults) {
            loadData(lastTolerance);
        }
    }, []);

    const handleReprocess = () => {
        loadData(lastTolerance);
    };

    const rows = reconcileResults?.rows || [];

    const filteredRows = useMemo(() => {
        return rows.filter(row => {
            // Status filter: Only show rows matching selected statuses
            const statusMatch = filterStatus.some(fs => {
                if (fs === 'Conciliado') {
                    return (row.status || '').includes('Conciliado');
                } else {
                    return row.status === fs;
                }
            });

            if (!statusMatch) return false;

            // Search filter
            if (searchTerm) {
                const term = searchTerm.toLowerCase();
                const desc = (row.description || '').toLowerCase();
                const val = typeof row.amount === 'number' ? row.amount.toString() : '';
                return desc.includes(term) || val.includes(term);
            }

            return true;
        });
    }, [rows, filterStatus, searchTerm]);

    const statusOptions = ['Conciliado', 'Apenas no Banco', 'Apenas no Diário'];

    const toggleFilter = (s) => {
        setFilterStatus(prev =>
            prev.includes(s) ? prev.filter(p => p !== s) : [...prev, s]
        );
    };

    const StatusBadge = ({ status }) => {
        let color = '#94a3b8';
        let bg = 'rgba(148, 163, 184, 0.1)';
        let Icon = HelpCircle;

        if (status.includes('Conciliado')) {
            color = '#10b981';
            bg = 'rgba(16, 185, 129, 0.1)';
            Icon = CheckCircle2;
        } else if (status === 'Apenas no Banco') {
            color = '#f59e0b';
            bg = 'rgba(245, 158, 11, 0.1)';
            Icon = AlertCircle;
        } else if (status === 'Apenas no Diário') {
            color = '#ef4444';
            bg = 'rgba(239, 68, 68, 0.1)';
            Icon = XCircle;
        }

        return (
            <div style={{
                display: 'inline-flex',
                alignItems: 'center',
                gap: '6px',
                padding: '4px 10px',
                borderRadius: '20px',
                background: bg,
                color: color,
                fontSize: '0.75rem',
                fontWeight: 600,
                border: `1px solid ${color}44`
            }}>
                <Icon size={14} />
                {status}
            </div>
        );
    };

    const getRowClass = (row) => {
        if (row.group_id !== "-1") return "grouped-row";
        return "";
    };

    const handleDownload = async (type) => {
        try {
            // Enviar dados filtrados para o backend
            const response = await api.post(`/export/${type}`, filteredRows, {
                responseType: 'blob' // Importante para receber arquivo binário
            });

            // Criar URL temporária para download
            const blob = new Blob([response.data]);
            const url = window.URL.createObjectURL(blob);
            const link = document.createElement('a');
            link.href = url;

            // Extrair nome do arquivo do header Content-Disposition se disponível
            const contentDisposition = response.headers['content-disposition'];
            let filename = `conciliacao_${new Date().toISOString().slice(0, 10)}.${type === 'excel' ? 'xlsx' : 'pdf'}`;
            if (contentDisposition) {
                const filenameMatch = contentDisposition.match(/filename="([^"]+)"/);
                if (filenameMatch && filenameMatch[1]) {
                    filename = filenameMatch[1];
                }
            }

            link.download = filename;
            document.body.appendChild(link);
            link.click();
            document.body.removeChild(link);
            window.URL.revokeObjectURL(url);
        } catch (error) {
            console.error(`Erro ao gerar ${type}:`, error);
            alert(`Erro ao gerar ${type}. Verifique o console para mais detalhes.`);
        }
    };

    return (
        <div style={{ animation: 'fadeIn 0.5s ease-out' }}>
            {/* Page Header */}
            <div style={{ marginBottom: '25px', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                <h1 style={{ margin: 0 }}>Conciliação Detalhada</h1>
                <div style={{ display: 'flex', gap: '10px' }}>
                    <button className="btn-primary" onClick={() => handleDownload('excel')} style={{ background: '#059669', display: 'inline-flex', alignItems: 'center', gap: 6 }}>
                        <Download size={18} /> Excel
                    </button>
                    <button className="btn-primary" onClick={() => handleDownload('pdf')} style={{ background: '#dc2626', display: 'inline-flex', alignItems: 'center', gap: 6 }}>
                        <Download size={18} /> PDF
                    </button>
                </div>
            </div>

            {/* Sticky Control Bar */}
            <div className="glass-panel" style={{ padding: '18px 20px', marginBottom: '20px', position: 'sticky', top: '0', zIndex: 5, boxShadow: '0 8px 32px rgba(0,0,0,0.2)' }}>
                <div style={{ display: 'flex', gap: '15px', alignItems: 'center', justifyContent: 'space-between' }}>

                    {/* Search */}
                    <div style={{ position: 'relative', flex: '0 0 400px' }}>
                        <Search size={18} style={{ position: 'absolute', left: 12, top: '50%', transform: 'translateY(-50%)', color: 'rgba(255,255,255,0.4)' }} />
                        <input
                            type="text"
                            placeholder="Filtrar lançamentos..."
                            value={searchTerm}
                            onChange={e => setSearchTerm(e.target.value)}
                            style={{
                                paddingLeft: '40px',
                                height: '42px',
                                background: 'rgba(0,0,0,0.3)',
                                border: '1px solid rgba(255,255,255,0.15)',
                                borderRadius: '10px',
                                color: 'white',
                                width: '100%',
                                fontSize: '0.9rem'
                            }}
                        />
                    </div>

                    {/* Filters */}
                    <div style={{ display: 'flex', gap: '12px', alignItems: 'center', flexWrap: 'wrap' }}>
                        {statusOptions.map(opt => {
                            const isActive = filterStatus.includes(opt);

                            // Define cores específicas para cada status
                            let btnColor = '#6366f1'; // Default
                            let btnBg = 'rgba(99, 102, 241, 0.15)';

                            if (opt === 'Conciliado') {
                                btnColor = '#10b981';
                                btnBg = 'rgba(16, 185, 129, 0.15)';
                            } else if (opt === 'Apenas no Banco') {
                                btnColor = '#f59e0b';
                                btnBg = 'rgba(245, 158, 11, 0.15)';
                            } else if (opt === 'Apenas no Diário') {
                                btnColor = '#ef4444';
                                btnBg = 'rgba(239, 68, 68, 0.15)';
                            }

                            return (
                                <button
                                    key={opt}
                                    onClick={() => toggleFilter(opt)}
                                    style={{
                                        background: isActive ? btnColor : btnBg,
                                        border: `1px solid ${isActive ? btnColor : 'rgba(255,255,255,0.1)'}`,
                                        color: isActive ? 'white' : btnColor,
                                        padding: '7px 14px',
                                        borderRadius: '8px',
                                        cursor: 'pointer',
                                        fontSize: '0.77rem',
                                        fontWeight: isActive ? 600 : 500,
                                        transition: 'all 0.2s',
                                        whiteSpace: 'nowrap'
                                    }}
                                >
                                    {opt}
                                </button>
                            );
                        })}

                        <div style={{ marginLeft: 'auto' }} />

                        {/* Right: Settings */}
                        <button
                            onClick={() => setShowSettings(!showSettings)}
                            style={{
                                background: showSettings ? 'rgba(99, 102, 241, 0.2)' : 'transparent',
                                border: '1px solid rgba(255,255,255,0.1)',
                                borderRadius: '10px',
                                width: '40px',
                                height: '40px',
                                display: 'flex',
                                alignItems: 'center',
                                justifyContent: 'center',
                                cursor: 'pointer',
                                color: 'white',
                                transition: 'all 0.2s'
                            }}
                            title="Configurações de Conciliação"
                        >
                            <Settings size={20} className={showSettings ? 'spin' : ''} />
                        </button>
                    </div>

                    {showSettings && (
                        <div style={{ marginTop: 20, paddingTop: 15, borderTop: '1px solid rgba(255,255,255,0.1)', display: 'flex', alignItems: 'center', gap: 25, animation: 'fadeIn 0.3s' }}>
                            <div style={{ flex: 1 }}>
                                <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 8 }}>
                                    <span style={{ fontSize: '0.85rem', color: '#94a3b8' }}>Tolerância de Datas (Dias)</span>
                                    <span style={{ fontWeight: 'bold' }}>{lastTolerance} dias</span>
                                </div>
                                <input
                                    type="range"
                                    min="0" max="15"
                                    value={lastTolerance}
                                    onChange={(e) => setLastTolerance(parseInt(e.target.value))}
                                    style={{ width: '100%', accentColor: 'var(--accent-color)' }}
                                />
                            </div>
                            <button
                                className="btn-primary"
                                onClick={handleReprocess}
                                disabled={loading}
                                style={{ padding: '10px 25px', display: 'flex', alignItems: 'center', gap: 10 }}
                            >
                                {loading ? <RefreshCw className="spin" size={18} /> : <Play size={18} fill="currentColor" />}
                                Recalcular Agora
                            </button>
                        </div>
                    )}
                </div>
            </div>

            {/* Results Grid */}
            <div className="glass-panel" style={{ borderRadius: '15px', overflow: 'hidden', minHeight: '500px' }}>
                <table className="data-table" style={{ marginTop: 0 }}>
                    <thead style={{ background: 'rgba(15, 23, 42, 0.4)' }}>
                        <tr>
                            <th style={{ width: '110px' }}>DATA</th>
                            <th style={{ width: '90px' }}>ORIGEM</th>
                            <th style={{ maxWidth: '450px' }}>DESCRIÇÃO</th>
                            <th style={{ width: '140px', textAlign: 'right' }}>VALOR</th>
                            <th style={{ width: '200px', textAlign: 'center' }}>STATUS</th>
                            <th style={{ width: '80px', textAlign: 'center' }}>GRUPO</th>
                        </tr>
                    </thead>
                    <tbody>
                        {loading && (
                            <tr>
                                <td colSpan={6} style={{ height: '400px', textAlign: 'center' }}>
                                    <RefreshCw size={48} className="spin" color="var(--accent-color)" opacity={0.5} />
                                    <p style={{ marginTop: 15, color: '#94a3b8' }}>Sincronizando dados...</p>
                                </td>
                            </tr>
                        )}
                        {!loading && filteredRows.length === 0 && (
                            <tr>
                                <td colSpan={6} style={{ height: '300px', textAlign: 'center', opacity: 0.5 }}>
                                    <Search size={48} style={{ marginBottom: 15 }} />
                                    <p>{rows.length === 0 ? "Nenhum dado processado. Vá para a aba 'Dados e Upload' primeiro." : "Nenhum registro encontrado para estes filtros."}</p>
                                </td>
                            </tr>
                        )}
                        {!loading && filteredRows.map((row, idx) => {
                            // Format date to PT-BR (DD/MM/YYYY)
                            const formatDate = (dateStr) => {
                                if (!dateStr) return '';
                                const d = new Date(dateStr);
                                return d.toLocaleDateString('pt-BR');
                            };

                            return (
                                <tr key={idx} className={getRowClass(row)} style={{
                                    transition: 'background 0.2s',
                                    borderLeft: row.group_id !== "-1" ? '3px solid var(--accent-color)' : 'none',
                                    background: row.group_id !== "-1" ? 'rgba(99, 102, 241, 0.05)' : 'transparent'
                                }}>
                                    <td style={{ fontSize: '0.9rem', color: '#cbd5e1', whiteSpace: 'nowrap' }}>{formatDate(row.date)}</td>
                                    <td>
                                        <span style={{ fontSize: '0.75rem', textTransform: 'uppercase', opacity: 0.6 }}>{row.source}</span>
                                    </td>
                                    <td
                                        style={{
                                            fontSize: '0.9rem',
                                            maxWidth: '450px',
                                            overflow: 'hidden',
                                            textOverflow: 'ellipsis',
                                            whiteSpace: 'nowrap'
                                        }}
                                        title={row.description}
                                    >
                                        {row.description}
                                    </td>
                                    <td style={{ textAlign: 'right', fontWeight: 600, color: row.amount < 0 ? '#f87171' : '#34d399', fontFamily: 'Inter, sans-serif', whiteSpace: 'nowrap' }}>
                                        {row.amount.toLocaleString('pt-BR', { style: 'currency', currency: 'BRL' })}
                                    </td>
                                    <td style={{ textAlign: 'center' }}>
                                        <StatusBadge status={row.status} />
                                    </td>
                                    <td style={{ textAlign: 'center', opacity: 0.5 }}>
                                        {row.group_id !== "-1" && (
                                            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 4 }}>
                                                <Layers size={12} />
                                                <span style={{ fontSize: '0.85rem' }}>{row.group_id}</span>
                                            </div>
                                        )}
                                    </td>
                                </tr>
                            );
                        })}
                    </tbody>
                </table>
            </div>

            <div style={{ padding: '20px 0', display: 'flex', justifyContent: 'space-between', color: '#94a3b8', fontSize: '0.85rem' }}>
                <div>Total: <strong>{rows.length}</strong> registros analisados</div>
                <div>Filtrados: <strong>{filteredRows.length}</strong> | Pendentes: <strong>{rows.filter(r => r.status === 'Apenas no Banco' || r.status === 'Apenas no Diário').length}</strong></div>
            </div>

            <style dangerouslySetInnerHTML={{
                __html: `
                .grouped-row:hover { background: rgba(99, 102, 241, 0.1) !important; }
                tbody tr:hover { background: rgba(255,255,255,0.03); }
            `}} />
        </div >
    );
};

export default Conciliation;
