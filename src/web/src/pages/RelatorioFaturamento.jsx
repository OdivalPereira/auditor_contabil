import React, { useState, useMemo } from 'react';
import { FileText, Building2, Calendar, User, Printer, Download, FileSpreadsheet, FileIcon, Search, ChevronDown, AlertCircle } from 'lucide-react';

// Mock data - will be replaced with persistent database
const MOCK_EMPRESAS = [
    { id: 1, nome: 'Arruda & Barros LTDA', cnpj: '12.345.678/0001-90' },
    { id: 2, nome: 'Comercial Santos ME', cnpj: '98.765.432/0001-10' },
    { id: 3, nome: 'Indústria Silva S.A.', cnpj: '11.222.333/0001-44' },
    { id: 4, nome: 'Transportes Oliveira LTDA', cnpj: '55.666.777/0001-88' },
];

const MOCK_RESPONSAVEIS = [
    { id: 1, nome: 'João Carlos Silva', cargo: 'Contador - CRC 12345' },
    { id: 2, nome: 'Maria Fernanda Costa', cargo: 'Contadora - CRC 67890' },
    { id: 3, nome: 'Pedro Augusto Lima', cargo: 'Técnico Contábil - CRC 11111' },
];

const RelatorioFaturamento = () => {
    // Form state
    const [empresaSelecionada, setEmpresaSelecionada] = useState(null);
    const [periodoInicio, setPeriodoInicio] = useState('');
    const [periodoFim, setPeriodoFim] = useState('');
    const [responsavel, setResponsavel] = useState(null);
    const [searchEmpresa, setSearchEmpresa] = useState('');
    const [showEmpresaDropdown, setShowEmpresaDropdown] = useState(false);

    // Preview state
    const [showPreview, setShowPreview] = useState(false);
    const [generating, setGenerating] = useState(false);

    // Filter empresas
    const empresasFiltradas = useMemo(() => {
        if (!searchEmpresa) return MOCK_EMPRESAS;
        const term = searchEmpresa.toLowerCase();
        return MOCK_EMPRESAS.filter(e =>
            e.nome.toLowerCase().includes(term) ||
            e.cnpj.includes(term)
        );
    }, [searchEmpresa]);

    const canGenerate = empresaSelecionada && periodoInicio && periodoFim && responsavel;

    const handleGenerate = (type) => {
        if (!canGenerate) return;

        setGenerating(true);
        // Simulate generation
        setTimeout(() => {
            setGenerating(false);
            if (type === 'preview') {
                setShowPreview(true);
            } else {
                // In future: trigger actual PDF/Excel generation via API
                alert(`Relatório ${type.toUpperCase()} será gerado quando o backend estiver implementado.`);
            }
        }, 800);
    };

    const handlePrint = () => {
        window.print();
    };

    return (
        <div style={{ animation: 'fadeIn 0.5s ease-out' }}>
            {/* Page Header */}
            <div style={{ marginBottom: '25px', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                <h1 style={{ margin: 0, display: 'flex', alignItems: 'center', gap: 12 }}>
                    <FileText size={28} />
                    Relatório de Faturamento
                </h1>
            </div>

            {/* Info Alert */}
            <div style={{
                padding: '15px 20px',
                borderRadius: '10px',
                marginBottom: '25px',
                background: 'rgba(99, 102, 241, 0.1)',
                border: '1px solid rgba(99, 102, 241, 0.3)',
                display: 'flex',
                alignItems: 'center',
                gap: 12,
                color: '#a5b4fc'
            }}>
                <AlertCircle size={20} />
                <span>
                    Este módulo requer uma base de dados persistente. Os dados abaixo são exemplos de demonstração.
                </span>
            </div>

            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '30px' }}>
                {/* Left Column - Form */}
                <div className="glass-panel" style={{ padding: '25px' }}>
                    <h3 style={{ marginTop: 0, marginBottom: 20, display: 'flex', alignItems: 'center', gap: 8 }}>
                        <Building2 size={20} />
                        Parâmetros do Relatório
                    </h3>

                    {/* Empresa Selection */}
                    <div style={{ marginBottom: 20 }}>
                        <label style={{ display: 'block', marginBottom: 8, color: '#94a3b8', fontSize: '0.9rem' }}>
                            Empresa *
                        </label>
                        <div style={{ position: 'relative' }}>
                            <div
                                onClick={() => setShowEmpresaDropdown(!showEmpresaDropdown)}
                                style={{
                                    background: 'rgba(0,0,0,0.3)',
                                    border: '1px solid rgba(255,255,255,0.15)',
                                    borderRadius: '10px',
                                    padding: '12px 15px',
                                    cursor: 'pointer',
                                    display: 'flex',
                                    justifyContent: 'space-between',
                                    alignItems: 'center',
                                    color: empresaSelecionada ? 'white' : '#64748b'
                                }}
                            >
                                <span>{empresaSelecionada ? empresaSelecionada.nome : 'Selecione a empresa...'}</span>
                                <ChevronDown size={18} style={{ transform: showEmpresaDropdown ? 'rotate(180deg)' : 'rotate(0)', transition: 'transform 0.2s' }} />
                            </div>

                            {showEmpresaDropdown && (
                                <div style={{
                                    position: 'absolute',
                                    top: '100%',
                                    left: 0,
                                    right: 0,
                                    background: '#1e293b',
                                    border: '1px solid rgba(255,255,255,0.15)',
                                    borderRadius: '10px',
                                    marginTop: 5,
                                    zIndex: 100,
                                    boxShadow: '0 10px 40px rgba(0,0,0,0.5)',
                                    overflow: 'hidden'
                                }}>
                                    <div style={{ padding: '10px', borderBottom: '1px solid rgba(255,255,255,0.1)' }}>
                                        <div style={{ position: 'relative' }}>
                                            <Search size={16} style={{ position: 'absolute', left: 10, top: '50%', transform: 'translateY(-50%)', color: '#64748b' }} />
                                            <input
                                                type="text"
                                                placeholder="Buscar empresa..."
                                                value={searchEmpresa}
                                                onChange={(e) => setSearchEmpresa(e.target.value)}
                                                style={{
                                                    width: '100%',
                                                    padding: '8px 10px 8px 35px',
                                                    background: 'rgba(0,0,0,0.3)',
                                                    border: '1px solid rgba(255,255,255,0.1)',
                                                    borderRadius: '6px',
                                                    color: 'white',
                                                    fontSize: '0.9rem'
                                                }}
                                                autoFocus
                                            />
                                        </div>
                                    </div>
                                    <div style={{ maxHeight: 200, overflowY: 'auto' }}>
                                        {empresasFiltradas.map(emp => (
                                            <div
                                                key={emp.id}
                                                onClick={() => {
                                                    setEmpresaSelecionada(emp);
                                                    setShowEmpresaDropdown(false);
                                                    setSearchEmpresa('');
                                                }}
                                                style={{
                                                    padding: '12px 15px',
                                                    cursor: 'pointer',
                                                    borderBottom: '1px solid rgba(255,255,255,0.05)',
                                                    transition: 'background 0.2s'
                                                }}
                                                onMouseEnter={(e) => e.currentTarget.style.background = 'rgba(99, 102, 241, 0.2)'}
                                                onMouseLeave={(e) => e.currentTarget.style.background = 'transparent'}
                                            >
                                                <div style={{ fontWeight: 500 }}>{emp.nome}</div>
                                                <div style={{ fontSize: '0.8rem', color: '#64748b' }}>{emp.cnpj}</div>
                                            </div>
                                        ))}
                                        {empresasFiltradas.length === 0 && (
                                            <div style={{ padding: '15px', textAlign: 'center', color: '#64748b' }}>
                                                Nenhuma empresa encontrada
                                            </div>
                                        )}
                                    </div>
                                </div>
                            )}
                        </div>
                    </div>

                    {/* Período */}
                    <div style={{ marginBottom: 20 }}>
                        <label style={{ display: 'block', marginBottom: 8, color: '#94a3b8', fontSize: '0.9rem' }}>
                            <Calendar size={14} style={{ verticalAlign: -2, marginRight: 5 }} />
                            Período de Faturamento *
                        </label>
                        <div style={{ display: 'flex', gap: 10, alignItems: 'center' }}>
                            <input
                                type="date"
                                value={periodoInicio}
                                onChange={(e) => setPeriodoInicio(e.target.value)}
                                style={{
                                    flex: 1,
                                    padding: '12px 15px',
                                    background: 'rgba(0,0,0,0.3)',
                                    border: '1px solid rgba(255,255,255,0.15)',
                                    borderRadius: '10px',
                                    color: 'white',
                                    fontSize: '0.95rem'
                                }}
                            />
                            <span style={{ color: '#64748b' }}>até</span>
                            <input
                                type="date"
                                value={periodoFim}
                                onChange={(e) => setPeriodoFim(e.target.value)}
                                style={{
                                    flex: 1,
                                    padding: '12px 15px',
                                    background: 'rgba(0,0,0,0.3)',
                                    border: '1px solid rgba(255,255,255,0.15)',
                                    borderRadius: '10px',
                                    color: 'white',
                                    fontSize: '0.95rem'
                                }}
                            />
                        </div>
                    </div>

                    {/* Responsável */}
                    <div style={{ marginBottom: 25 }}>
                        <label style={{ display: 'block', marginBottom: 8, color: '#94a3b8', fontSize: '0.9rem' }}>
                            <User size={14} style={{ verticalAlign: -2, marginRight: 5 }} />
                            Responsável pela Assinatura *
                        </label>
                        <select
                            value={responsavel?.id || ''}
                            onChange={(e) => setResponsavel(MOCK_RESPONSAVEIS.find(r => r.id === parseInt(e.target.value)) || null)}
                            style={{
                                width: '100%',
                                padding: '12px 15px',
                                background: 'rgba(0,0,0,0.3)',
                                border: '1px solid rgba(255,255,255,0.15)',
                                borderRadius: '10px',
                                color: responsavel ? 'white' : '#64748b',
                                fontSize: '0.95rem',
                                cursor: 'pointer'
                            }}
                        >
                            <option value="">Selecione o responsável...</option>
                            {MOCK_RESPONSAVEIS.map(resp => (
                                <option key={resp.id} value={resp.id}>
                                    {resp.nome} - {resp.cargo}
                                </option>
                            ))}
                        </select>
                    </div>

                    {/* Action Buttons */}
                    <div style={{ display: 'flex', gap: 10, flexWrap: 'wrap' }}>
                        <button
                            onClick={() => handleGenerate('preview')}
                            disabled={!canGenerate || generating}
                            className="btn-primary"
                            style={{
                                flex: 1,
                                padding: '14px 20px',
                                background: canGenerate ? 'linear-gradient(135deg, #6366f1 0%, #a855f7 100%)' : 'rgba(100,100,100,0.3)',
                                display: 'flex',
                                alignItems: 'center',
                                justifyContent: 'center',
                                gap: 8,
                                opacity: canGenerate ? 1 : 0.5,
                                cursor: canGenerate ? 'pointer' : 'not-allowed'
                            }}
                        >
                            <FileText size={18} />
                            {generating ? 'Gerando...' : 'Visualizar'}
                        </button>

                        <button
                            onClick={handlePrint}
                            disabled={!showPreview}
                            style={{
                                padding: '14px 20px',
                                background: showPreview ? 'rgba(16, 185, 129, 0.2)' : 'rgba(100,100,100,0.2)',
                                border: showPreview ? '1px solid #10b981' : '1px solid rgba(255,255,255,0.1)',
                                borderRadius: '10px',
                                color: showPreview ? '#10b981' : '#64748b',
                                display: 'flex',
                                alignItems: 'center',
                                gap: 8,
                                cursor: showPreview ? 'pointer' : 'not-allowed'
                            }}
                        >
                            <Printer size={18} />
                            Imprimir
                        </button>
                    </div>

                    <div style={{ display: 'flex', gap: 10, marginTop: 10 }}>
                        <button
                            onClick={() => handleGenerate('pdf')}
                            disabled={!canGenerate}
                            style={{
                                flex: 1,
                                padding: '12px 20px',
                                background: 'rgba(239, 68, 68, 0.15)',
                                border: '1px solid rgba(239, 68, 68, 0.3)',
                                borderRadius: '10px',
                                color: canGenerate ? '#f87171' : '#64748b',
                                display: 'flex',
                                alignItems: 'center',
                                justifyContent: 'center',
                                gap: 8,
                                cursor: canGenerate ? 'pointer' : 'not-allowed',
                                opacity: canGenerate ? 1 : 0.5
                            }}
                        >
                            <Download size={16} />
                            Salvar PDF
                        </button>

                        <button
                            onClick={() => handleGenerate('excel')}
                            disabled={!canGenerate}
                            style={{
                                flex: 1,
                                padding: '12px 20px',
                                background: 'rgba(16, 185, 129, 0.15)',
                                border: '1px solid rgba(16, 185, 129, 0.3)',
                                borderRadius: '10px',
                                color: canGenerate ? '#34d399' : '#64748b',
                                display: 'flex',
                                alignItems: 'center',
                                justifyContent: 'center',
                                gap: 8,
                                cursor: canGenerate ? 'pointer' : 'not-allowed',
                                opacity: canGenerate ? 1 : 0.5
                            }}
                        >
                            <FileSpreadsheet size={16} />
                            Salvar Excel
                        </button>
                    </div>
                </div>

                {/* Right Column - Preview */}
                <div className="glass-panel" style={{ padding: '25px', minHeight: 500 }}>
                    <h3 style={{ marginTop: 0, marginBottom: 20, display: 'flex', alignItems: 'center', gap: 8 }}>
                        <FileIcon size={20} />
                        Pré-visualização
                    </h3>

                    {!showPreview ? (
                        <div style={{
                            display: 'flex',
                            flexDirection: 'column',
                            alignItems: 'center',
                            justifyContent: 'center',
                            height: '400px',
                            color: '#64748b',
                            textAlign: 'center'
                        }}>
                            <FileText size={64} style={{ marginBottom: 20, opacity: 0.3 }} />
                            <p style={{ fontSize: '1.1rem' }}>Preencha os parâmetros e clique em "Visualizar"</p>
                            <p style={{ fontSize: '0.9rem', marginTop: 5 }}>para gerar a pré-visualização do relatório.</p>
                        </div>
                    ) : (
                        <div style={{
                            background: 'white',
                            borderRadius: '8px',
                            padding: '30px',
                            color: '#1e293b',
                            minHeight: '400px'
                        }}>
                            {/* Mock Report Preview */}
                            <div style={{ textAlign: 'center', borderBottom: '2px solid #1e293b', paddingBottom: 20, marginBottom: 20 }}>
                                <h2 style={{ margin: 0, color: '#1e293b' }}>RELATÓRIO DE FATURAMENTO</h2>
                                <p style={{ margin: '10px 0 0', fontSize: '0.9rem', color: '#64748b' }}>
                                    Período: {new Date(periodoInicio).toLocaleDateString('pt-BR')} a {new Date(periodoFim).toLocaleDateString('pt-BR')}
                                </p>
                            </div>

                            <div style={{ marginBottom: 20 }}>
                                <strong>Empresa:</strong> {empresaSelecionada?.nome}<br />
                                <strong>CNPJ:</strong> {empresaSelecionada?.cnpj}
                            </div>

                            <table style={{ width: '100%', borderCollapse: 'collapse', marginBottom: 30 }}>
                                <thead>
                                    <tr style={{ background: '#f1f5f9' }}>
                                        <th style={{ padding: '10px', textAlign: 'left', borderBottom: '1px solid #cbd5e1' }}>Descrição</th>
                                        <th style={{ padding: '10px', textAlign: 'right', borderBottom: '1px solid #cbd5e1' }}>Valor</th>
                                    </tr>
                                </thead>
                                <tbody>
                                    <tr>
                                        <td style={{ padding: '10px', borderBottom: '1px solid #e2e8f0' }}>Serviços Contábeis</td>
                                        <td style={{ padding: '10px', textAlign: 'right', borderBottom: '1px solid #e2e8f0' }}>R$ 2.500,00</td>
                                    </tr>
                                    <tr>
                                        <td style={{ padding: '10px', borderBottom: '1px solid #e2e8f0' }}>Folha de Pagamento</td>
                                        <td style={{ padding: '10px', textAlign: 'right', borderBottom: '1px solid #e2e8f0' }}>R$ 800,00</td>
                                    </tr>
                                    <tr>
                                        <td style={{ padding: '10px', borderBottom: '1px solid #e2e8f0' }}>Obrigações Acessórias</td>
                                        <td style={{ padding: '10px', textAlign: 'right', borderBottom: '1px solid #e2e8f0' }}>R$ 450,00</td>
                                    </tr>
                                    <tr style={{ fontWeight: 'bold', background: '#f8fafc' }}>
                                        <td style={{ padding: '10px' }}>TOTAL</td>
                                        <td style={{ padding: '10px', textAlign: 'right' }}>R$ 3.750,00</td>
                                    </tr>
                                </tbody>
                            </table>

                            <div style={{ marginTop: 50, textAlign: 'center', borderTop: '1px solid #cbd5e1', paddingTop: 20 }}>
                                <p style={{ marginBottom: 30 }}>_______________________________</p>
                                <p style={{ margin: 0, fontWeight: 'bold' }}>{responsavel?.nome}</p>
                                <p style={{ margin: '5px 0 0', fontSize: '0.9rem', color: '#64748b' }}>{responsavel?.cargo}</p>
                            </div>
                        </div>
                    )}
                </div>
            </div>
        </div>
    );
};

export default RelatorioFaturamento;
