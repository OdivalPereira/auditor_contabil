import React, { useEffect, useState, useMemo } from 'react';
import api from '../api/client';
import { Search, Filter, Download, RefreshCw, Settings, Play, CheckCircle2, XCircle, HelpCircle, Layers } from 'lucide-react';

const Conciliation = () => {
    const [rows, setRows] = useState([]);
    const [loading, setLoading] = useState(false);

    // Config
    const [tolerance, setTolerance] = useState(3);
    const [showSettings, setShowSettings] = useState(false);

    // Filters
    const [filterStatus, setFilterStatus] = useState(['Pendente - Banco', 'Pendente - Diário']);
    const [searchTerm, setSearchTerm] = useState('');

    const loadData = async (tol) => {
        setLoading(true);
        try {
            const res = await api.post(`/reconcile/?tolerance=${tol}`);
            if (res.data.rows) {
                setRows(res.data.rows);
            }
        } catch (err) {
            console.error(err);
        } finally {
            setLoading(false);
        }
    };

    useEffect(() => {
        loadData(tolerance);
    }, []);

    const handleReprocess = () => {
        loadData(tolerance);
    };

    const filteredRows = useMemo(() => {
        return rows.filter(row => {
            if (!filterStatus.includes(row.status)) {
                if (row.status.includes('Conciliado') && !filterStatus.includes('Conciliado')) return false;
            }
            if (searchTerm) {
                const term = searchTerm.toLowerCase();
                const desc = (row.description || '').toLowerCase();
                const val = typeof row.amount === 'number' ? row.amount.toString() : '';
                return desc.includes(term) || val.includes(term);
            }
            return true;
        });
    }, [rows, filterStatus, searchTerm]);

    const statusOptions = ['Conciliado', 'Pendente - Banco', 'Pendente - Diário'];

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
        } else if (status === 'Pendente - Banco') {
            color = '#f59e0b';
            bg = 'rgba(245, 158, 11, 0.1)';
            Icon = AlertCircle;
        } else if (status === 'Pendente - Diário') {
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

    const handleDownload = (type) => {
        const url = `/api/export/${type}`;
        window.open(url, '_blank');
    };

    return (
        <div style={{ animation: 'fadeIn 0.5s ease-out' }}>
            {/* Page Header */}
            <div style={{ marginBottom: '25px', display: 'flex', justifyContent: 'space-between', alignItems: 'flex-end' }}>
                <div>
                    <h1>Conciliação Detalhada</h1>
                    <p style={{ color: 'var(--text-secondary)', margin: 0 }}>Análise avançada cruzando Livro Diário e Extratos.</p>
                </div>
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
            <div className="glass-panel" style={{ padding: '15px 25px', marginBottom: '20px', position: 'sticky', top: '0', zIndex: 5, boxShadow: '0 8px 32px rgba(0,0,0,0.2)' }}>
                <div style={{ display: 'flex', gap: '30px', alignItems: 'center', justifyContent: 'space-between' }}>

                    {/* Left: Search & Filters */}
                    <div style={{ display: 'flex', gap: '20px', alignItems: 'center', flex: 1 }}>
                        <div style={{ position: 'relative', width: '300px' }}>
                            <Search size={18} style={{ position: 'absolute', left: 12, top: '50%', transform: 'translateY(-50%)', opacity: 0.5 }} />
                            <input
                                type="text"
                                placeholder="Filtrar lançamentos..."
                                value={searchTerm}
                                onChange={e => setSearchTerm(e.target.value)}
                                style={{
                                    paddingLeft: '40px',
                                    height: '40px',
                                    background: 'rgba(0,0,0,0.2)',
                                    border: '1px solid rgba(255,255,255,0.1)',
                                    borderRadius: '10px',
                                    color: 'white',
                                    width: '100%'
                                }}
                            />
                        </div>

                        <div style={{ display: 'flex', gap: '8px' }}>
                            {statusOptions.map(opt => (
                                <button
                                    key={opt}
                                    onClick={() => toggleFilter(opt)}
                                    style={{
                                        background: filterStatus.includes(opt) ? 'var(--accent-color)' : 'rgba(255,255,255,0.05)',
                                        border: filterStatus.includes(opt) ? '1px solid var(--accent-color)' : '1px solid rgba(255,255,255,0.1)',
                                        color: 'white',
                                        padding: '5px 14px',
                                        borderRadius: '25px',
                                        cursor: 'pointer',
                                        fontSize: '0.8rem',
                                        fontWeight: 500,
                                        transition: 'all 0.2s'
                                    }}
                                >
                                    {opt}
                                </button>
                            ))}
                        </div>
                    </div>

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
                                <span style={{ fontWeight: 'bold' }}>{tolerance} dias</span>
                            </div>
                            <input
                                type="range"
                                min="0" max="60"
                                value={tolerance}
                                onChange={(e) => setTolerance(parseInt(e.target.value))}
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

            {/* Results Grid */}
            <div className="glass-panel" style={{ borderRadius: '15px', overflow: 'hidden', minHeight: '500px' }}>
                <table className="data-table" style={{ marginTop: 0 }}>
                    <thead style={{ background: 'rgba(15, 23, 42, 0.4)' }}>
                        <tr>
                            <th style={{ width: '110px' }}>Data</th>
                            <th style={{ width: '100px' }}>Origem</th>
                            <th>Descrição</th>
                            <th style={{ width: '140px', textAlign: 'right' }}>Valor</th>
                            <th style={{ width: '180px', textAlign: 'center' }}>Status</th>
                            <th style={{ width: '80px', textAlign: 'center' }}>Grupo</th>
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
                                    <p>Nenhum registro encontrado para estes filtros.</p>
                                </td>
                            </tr>
                        )}
                        {!loading && filteredRows.map((row, idx) => (
                            <tr key={idx} className={getRowClass(row)} style={{
                                transition: 'background 0.2s',
                                borderLeft: row.group_id !== "-1" ? '3px solid var(--accent-color)' : 'none',
                                background: row.group_id !== "-1" ? 'rgba(99, 102, 241, 0.05)' : 'transparent'
                            }}>
                                <td style={{ fontSize: '0.9rem', color: '#cbd5e1' }}>{row.date}</td>
                                <td>
                                    <span style={{ fontSize: '0.75rem', textTransform: 'uppercase', opacity: 0.6 }}>{row.source}</span>
                                </td>
                                <td style={{ fontSize: '0.95rem' }}>{row.description}</td>
                                <td style={{ textAlign: 'right', fontWeight: 600, color: row.amount < 0 ? '#f87171' : '#34d399', fontFamily: 'Inter, sans-serif' }}>
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
                        ))}
                    </tbody>
                </table>
            </div>

            <div style={{ padding: '20px 0', display: 'flex', justifyContent: 'space-between', color: '#94a3b8', fontSize: '0.85rem' }}>
                <div>Total: <strong>{rows.length}</strong> registros analisados</div>
                <div>Filtrados: <strong>{filteredRows.length}</strong> | Pendentes: <strong>{rows.filter(r => r.status.includes('Pendente')).length}</strong></div>
            </div>

            <style dangerouslySetInnerHTML={{
                __html: `
                .grouped-row:hover { background: rgba(99, 102, 241, 0.1) !important; }
                tbody tr:hover { background: rgba(255,255,255,0.03); }
            `}} />
        </div>
    );
};

export default Conciliation;
