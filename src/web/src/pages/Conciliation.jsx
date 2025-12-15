import React, { useEffect, useState, useMemo } from 'react';
import api from '../api/client';
import { Search, Filter } from 'lucide-react';
import clsx from 'clsx';

const Conciliation = () => {
    const [rows, setRows] = useState([]);
    const [loading, setLoading] = useState(false);

    // Filters
    const [filterStatus, setFilterStatus] = useState(['Pendente - Banco', 'Pendente - Diário']);
    const [searchTerm, setSearchTerm] = useState('');

    useEffect(() => {
        const loadData = async () => {
            setLoading(true);
            try {
                const res = await api.post('/reconcile/');
                if (res.data.rows) {
                    setRows(res.data.rows);
                }
            } catch (err) {
                console.error(err);
            } finally {
                setLoading(false);
            }
        };
        loadData();
    }, []);

    const filteredRows = useMemo(() => {
        return rows.filter(row => {
            // Status Filter
            if (!filterStatus.includes(row.status)) {
                // Check if it's a "Conciliado" type and if we want that
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
        // Map backend color_code to styles
        const code = row.color_code;
        if (code === 'matched_ledger') return { backgroundColor: 'rgba(5, 81, 96, 0.3)', color: '#a5f3fc' }; // Cyan tint
        if (code === 'matched_bank') return { backgroundColor: 'rgba(15, 81, 50, 0.3)', color: '#6ee7b7' }; // Green tint
        if (code === 'unmatched_ledger') return { backgroundColor: 'rgba(132, 32, 41, 0.3)', color: '#fca5a5' }; // Red tint
        if (code === 'unmatched_bank') return { backgroundColor: 'rgba(191, 54, 12, 0.3)', color: '#fdba74' }; // Orange tint
        return {};
    };

    return (
        <div>
            {/* Filters Bar */}
            <div className="glass-panel" style={{ padding: '20px', marginBottom: '20px', display: 'flex', gap: '20px', flexWrap: 'wrap', alignItems: 'center' }}>

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
                                fontSize: '0.9rem'
                            }}
                        >
                            {opt}
                        </button>
                    ))}
                </div>

                <div style={{ flex: 1, display: 'flex', justifyContent: 'flex-end', position: 'relative' }}>
                    <Search size={18} style={{ position: 'absolute', left: 10, top: '50%', transform: 'translateY(-50%)', color: 'rgba(255,255,255,0.5)' }} />
                    <input
                        type="text"
                        placeholder="Buscar descrição ou valor..."
                        value={searchTerm}
                        onChange={e => setSearchTerm(e.target.value)}
                        style={{
                            padding: '10px 10px 10px 35px',
                            background: 'rgba(0,0,0,0.3)',
                            border: '1px solid rgba(255,255,255,0.1)',
                            borderRadius: '8px',
                            color: 'white',
                            width: '300px'
                        }}
                    />
                </div>
            </div>

            {/* Table */}
            <div className="glass-panel" style={{ overflow: 'hidden' }}>
                <table className="data-table">
                    <thead style={{ background: 'rgba(0,0,0,0.3)' }}>
                        <tr>
                            <th>Data</th>
                            <th>Origem</th>
                            <th>Descrição</th>
                            <th>Valor</th>
                            <th>Status</th>
                            <th>ID Grupo</th>
                        </tr>
                    </thead>
                    <tbody>
                        {filteredRows.length === 0 ? (
                            <tr><td colSpan={6} style={{ textAlign: 'center', padding: 30 }}>Nenhum registro encontrado.</td></tr>
                        ) : (
                            filteredRows.map((row, idx) => (
                                <tr key={idx} style={getRowStyle(row)}>
                                    <td>{row.date}</td>
                                    <td>{row.source}</td>
                                    <td>{row.description}</td>
                                    <td style={{ fontWeight: 'bold' }}>
                                        {typeof row.amount === 'number' ? `R$ ${row.amount.toLocaleString('pt-BR', { minimumFractionDigits: 2 })}` : row.amount}
                                    </td>
                                    <td>
                                        <span style={{
                                            padding: '4px 8px',
                                            borderRadius: '4px',
                                            background: 'rgba(0,0,0,0.2)',
                                            fontSize: '0.8rem'
                                        }}>
                                            {row.status}
                                        </span>
                                    </td>
                                    <td style={{ fontFamily: 'monospace', opacity: 0.7 }}>
                                        {row.group_id !== "-1" ? row.group_id : '-'}
                                    </td>
                                </tr>
                            ))
                        )}
                    </tbody>
                </table>
            </div>
            <div style={{ padding: '10px', color: 'gray', textAlign: 'right' }}>
                {filteredRows.length} registros
            </div>
        </div>
    );
};

export default Conciliation;
