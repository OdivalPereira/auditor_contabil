import React, { useState } from 'react';
import api from '../api/client';
import {
    FileUp, FileCheck, AlertCircle, CheckCircle2,
    ArrowRight, Download, Activity, ShieldCheck
} from 'lucide-react';

const Extractor = () => {
    const [files, setFiles] = useState([]);
    const [results, setResults] = useState(null);
    const [loading, setLoading] = useState(false);
    const [syncLoading, setSyncLoading] = useState(false);
    const [status, setStatus] = useState({ type: '', msg: '' });

    const handleFileChange = (e) => {
        setFiles(Array.from(e.target.files));
    };

    const handleExtract = async () => {
        if (files.length === 0) return;
        setLoading(true);
        setStatus({ type: 'info', msg: 'Processando PDFs e validando saldos...' });

        const formData = new FormData();
        files.forEach(f => formData.append('files', f));

        try {
            const res = await api.post('/extract/', formData);
            setResults(res.data);
            setStatus({ type: 'success', msg: 'Processamento concluído com sucesso!' });
        } catch (err) {
            console.error(err);
            setStatus({ type: 'error', msg: 'Erro ao processar arquivos. Verifique os formatos.' });
        } finally {
            setLoading(false);
        }
    };

    const handleDownloadOFX = async () => {
        if (!results || !results.audit) return;

        // Consolidate all transactions from successful audits
        const allTransactions = results.audit.flatMap(a => a.transactions || []);

        try {
            const res = await api.post('/export/ofx', allTransactions, {
                responseType: 'blob'
            });
            const url = window.URL.createObjectURL(new Blob([res.data]));
            const link = document.createElement('a');
            link.href = url;
            link.setAttribute('download', 'extrato_unificado.ofx');
            document.body.appendChild(link);
            link.click();
            link.remove();
        } catch (err) {
            console.error(err);
            alert('Erro ao gerar OFX.');
        }
    };

    const handleSendToReconciler = async () => {
        if (!results) return;
        const allTransactions = results.audit.flatMap(a => a.transactions || []);

        setSyncLoading(true);
        try {
            await api.post('/extract/send-to-reconciler', allTransactions);
            setStatus({
                type: 'success',
                msg: `✅ ${allTransactions.length} transações enviadas para Auditoria! Os dados agora estão disponíveis na aba CONCILIAÇÃO para cruzamento com o Diário.`
            });
        } catch (err) {
            console.error(err);
            setStatus({ type: 'error', msg: 'Erro ao enviar dados para reconciliação.' });
        } finally {
            setSyncLoading(false);
        }
    };

    const AuditCard = ({ audit }) => {
        const isValid = audit.status === 'success';
        const isWarning = audit.status === 'warning';

        return (
            <div className="glass-panel" style={{ padding: '20px', marginBottom: '15px', borderLeft: `4px solid ${isValid ? '#10b981' : (isWarning ? '#f59e0b' : '#ef4444')}` }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
                    <div>
                        <h4 style={{ margin: '0 0 5px 0', fontSize: '1.1rem' }}>{audit.filename}</h4>
                        <p style={{ margin: 0, fontSize: '0.85rem', color: 'var(--text-secondary)' }}>
                            Banco: <span style={{ color: 'white' }}>{audit.bank}</span> |
                            Transações: <span style={{ color: 'white' }}>{audit.tx_count}</span>
                        </p>
                    </div>
                    {isValid ? <CheckCircle2 color="#10b981" size={24} /> : (isWarning ? <AlertCircle color="#f59e0b" size={24} /> : <AlertCircle color="#ef4444" size={24} />)}
                </div>

                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1.5fr', gap: '15px', marginTop: '15px', padding: '10px', background: 'rgba(0,0,0,0.2)', borderRadius: '8px' }}>
                    <div>
                        <caption style={{ display: 'block', textAlign: 'left', fontSize: '0.7rem', textTransform: 'uppercase', color: 'var(--text-secondary)' }}>Status Validação</caption>
                        <span style={{ fontSize: '0.85rem', fontWeight: 600, color: isValid ? '#10b981' : '#f87171' }}>
                            {audit.validation?.msg || (isValid ? 'Saldo Validado' : 'Erro de Saldo')}
                        </span>
                    </div>
                    <div>
                        <caption style={{ display: 'block', textAlign: 'left', fontSize: '0.7rem', textTransform: 'uppercase', color: 'var(--text-secondary)' }}>Saldos (Início/Fim)</caption>
                        <span style={{ fontSize: '0.85rem' }}>
                            R$ {audit.balances?.start?.toLocaleString('pt-BR')} / R$ {audit.balances?.end?.toLocaleString('pt-BR')}
                        </span>
                    </div>
                    <div style={{ textAlign: 'right' }}>
                        <caption style={{ display: 'block', textAlign: 'right', fontSize: '0.7rem', textTransform: 'uppercase', color: 'var(--text-secondary)' }}>Confiabilidade</caption>
                        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'flex-end', gap: 5 }}>
                            <div style={{ width: 60, height: 6, background: 'rgba(255,255,255,0.1)', borderRadius: 3, overflow: 'hidden' }}>
                                <div style={{ width: isValid ? '100%' : '40%', height: '100%', background: isValid ? 'var(--success)' : 'var(--danger)' }} />
                            </div>
                            <span style={{ fontSize: '0.75rem' }}>{isValid ? '100%' : 'Alta'}</span>
                        </div>
                    </div>
                </div>
            </div>
        );
    };

    return (
        <div style={{ maxWidth: '1000px', margin: '0 auto' }}>
            <div style={{ marginBottom: '30px' }}>
                <h1 style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
                    <ShieldCheck size={32} color="var(--accent-color)" />
                    Conversor Inteligente (PDF → OFX)
                </h1>
                <p style={{ color: 'var(--text-secondary)' }}>
                    Extração unificada de layouts bancários com validação matemática de saldos.
                </p>
            </div>

            {status.msg && (
                <div style={{
                    padding: '15px',
                    borderRadius: '8px',
                    marginBottom: '20px',
                    backgroundColor: status.type === 'error' ? 'rgba(239, 68, 68, 0.1)' : 'rgba(16, 185, 129, 0.1)',
                    color: status.type === 'error' ? '#fca5a5' : '#6ee7b7',
                    border: `1px solid ${status.type === 'error' ? 'rgba(239, 68, 68, 0.2)' : 'rgba(16, 185, 129, 0.2)'}`,
                    display: 'flex',
                    alignItems: 'center',
                    gap: 10
                }}>
                    {status.type === 'error' ? <AlertCircle size={20} /> : <CheckCircle2 size={20} />}
                    {status.msg}
                </div>
            )}

            <div className="glass-panel" style={{ padding: '30px', textAlign: 'center', marginBottom: '30px' }}>
                <div style={{ marginBottom: '20px' }}>
                    <FileUp size={48} color="var(--accent-color)" opacity={0.5} style={{ marginBottom: '10px' }} />
                    <h3>Selecione os Extratos Bancários</h3>
                    <p style={{ color: 'var(--text-secondary)', fontSize: '0.9rem' }}>Suporta PDFs do Itaú, Bradesco, BB, Santander, etc.</p>
                </div>

                <input
                    type="file"
                    id="pdf-upload"
                    multiple
                    accept=".pdf"
                    onChange={handleFileChange}
                    style={{ display: 'none' }}
                />
                <label className="btn-primary" htmlFor="pdf-upload" style={{ display: 'inline-flex', alignItems: 'center', gap: 8, cursor: 'pointer' }}>
                    <FileUp size={18} /> Escolher Arquivos
                </label>

                {files.length > 0 && (
                    <div style={{ marginTop: '20px' }}>
                        <div style={{ marginBottom: '15px', fontSize: '0.9rem' }}>
                            {files.length} arquivos selecionados
                        </div>
                        <button
                            className="btn-primary"
                            onClick={handleExtract}
                            disabled={loading}
                            style={{ padding: '12px 30px', fontSize: '1rem' }}
                        >
                            {loading ? (
                                <><Activity className="spin" size={18} style={{ marginRight: 8 }} /> Processando...</>
                            ) : (
                                <><ArrowRight size={18} style={{ marginRight: 8 }} /> Converter & Unificar</>
                            )}
                        </button>
                    </div>
                )}
            </div>

            {results && results.audit && (
                <div style={{ animation: 'fadeIn 0.5s ease-out' }}>
                    <h3 style={{ marginBottom: '15px' }}>📋 Relatório de Auditoria</h3>
                    {results.audit.map((a, i) => <AuditCard key={i} audit={a} />)}

                    <div className="glass-panel" style={{ padding: '20px', marginTop: '30px', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                        <div>
                            <h4 style={{ margin: 0 }}>Total Consolidado</h4>
                            <p style={{ margin: 0, color: 'var(--text-secondary)', fontSize: '0.9rem' }}>{results.count} transações prontas para exportação.</p>
                        </div>
                        <div style={{ display: 'flex', gap: '10px' }}>
                            <button className="btn-primary" onClick={handleDownloadOFX} style={{ background: 'rgba(255,255,255,0.1)', border: '1px solid rgba(255,255,255,0.2)' }}>
                                <Download size={18} style={{ marginRight: 8 }} /> Baixar OFX Unificado
                            </button>
                            <button className="btn-primary" onClick={handleSendToReconciler} disabled={syncLoading}>
                                {syncLoading ? (
                                    <><Activity className="spin" size={18} style={{ marginRight: 8 }} /> Sincronizando...</>
                                ) : (
                                    <><Activity size={18} style={{ marginRight: 8 }} /> Enviar para Auditoria</>
                                )}
                            </button>
                        </div>
                    </div>
                </div>
            )}
        </div>
    );
};

export default Extractor;
