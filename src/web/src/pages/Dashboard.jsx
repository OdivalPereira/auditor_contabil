import React, { useEffect, useState, useMemo } from 'react';
import api from '../api/client';
import { useApp } from '../AppContext';
import {
    LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer,
    PieChart, Pie, Cell
} from 'recharts';
import { Activity, Archive, AlertTriangle, CheckCheck, PieChart as PieIcon } from 'lucide-react';

const Dashboard = () => {
    const { reconcileResults, setReconcileResults, uploadStatus, refreshUploadStatus, lastTolerance } = useApp();
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState('');

    const fetchData = async () => {
        if (uploadStatus.ledger_count === 0) {
            await refreshUploadStatus();
        }

        setLoading(true);
        setError('');
        try {
            const res = await api.post(`/reconcile/?tolerance=${lastTolerance}`);
            if (res.data.error) {
                console.warn(res.data.error);
            } else {
                setReconcileResults(res.data);
            }
        } catch (err) {
            console.error(err);
            setError('Erro ao carregar dados. Tente novamente.');
        } finally {
            setLoading(false);
        }
    };

    useEffect(() => {
        // If we don't have results but we have uploaded files, fetch.
        if (!reconcileResults) {
            fetchData();
        }
    }, []);

    const data = reconcileResults;

    // Compute Pie Data
    const pieData = useMemo(() => {
        if (!data?.rows) return [];

        const counts = {
            'Conciliado': 0,
            'Pendente - Banco': 0,
            'Pendente - Diário': 0
        };

        data.rows.forEach(r => {
            if ((r.status || '').includes('Conciliado')) counts['Conciliado']++;
            else if ((r.status || '').includes('Banco')) counts['Pendente - Banco']++;
            else if ((r.status || '').includes('Diário')) counts['Pendente - Diário']++;
        });

        return [
            { name: 'Conciliado', value: counts['Conciliado'], color: '#10b981' }, // Green
            { name: 'Pendente Banco', value: counts['Pendente - Banco'], color: '#ef4444' }, // Red
            { name: 'Pendente Diário', value: counts['Pendente - Diário'], color: '#f59e0b' } // Amber
        ].filter(d => d.value > 0);
    }, [data]);

    const MetricCard = ({ title, value, sub, icon: Icon, color }) => (
        <div className="glass-panel" style={{ padding: '20px', display: 'flex', alignItems: 'center' }}>
            <div style={{
                background: `rgba(${color}, 0.2)`,
                padding: '12px',
                borderRadius: '12px',
                marginRight: '15px'
            }}>
                <Icon size={24} style={{ color: `rgb(${color})` }} />
            </div>
            <div>
                <p style={{ margin: 0, color: 'var(--text-secondary)', fontSize: '0.9rem' }}>{title}</p>
                <h3 style={{ margin: '5px 0', fontSize: '1.5rem' }}>{value}</h3>
                {sub && <p style={{ margin: 0, fontSize: '0.8rem', opacity: 0.7 }}>{sub}</p>}
            </div>
        </div>
    );

    const CustomTooltip = ({ active, payload, label }) => {
        if (active && payload && payload.length) {
            return (
                <div style={{ background: '#1e293b', padding: '10px', borderRadius: '8px', border: '1px solid rgba(255,255,255,0.1)' }}>
                    <p style={{ margin: 0, fontWeight: 'bold', marginBottom: 5 }}>{label}</p>
                    {payload.map((entry, index) => (
                        <p key={index} style={{ margin: 0, color: entry.color, fontSize: '0.9rem' }}>
                            {entry.name}: {typeof entry.value === 'number' ? `R$ ${entry.value.toLocaleString('pt-BR')}` : entry.value}
                        </p>
                    ))}
                </div>
            );
        }
        return null;
    };

    if (loading) return (
        <div style={{ height: '100%', display: 'flex', justifyContent: 'center', alignItems: 'center' }}>
            <div style={{ textAlign: 'center' }}>
                <Activity size={40} className="spin" style={{ color: 'var(--accent-color)', marginBottom: 20 }} />
                <h3>Analisando Transações...</h3>
            </div>
        </div>
    );

    if (!data && !loading) return (
        <div style={{ textAlign: 'center', marginTop: 100 }}>
            <div className="glass-panel" style={{ display: 'inline-block', padding: 40 }}>
                <Archive size={60} style={{ color: 'var(--accent-color)', marginBottom: 20 }} opacity={0.5} />
                <h2>Bem-vindo ao Auditor Contábil</h2>
                <p style={{ color: 'var(--text-secondary)' }}>Nenhum dado carregado ou processado. Comece pela aba <strong style={{ color: 'white' }}>Dados e Upload</strong>.</p>
            </div>
        </div>
    );

    const metrics = data?.metrics || {};
    const chartData = data?.chart || [];

    return (
        <div>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '30px' }}>
                <h1>Dashboard Financeiro</h1>
                <button className="btn-primary" onClick={fetchData} style={{ display: 'flex', alignItems: 'center' }}>
                    <Activity size={16} style={{ marginRight: 8 }} /> Atualizar Análise
                </button>
            </div>

            {/* Metrics Grid */}
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: '20px', marginBottom: '30px' }}>
                <MetricCard
                    title="Lançamentos Diário"
                    value={metrics.ledger_total}
                    icon={Archive}
                    color="99, 102, 241"
                />
                <MetricCard
                    title="Transações Banco"
                    value={metrics.bank_total}
                    icon={Activity}
                    color="16, 185, 129"
                />
                <MetricCard
                    title="Diferença Inicial"
                    value={`R$ ${metrics.diff_initial?.toLocaleString('pt-BR', { minimumFractionDigits: 2 })}`}
                    icon={AlertTriangle}
                    color="239, 68, 68"
                />
                <MetricCard
                    title="Diferença Final"
                    value={`R$ ${metrics.diff_final?.toLocaleString('pt-BR', { minimumFractionDigits: 2 })}`}
                    sub={`${metrics.comb_count} combinações achadas`}
                    icon={CheckCheck}
                    color="245, 158, 11"
                />
            </div>

            {/* Charts Row */}
            <div style={{ display: 'grid', gridTemplateColumns: '2fr 1fr', gap: '20px', marginBottom: 30 }}>
                {/* Evolution Chart */}
                <div className="glass-panel" style={{ padding: '25px', height: '400px' }}>
                    <h3 style={{ marginBottom: '20px', display: 'flex', alignItems: 'center' }}>
                        <Activity size={20} style={{ marginRight: 10, color: 'var(--accent-color)' }} />
                        Evolução Diária (Soma)
                    </h3>
                    <ResponsiveContainer width="100%" height="85%">
                        <LineChart data={chartData}>
                            <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.05)" />
                            <XAxis dataKey="date" stroke="#94a3b8" fontSize={12} tickFormatter={(str) => str ? str.split('-').slice(1).join('/') : ''} />
                            <YAxis stroke="#94a3b8" fontSize={12} tickFormatter={(val) => `R$${val / 1000}k`} />
                            <Tooltip content={<CustomTooltip />} />
                            <Legend wrapperStyle={{ paddingTop: 10 }} />
                            <Line type="monotone" dataKey="ledger" name="Diário" stroke="#6366f1" strokeWidth={3} dot={{ r: 3, fill: '#6366f1' }} activeDot={{ r: 8 }} />
                            <Line type="monotone" dataKey="bank" name="Banco" stroke="#10b981" strokeWidth={3} dot={{ r: 3, fill: '#10b981' }} activeDot={{ r: 8 }} />
                        </LineChart>
                    </ResponsiveContainer>
                </div>

                {/* Distribution Pie Chart */}
                <div className="glass-panel" style={{ padding: '25px', height: '400px' }}>
                    <h3 style={{ marginBottom: '20px', display: 'flex', alignItems: 'center' }}>
                        <PieIcon size={20} style={{ marginRight: 10, color: '#f59e0b' }} />
                        Distribuição
                    </h3>
                    <ResponsiveContainer width="100%" height="85%">
                        <PieChart>
                            <Pie
                                data={pieData}
                                cx="50%"
                                cy="50%"
                                innerRadius={60}
                                outerRadius={80}
                                paddingAngle={5}
                                dataKey="value"
                            >
                                {pieData.map((entry, index) => (
                                    <Cell key={`cell-${index}`} fill={entry.color} />
                                ))}
                            </Pie>
                            <Tooltip
                                contentStyle={{ backgroundColor: '#1e293b', border: 'none', borderRadius: '8px' }}
                                itemStyle={{ color: 'white' }}
                            />
                            <Legend layout="vertical" verticalAlign="middle" align="bottom" wrapperStyle={{ fontSize: '0.8rem' }} />
                        </PieChart>
                    </ResponsiveContainer>
                </div>
            </div>
        </div>
    );
};

export default Dashboard;
