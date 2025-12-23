import React, { useEffect, useState } from 'react';
import api from '../api/client';
import { Download, Plus, Edit2, Trash2, FileText, AlertCircle, CheckCircle2 } from 'lucide-react';

function ExportLancamentos() {
    const [bankTransactions, setBankTransactions] = useState([]);
    const [manualTransactions, setManualTransactions] = useState([]);
    const [selectedIds, setSelectedIds] = useState(new Set());
    const [loading, setLoading] = useState(false);
    const [showAddModal, setShowAddModal] = useState(false);
    const [editingId, setEditingId] = useState(null);
    const [searchTerm, setSearchTerm] = useState('');
    const [notification, setNotification] = useState(null);

    // Form state
    const [formData, setFormData] = useState({
        date: '',
        amount: '',
        description: '',
        conta_debito: '78',
        participante_debito: '',
        conta_credito: '6670',
        participante_credito: '',
        documento: '001'
    });

    useEffect(() => {
        loadTransactions();
    }, []);

    const loadTransactions = async () => {
        setLoading(true);
        try {
            const [bankRes, manualRes] = await Promise.all([
                api.get('/export-lancamentos/bank-only'),
                api.get('/export-lancamentos/manual')
            ]);
            setBankTransactions(bankRes.data.transactions || []);
            setManualTransactions(manualRes.data.transactions || []);
        } catch (error) {
            console.error('Error loading transactions:', error);
            showNotification('Erro ao carregar transações', 'error');
        } finally {
            setLoading(false);
        }
    };

    const showNotification = (message, type = 'success') => {
        setNotification({ message, type });
        setTimeout(() => setNotification(null), 3000);
    };

    const handleSelectAll = (checked) => {
        if (checked) {
            const allIds = new Set([
                ...bankTransactions.map(t => t.id),
                ...manualTransactions.map(t => t.id)
            ]);
            setSelectedIds(allIds);
        } else {
            setSelectedIds(new Set());
        }
    };

    const handleSelectTransaction = (id) => {
        const newSelected = new Set(selectedIds);
        if (newSelected.has(id)) {
            newSelected.delete(id);
        } else {
            newSelected.add(id);
        }
        setSelectedIds(newSelected);
    };

    const handleEditTransaction = async (id, edits) => {
        try {
            await api.put(`/export-lancamentos/edit/${id}`, edits);
            showNotification('Transação editada com sucesso');
            loadTransactions();
            setEditingId(null);
        } catch (error) {
            console.error('Error editing transaction:', error);
            showNotification('Erro ao editar transação', 'error');
        }
    };

    const handleAddManual = async (e) => {
        e.preventDefault();
        try {
            await api.post('/export-lancamentos/manual', formData);
            showNotification('Lançamento adicionado com sucesso');
            setShowAddModal(false);
            resetForm();
            loadTransactions();
        } catch (error) {
            console.error('Error adding manual transaction:', error);
            showNotification('Erro ao adicionar lançamento', 'error');
        }
    };

    const handleDeleteManual = async (id) => {
        if (!confirm('Deseja realmente excluir este lançamento?')) return;

        try {
            await api.delete(`/export-lancamentos/manual/${id}`);
            showNotification('Lançamento excluído');
            loadTransactions();
            // Remove from selected if was selected
            const newSelected = new Set(selectedIds);
            newSelected.delete(id);
            setSelectedIds(newSelected);
        } catch (error) {
            console.error('Error deleting transaction:', error);
            showNotification('Erro ao excluir lançamento', 'error');
        }
    };

    const handleExport = async () => {
        if (selectedIds.size === 0) {
            showNotification('Selecione pelo menos uma transação', 'error');
            return;
        }

        try {
            setLoading(true);
            const response = await api.post('/export-lancamentos/generate', {
                selected_ids: Array.from(selectedIds)
            }, {
                responseType: 'blob'
            });

            // Create download link
            const url = window.URL.createObjectURL(new Blob([response.data]));
            const link = document.createElement('a');
            link.href = url;

            // Extract filename from Content-Disposition header
            const contentDisposition = response.headers['content-disposition'];
            const filename = contentDisposition
                ? contentDisposition.split('filename=')[1].replace(/"/g, '')
                : 'lancamentos.txt';

            link.setAttribute('download', filename);
            document.body.appendChild(link);
            link.click();
            link.remove();
            window.URL.revokeObjectURL(url);

            showNotification('Arquivo exportado com sucesso');
        } catch (error) {
            console.error('Error exporting:', error);
            showNotification('Erro ao exportar arquivo', 'error');
        } finally {
            setLoading(false);
        }
    };

    const resetForm = () => {
        setFormData({
            date: '',
            amount: '',
            description: '',
            conta_debito: '78',
            participante_debito: '',
            conta_credito: '6670',
            participante_credito: '',
            documento: '001'
        });
    };

    const allTransactions = [...bankTransactions, ...manualTransactions];
    const filteredTransactions = allTransactions.filter(t =>
        t.description.toLowerCase().includes(searchTerm.toLowerCase())
    );

    return (
        <div style={{ padding: '20px' }}>
            {/* Header */}
            <div style={{ marginBottom: '30px' }}>
                <h1 style={{ fontSize: '2rem', fontWeight: 'bold', marginBottom: '10px', color: '#1e293b' }}>
                    Exportar Lançamentos
                </h1>
                <p style={{ color: '#64748b' }}>
                    Selecione e exporte transações que estão apenas no extrato bancário
                </p>
            </div>

            {/* Notification */}
            {notification && (
                <div style={{
                    position: 'fixed',
                    top: '20px',
                    right: '20px',
                    padding: '15px 20px',
                    borderRadius: '8px',
                    background: notification.type === 'error' ? '#fee2e2' : '#d1fae5',
                    color: notification.type === 'error' ? '#991b1b' : '#065f46',
                    display: 'flex',
                    alignItems: 'center',
                    gap: '10px',
                    boxShadow: '0 4px 6px rgba(0,0,0,0.1)',
                    zIndex: 1000
                }}>
                    {notification.type === 'error' ? <AlertCircle size={20} /> : <CheckCircle2 size={20} />}
                    {notification.message}
                </div>
            )}

            {/* Actions Bar */}
            <div style={{
                display: 'flex',
                gap: '15px',
                marginBottom: '20px',
                flexWrap: 'wrap',
                alignItems: 'center'
            }}>
                <button
                    onClick={() => setShowAddModal(true)}
                    style={{
                        padding: '10px 20px',
                        background: 'linear-gradient(135deg, #3b82f6 0%, #2563eb 100%)',
                        color: 'white',
                        border: 'none',
                        borderRadius: '8px',
                        cursor: 'pointer',
                        display: 'flex',
                        alignItems: 'center',
                        gap: '8px',
                        fontWeight: '500',
                        transition: 'transform 0.2s'
                    }}
                    onMouseEnter={e => e.currentTarget.style.transform = 'translateY(-2px)'}
                    onMouseLeave={e => e.currentTarget.style.transform = 'translateY(0)'}
                >
                    <Plus size={18} />
                    Adicionar Lançamento
                </button>

                <button
                    onClick={handleExport}
                    disabled={selectedIds.size === 0 || loading}
                    style={{
                        padding: '10px 20px',
                        background: selectedIds.size > 0 ? 'linear-gradient(135deg, #10b981 0%, #059669 100%)' : '#e2e8f0',
                        color: selectedIds.size > 0 ? 'white' : '#94a3b8',
                        border: 'none',
                        borderRadius: '8px',
                        cursor: selectedIds.size > 0 ? 'pointer' : 'not-allowed',
                        display: 'flex',
                        alignItems: 'center',
                        gap: '8px',
                        fontWeight: '500',
                        transition: 'transform 0.2s'
                    }}
                    onMouseEnter={e => selectedIds.size > 0 && (e.currentTarget.style.transform = 'translateY(-2px)')}
                    onMouseLeave={e => e.currentTarget.style.transform = 'translateY(0)'}
                >
                    <Download size={18} />
                    Exportar ({selectedIds.size})
                </button>

                <input
                    type="text"
                    placeholder="Buscar por descrição..."
                    value={searchTerm}
                    onChange={e => setSearchTerm(e.target.value)}
                    style={{
                        padding: '10px 15px',
                        border: '1px solid #e2e8f0',
                        borderRadius: '8px',
                        flex: '1',
                        minWidth: '200px',
                        fontSize: '0.95rem'
                    }}
                />
            </div>

            {/* Stats */}
            <div style={{
                display: 'grid',
                gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))',
                gap: '15px',
                marginBottom: '25px'
            }}>
                <div style={{
                    padding: '20px',
                    background: 'linear-gradient(135deg, #fff7ed 0%, #ffedd5 100%)',
                    borderRadius: '12px',
                    border: '1px solid #fed7aa'
                }}>
                    <div style={{ fontSize: '0.875rem', color: '#9a3412', marginBottom: '5px' }}>
                        Do Banco
                    </div>
                    <div style={{ fontSize: '1.75rem', fontWeight: 'bold', color: '#c2410c' }}>
                        {bankTransactions.length}
                    </div>
                </div>
                <div style={{
                    padding: '20px',
                    background: 'linear-gradient(135deg, #dbeafe 0%, #bfdbfe 100%)',
                    borderRadius: '12px',
                    border: '1px solid #93c5fd'
                }}>
                    <div style={{ fontSize: '0.875rem', color: '#1e3a8a', marginBottom: '5px' }}>
                        Manuais
                    </div>
                    <div style={{ fontSize: '1.75rem', fontWeight: 'bold', color: '#1e40af' }}>
                        {manualTransactions.length}
                    </div>
                </div>
                <div style={{
                    padding: '20px',
                    background: 'linear-gradient(135deg, #d1fae5 0%, #a7f3d0 100%)',
                    borderRadius: '12px',
                    border: '1px solid #6ee7b7'
                }}>
                    <div style={{ fontSize: '0.875rem', color: '#065f46', marginBottom: '5px' }}>
                        Selecionadas
                    </div>
                    <div style={{ fontSize: '1.75rem', fontWeight: 'bold', color: '#047857' }}>
                        {selectedIds.size}
                    </div>
                </div>
            </div>

            {/* Table */}
            <div style={{
                background: 'white',
                borderRadius: '12px',
                boxShadow: '0 1px 3px rgba(0,0,0,0.1)',
                overflow: 'hidden'
            }}>
                <table style={{ width: '100%', borderCollapse: 'collapse' }}>
                    <thead>
                        <tr style={{ background: '#f8fafc', borderBottom: '2px solid #e2e8f0' }}>
                            <th style={{ padding: '15px', textAlign: 'left' }}>
                                <input
                                    type="checkbox"
                                    checked={selectedIds.size === allTransactions.length && allTransactions.length > 0}
                                    onChange={e => handleSelectAll(e.target.checked)}
                                    style={{ cursor: 'pointer' }}
                                />
                            </th>
                            <th style={{ padding: '15px', textAlign: 'left', fontWeight: '600', color: '#475569' }}>Data</th>
                            <th style={{ padding: '15px', textAlign: 'right', fontWeight: '600', color: '#475569' }}>Valor</th>
                            <th style={{ padding: '15px', textAlign: 'left', fontWeight: '600', color: '#475569' }}>Descrição</th>
                            <th style={{ padding: '15px', textAlign: 'center', fontWeight: '600', color: '#475569' }}>Débito</th>
                            <th style={{ padding: '15px', textAlign: 'center', fontWeight: '600', color: '#475569' }}>Crédito</th>
                            <th style={{ padding: '15px', textAlign: 'center', fontWeight: '600', color: '#475569' }}>Doc</th>
                            <th style={{ padding: '15px', textAlign: 'center', fontWeight: '600', color: '#475569' }}>Origem</th>
                            <th style={{ padding: '15px', textAlign: 'center', fontWeight: '600', color: '#475569' }}>Ações</th>
                        </tr>
                    </thead>
                    <tbody>
                        {filteredTransactions.length === 0 ? (
                            <tr>
                                <td colSpan="9" style={{ padding: '40px', textAlign: 'center', color: '#94a3b8' }}>
                                    <FileText size={48} style={{ margin: '0 auto 10px', opacity: 0.3 }} />
                                    <div>Nenhuma transação para exportar</div>
                                </td>
                            </tr>
                        ) : (
                            filteredTransactions.map(txn => (
                                <TransactionRow
                                    key={txn.id}
                                    transaction={txn}
                                    isSelected={selectedIds.has(txn.id)}
                                    onSelect={() => handleSelectTransaction(txn.id)}
                                    onEdit={handleEditTransaction}
                                    onDelete={handleDeleteManual}
                                    isEditing={editingId === txn.id}
                                    setIsEditing={setEditingId}
                                />
                            ))
                        )}
                    </tbody>
                </table>
            </div>

            {/* Add Modal */}
            {showAddModal && (
                <div style={{
                    position: 'fixed',
                    top: 0,
                    left: 0,
                    right: 0,
                    bottom: 0,
                    background: 'rgba(0,0,0,0.5)',
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    zIndex: 1000
                }}>
                    <div style={{
                        background: 'white',
                        borderRadius: '12px',
                        padding: '30px',
                        maxWidth: '600px',
                        width: '90%',
                        maxHeight: '90vh',
                        overflow: 'auto'
                    }}>
                        <h2 style={{ marginBottom: '20px', fontSize: '1.5rem', fontWeight: 'bold', color: '#1e293b' }}>
                            Adicionar Lançamento Manual
                        </h2>
                        <form onSubmit={handleAddManual}>
                            <div style={{ display: 'grid', gap: '15px' }}>
                                <div>
                                    <label style={{ display: 'block', marginBottom: '5px', fontSize: '0.875rem', fontWeight: '500', color: '#475569' }}>
                                        Data
                                    </label>
                                    <input
                                        type="date"
                                        required
                                        value={formData.date}
                                        onChange={e => setFormData({ ...formData, date: e.target.value })}
                                        style={{ width: '100%', padding: '10px', border: '1px solid #e2e8f0', borderRadius: '6px' }}
                                    />
                                </div>
                                <div>
                                    <label style={{ display: 'block', marginBottom: '5px', fontSize: '0.875rem', fontWeight: '500', color: '#475569' }}>
                                        Valor
                                    </label>
                                    <input
                                        type="number"
                                        step="0.01"
                                        required
                                        value={formData.amount}
                                        onChange={e => setFormData({ ...formData, amount: e.target.value })}
                                        style={{ width: '100%', padding: '10px', border: '1px solid #e2e8f0', borderRadius: '6px' }}
                                    />
                                </div>
                                <div>
                                    <label style={{ display: 'block', marginBottom: '5px', fontSize: '0.875rem', fontWeight: '500', color: '#475569' }}>
                                        Descrição/Histórico
                                    </label>
                                    <textarea
                                        required
                                        value={formData.description}
                                        onChange={e => setFormData({ ...formData, description: e.target.value })}
                                        rows={3}
                                        style={{ width: '100%', padding: '10px', border: '1px solid #e2e8f0', borderRadius: '6px', fontFamily: 'inherit' }}
                                    />
                                </div>
                                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '15px' }}>
                                    <div>
                                        <label style={{ display: 'block', marginBottom: '5px', fontSize: '0.875rem', fontWeight: '500', color: '#475569' }}>
                                            Conta Débito
                                        </label>
                                        <input
                                            type="text"
                                            required
                                            value={formData.conta_debito}
                                            onChange={e => setFormData({ ...formData, conta_debito: e.target.value })}
                                            style={{ width: '100%', padding: '10px', border: '1px solid #e2e8f0', borderRadius: '6px' }}
                                        />
                                    </div>
                                    <div>
                                        <label style={{ display: 'block', marginBottom: '5px', fontSize: '0.875rem', fontWeight: '500', color: '#475569' }}>
                                            Participante Débito
                                        </label>
                                        <input
                                            type="text"
                                            value={formData.participante_debito}
                                            onChange={e => setFormData({ ...formData, participante_debito: e.target.value })}
                                            style={{ width: '100%', padding: '10px', border: '1px solid #e2e8f0', borderRadius: '6px' }}
                                        />
                                    </div>
                                </div>
                                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '15px' }}>
                                    <div>
                                        <label style={{ display: 'block', marginBottom: '5px', fontSize: '0.875rem', fontWeight: '500', color: '#475569' }}>
                                            Conta Crédito
                                        </label>
                                        <input
                                            type="text"
                                            required
                                            value={formData.conta_credito}
                                            onChange={e => setFormData({ ...formData, conta_credito: e.target.value })}
                                            style={{ width: '100%', padding: '10px', border: '1px solid #e2e8f0', borderRadius: '6px' }}
                                        />
                                    </div>
                                    <div>
                                        <label style={{ display: 'block', marginBottom: '5px', fontSize: '0.875rem', fontWeight: '500', color: '#475569' }}>
                                            Participante Crédito
                                        </label>
                                        <input
                                            type="text"
                                            value={formData.participante_credito}
                                            onChange={e => setFormData({ ...formData, participante_credito: e.target.value })}
                                            style={{ width: '100%', padding: '10px', border: '1px solid #e2e8f0', borderRadius: '6px' }}
                                        />
                                    </div>
                                </div>
                                <div>
                                    <label style={{ display: 'block', marginBottom: '5px', fontSize: '0.875rem', fontWeight: '500', color: '#475569' }}>
                                        Documento
                                    </label>
                                    <input
                                        type="text"
                                        value={formData.documento}
                                        onChange={e => setFormData({ ...formData, documento: e.target.value })}
                                        style={{ width: '100%', padding: '10px', border: '1px solid #e2e8f0', borderRadius: '6px' }}
                                    />
                                </div>
                            </div>
                            <div style={{ display: 'flex', gap: '10px', marginTop: '25px' }}>
                                <button
                                    type="submit"
                                    style={{
                                        flex: 1,
                                        padding: '12px',
                                        background: 'linear-gradient(135deg, #3b82f6 0%, #2563eb 100%)',
                                        color: 'white',
                                        border: 'none',
                                        borderRadius: '8px',
                                        cursor: 'pointer',
                                        fontWeight: '500'
                                    }}
                                >
                                    Adicionar
                                </button>
                                <button
                                    type="button"
                                    onClick={() => {
                                        setShowAddModal(false);
                                        resetForm();
                                    }}
                                    style={{
                                        flex: 1,
                                        padding: '12px',
                                        background: '#f1f5f9',
                                        color: '#475569',
                                        border: 'none',
                                        borderRadius: '8px',
                                        cursor: 'pointer',
                                        fontWeight: '500'
                                    }}
                                >
                                    Cancelar
                                </button>
                            </div>
                        </form>
                    </div>
                </div>
            )}
        </div>
    );
}

