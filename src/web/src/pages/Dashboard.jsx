import React, { useEffect, useState } from 'react';
import api from '../api/client';
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer } from 'recharts';
import { Activity, Archive, AlertTriangle, CheckCheck } from 'lucide-react';

const Dashboard = () => {
    const [data, setData] = useState(null);
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState('');

    const fetchData = async () => {
        setLoading(true);
        setError('');
        try {
            const res = await api.post('/reconcile/'); // Trigger reconcile to get fresh stats
            if (res.data.error) {
                // Determine if it's just missing data
                console.warn(res.data.error);
            } else {
                setData(res.data);
            }
        } catch (err) {
            console.error(err);
            setError('Erro ao carregar dados. Verifique se os arquivos foram importados.');
        } finally {
            setLoading(false);
        }
    };

    useEffect(() => {
        fetchData();
    }, []);

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

    if (loading) return <div style={{ padding: 40, textAlign: 'center' }}>Carregando análise...</div>;

    if (!data && !loading) return (
        <div style={{ textAlign: 'center', marginTop: 100 }}>
            <h2>Bem-vindo ao Auditor Contábil</h2>
            <p>Comece importando seus arquivos na aba "Dados e Upload".</p>
        </div>
    );

    // Safety check if data is partial
    const metrics = data?.metrics || {};
    const chartData = data?.chart || [];

    return (
        <div>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '30px' }}>
                <h1>Dashboard Financeiro</h1>
                <button className="btn-primary" onClick={fetchData}>Atualizar Análise</button>
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

            {/* Chart Section */}
            <div className="glass-panel" style={{ padding: '25px', height: '400px' }}>
                <h3 style={{ marginBottom: '20px' }}>Evolução de Movimentações (Diário vs Banco)</h3>
                <ResponsiveContainer width="100%" height="100%">
                    <LineChart data={chartData}>
                        <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.1)" />
                        <XAxis dataKey="date" stroke="#94a3b8" />
                        <YAxis stroke="#94a3b8" />
                        <Tooltip
                            contentStyle={{ backgroundColor: '#1e293b', border: 'none', borderRadius: '8px' }}
                        />
                        <Legend />
                        <Line type="monotone" dataKey="ledger" name="Diário" stroke="#6366f1" strokeWidth={3} dot={{ r: 4 }} />
                        <Line type="monotone" dataKey="bank" name="Banco" stroke="#10b981" strokeWidth={3} dot={{ r: 4 }} />
                    </LineChart>
                </ResponsiveContainer>
            </div>
        </div>
    );
};

export default Dashboard;
