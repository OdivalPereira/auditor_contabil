import React, { useEffect, useState, useMemo } from 'react';
import api from '../api/client';
import { Search, Filter, Download, RefreshCw, Settings, Play } from 'lucide-react';

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
            // Pass tolerance as query param
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
            // Status Filter
            if (!filterStatus.includes(row.status)) {
                if (row.status.includes('Conciliado') && !filterStatus.includes('Conciliado')) return false;
            }

            // Search Filter
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

    const getRowStyle = (row) => {
        // Map backend color_code to styles with stronger contrast
        const code = row.color_code;
        const style = { borderBottom: '1px solid rgba(255,255,255,0.05)' };

        if (code === 'matched_ledger') {
            style.backgroundColor = 'rgba(5, 81, 96, 0.4)';
            style.color = '#a5f3fc';
        }
        else if (code === 'matched_bank') {
            style.backgroundColor = 'rgba(15, 81, 50, 0.4)';
            style.color = '#6ee7b7';
        }
        else if (code === 'unmatched_ledger') {
            style.backgroundColor = 'rgba(132, 32, 41, 0.4)';
            style.color = '#fca5a5';
        }
        else if (code === 'unmatched_bank') {
            style.backgroundColor = 'rgba(191, 54, 12, 0.4)';
            style.color = '#fdba74';
        }

        // Group borders
        if (row.group_id !== "-1") {
            style.borderLeft = '4px solid rgba(255, 255, 255, 0.3)';
        }

        return style;
    };

    const handleDownload = (type) => {
        // Direct link download
        const url = `/api/export/${type}`;
        window.open(url, '_blank');
    };

    return (
        <div>
            {/* Control Bar */}
            <div className="glass-panel" style={{ padding: '20px', marginBottom: '20px' }}>
                <div style={{ display: 'flex', gap: '20px', flexWrap: 'wrap', alignItems: 'center' }}>

                    {/* Filters */}
                    <div style={{ display: 'flex', gap: '10px', alignItems: 'center' }}>
                        <Filter size={18} />
                        <span style={{ fontWeight: 600 }}>Filtros:</span>
                        {statusOptions.map(opt => (
                            <button
                                key={opt}
                                onClick={() => toggleFilter(opt)}
                                style={{
                                    background: filterStatus.includes(opt) ? 'var(--accent-color)' : 'rgba(255,255,255,0.1)',
                                    border: 'none',
                                    color: 'white',
                                    padding: '6px 12px',
                                    borderRadius: '20px',
                                    cursor: 'pointer',
                                    fontSize: '0.9rem',
                                    transition: 'background 0.2s'
                                }}
                            >
                                {opt}
                            </button>
                        ))}
                    </div>

                    <div style={{ borderLeft: '1px solid rgba(255,255,255,0.1)', height: 24, margin: '0 10px' }}></div>

                    {/* Settings Toggle */}
                    <button
                        onClick={() => setShowSettings(!showSettings)}
                        style={{
                            background: showSettings ? 'rgba(255,255,255,0.2)' : 'transparent',
                            border: '1px solid rgba(255,255,255,0.2)',
                            color: 'white',
                            padding: '6px 10px',
                            borderRadius: '8px',
                            cursor: 'pointer',
                            display: 'flex', alignItems: 'center', gap: 6
                        }}
                    >
                        <Settings size={16} /> Config
                    </button>

                    {/* Spacer */}
                    <div style={{ flex: 1 }} />

                    {/* Exports */}
                    <div style={{ display: 'flex', gap: '10px' }}>
                        <button className="btn-primary" onClick={() => handleDownload('excel')} style={{ display: 'flex', alignItems: 'center', backgroundColor: '#10b981', backgroundImage: 'none', padding: '6px 12px', fontSize: '0.9rem' }}>
                            <Download size={14} style={{ marginRight: 6 }} /> Excel
                        </button>
                        <button className="btn-primary" onClick={() => handleDownload('pdf')} style={{ display: 'flex', alignItems: 'center', backgroundColor: '#ef4444', backgroundImage: 'none', padding: '6px 12px', fontSize: '0.9rem' }}>
                            <Download size={14} style={{ marginRight: 6 }} /> PDF
                        </button>
                    </div>
                </div>

                {/* Expanded Settings Area */}
                {showSettings && (
                    <div style={{ marginTop: 20, paddingTop: 15, borderTop: '1px solid rgba(255,255,255,0.1)', display: 'flex', alignItems: 'center', gap: 20, animation: 'fadeIn 0.3s' }}>
                        <div style={{ display: 'flex', flexDirection: 'column', gap: 5 }}>
                            <label style={{ fontSize: '0.9rem', color: '#cbd5e1' }}>Tolerância de Datas (Dias): <strong style={{ color: 'white' }}>{tolerance}</strong></label>
                            <input
                                type="range"
                                min="0" max="60"
                                value={tolerance}
                                onChange={(e) => setTolerance(parseInt(e.target.value))}
                                style={{ width: 200 }}
                            />
                        </div>
                        <button
                            className="btn-primary"
                            onClick={handleReprocess}
                            disabled={loading}
                            style={{ display: 'flex', alignItems: 'center', padding: '8px 16px' }}
                        >
                            {loading ? <RefreshCw size={16} className="spin" /> : <Play size={16} style={{ marginRight: 8 }} />}
                            Re-processar Conciliação
                        </button>
                    </div>
                )}
            </div>

            {/* Search Bar */}
            <div style={{ marginBottom: '15px' }}>
                <div style={{ position: 'relative', maxWidth: '400px' }}>
                    <Search size={18} style={{ position: 'absolute', left: 10, top: '50%', transform: 'translateY(-50%)', color: 'rgba(255,255,255,0.5)' }} />
                    <input
                        type="text"
                        placeholder="Buscar descrição, valor ou grupo..."
                        value={searchTerm}
                        onChange={e => setSearchTerm(e.target.value)}
                        style={{
                            padding: '10px 10px 10px 35px',
                            background: 'rgba(0,0,0,0.3)',
                            border: '1px solid rgba(255,255,255,0.1)',
                            borderRadius: '8px',
                            color: 'white',
                            width: '100%',
                            fontSize: '1rem'
                        }}
                    />
                </div>
            </div>

            {/* Table */}
            <div className="glass-panel" style={{ overflowX: 'auto', minHeight: 400, position: 'relative' }}>
                {loading && (
                    <div style={{ position: 'absolute', inset: 0, background: 'rgba(0,0,0,0.5)', display: 'flex', justifyContent: 'center', alignItems: 'center', zIndex: 10 }}>
                        <RefreshCw size={40} className="spin" style={{ color: 'var(--accent-color)' }} />
                    </div>
                )}

                <table className="data-table">
                    <thead style={{ background: 'rgba(0,0,0,0.4)' }}>
                        <tr>
                            <th style={{ width: '120px' }}>Data</th>
                            <th style={{ width: '100px' }}>Origem</th>
                            <th>Descrição</th>
                            <th style={{ width: '150px' }}>Valor</th>
                            <th style={{ width: '160px' }}>Status</th>
                            <th style={{ width: '100px' }}>Grupo</th>
                        </tr>
                    </thead>
                    <tbody>
                        {filteredRows.length === 0 ? (
                            <tr><td colSpan={6} style={{ textAlign: 'center', padding: 40, opacity: 0.6 }}>Nenhum registro encontrado.</td></tr>
                        ) : (
                            filteredRows.map((row, idx) => (
                                <tr key={idx} style={getRowStyle(row)}>
                                    <td>{row.date}</td>
                                    <td>{row.source}</td>
                                    <td>{row.description}</td>
                                    <td style={{ fontWeight: 'bold', fontFamily: 'monospace', fontSize: '1.05rem' }}>
                                        {typeof row.amount === 'number' ? `R$ ${row.amount.toLocaleString('pt-BR', { minimumFractionDigits: 2 })}` : row.amount}
                                    </td>
                                    <td>
                                        <span style={{
                                            padding: '4px 8px',
                                            borderRadius: '4px',
                                            background: 'rgba(0,0,0,0.2)',
                                            fontSize: '0.8rem',
                                            fontWeight: 500
                                        }}>
                                            {row.status}
                                        </span>
                                    </td>
                                    <td style={{ fontFamily: 'monospace', opacity: 0.7 }}>
                                        {row.group_id !== "-1" ? row.group_id : ''}
                                    </td>
                                </tr>
                            ))
                        )}
                    </tbody>
                </table>
            </div>

            <div style={{ padding: '15px 0', color: '#94a3b8', textAlign: 'right', fontSize: '0.9rem' }}>
                Exibindo {filteredRows.length} de {rows.length} transações
            </div>
        </div>
    );
};

export default Conciliation;