// Transaction Row Component with inline editing
function TransactionRow({ transaction, isSelected, onSelect, onEdit, onDelete, isEditing, setIsEditing }) {
    const [editData, setEditData] = useState({
        conta_debito: transaction.conta_debito,
        participante_debito: transaction.participante_debito || '',
        conta_credito: transaction.conta_credito,
        participante_credito: transaction.participante_credito || '',
        documento: transaction.documento
    });

    // Update editData when transaction changes (after reload from backend)
    useEffect(() => {
        setEditData({
            conta_debito: transaction.conta_debito,
            participante_debito: transaction.participante_debito || '',
            conta_credito: transaction.conta_credito,
            participante_credito: transaction.participante_credito || '',
            documento: transaction.documento
        });
    }, [transaction]);

    const handleSave = () => {
        onEdit(transaction.id, editData);
    };

    const formatDate = (dateStr) => {
        const date = new Date(dateStr);
        return date.toLocaleDateString('pt-BR');
    };

    const formatCurrency = (value) => {
        return new Intl.NumberFormat('pt-BR', {
            style: 'currency',
            currency: 'BRL'
        }).format(value);
    };

    return (
        <tr style={{
            borderBottom: '1px solid #f1f5f9',
            background: isEditing ? '#fef3c7' : (isSelected ? '#f0f9ff' : 'white')
        }}>
            <td style={{ padding: '15px' }}>
                <input
                    type="checkbox"
                    checked={isSelected}
                    onChange={onSelect}
                    style={{ cursor: 'pointer' }}
                />
            </td>
            <td style={{ padding: '15px', fontSize: '0.875rem', color: '#475569' }}>
                {formatDate(transaction.date)}
            </td>
            <td style={{ padding: '15px', textAlign: 'right', fontSize: '0.875rem', fontWeight: '500', color: '#1e293b' }}>
                {formatCurrency(transaction.amount)}
            </td>
            <td style={{ padding: '15px', fontSize: '0.875rem', color: '#475569', maxWidth: '300px' }}>
                <div style={{ overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                    {transaction.description}
                </div>
            </td>
            <td style={{ padding: '15px', textAlign: 'center' }}>
                {isEditing ? (
                    <input
                        type="text"
                        value={editData.conta_debito}
                        onChange={e => setEditData({ ...editData, conta_debito: e.target.value })}
                        style={{ width: '60px', padding: '4px', border: '1px solid #e2e8f0', borderRadius: '4px', textAlign: 'center' }}
                    />
                ) : (
                    <span style={{ fontSize: '0.875rem', fontFamily: 'monospace', background: '#f1f5f9', padding: '4px 8px', borderRadius: '4px', color: '#1e293b' }}>
                        {transaction.conta_debito}
                    </span>
                )}
            </td>
            <td style={{ padding: '15px', textAlign: 'center' }}>
                {isEditing ? (
                    <input
                        type="text"
                        value={editData.conta_credito}
                        onChange={e => setEditData({ ...editData, conta_credito: e.target.value })}
                        style={{ width: '60px', padding: '4px', border: '1px solid #e2e8f0', borderRadius: '4px', textAlign: 'center' }}
                    />
                ) : (
                    <span style={{ fontSize: '0.875rem', fontFamily: 'monospace', background: '#f1f5f9', padding: '4px 8px', borderRadius: '4px', color: '#1e293b' }}>
                        {transaction.conta_credito}
                    </span>
                )}
            </td>
            <td style={{ padding: '15px', textAlign: 'center' }}>
                {isEditing ? (
                    <input
                        type="text"
                        value={editData.documento}
                        onChange={e => setEditData({ ...editData, documento: e.target.value })}
                        style={{ width: '60px', padding: '4px', border: '1px solid #e2e8f0', borderRadius: '4px', textAlign: 'center' }}
                    />
                ) : (
                    <span style={{ fontSize: '0.875rem', fontFamily: 'monospace', color: '#1e293b' }}>
                        {transaction.documento}
                    </span>
                )}
            </td>
            <td style={{ padding: '15px', textAlign: 'center' }}>
                <span style={{
                    fontSize: '0.75rem',
                    padding: '4px 8px',
                    borderRadius: '12px',
                    background: transaction.source === 'manual' ? '#dbeafe' : '#fed7aa',
                    color: transaction.source === 'manual' ? '#1e40af' : '#9a3412',
                    fontWeight: '500'
                }}>
                    {transaction.source === 'manual' ? 'Manual' : 'Banco'}
                </span>
            </td>
            <td style={{ padding: '15px', textAlign: 'center' }}>
                <div style={{ display: 'flex', gap: '5px', justifyContent: 'center' }}>
                    {isEditing ? (
                        <>
                            <button
                                onClick={handleSave}
                                style={{
                                    padding: '6px 12px',
                                    background: '#10b981',
                                    color: 'white',
                                    border: 'none',
                                    borderRadius: '4px',
                                    cursor: 'pointer',
                                    fontSize: '0.75rem'
                                }}
                            >
                                Salvar
                            </button>
                            <button
                                onClick={() => setIsEditing(null)}
                                style={{
                                    padding: '6px 12px',
                                    background: '#94a3b8',
                                    color: 'white',
                                    border: 'none',
                                    borderRadius: '4px',
                                    cursor: 'pointer',
                                    fontSize: '0.75rem'
                                }}
                            >
                                Cancelar
                            </button>
                        </>
                    ) : (
                        <>
                            <button
                                onClick={() => setIsEditing(transaction.id)}
                                style={{
                                    padding: '6px',
                                    background: 'transparent',
                                    border: 'none',
                                    cursor: 'pointer',
                                    color: '#3b82f6'
                                }}
                                title="Editar"
                            >
                                <Edit2 size={16} />
                            </button>
                            {transaction.source === 'manual' && (
                                <button
                                    onClick={() => onDelete(transaction.id)}
                                    style={{
                                        padding: '6px',
                                        background: 'transparent',
                                        border: 'none',
                                        cursor: 'pointer',
                                        color: '#ef4444'
                                    }}
                                    title="Excluir"
                                >
                                    <Trash2 size={16} />
                                </button>
                            )}
                        </>
                    )}
                </div>
            </td>
        </tr>
    );
}

export default ExportLancamentos;
