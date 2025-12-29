import React from 'react';
import { UserCog, AlertCircle } from 'lucide-react';

const ConciliacaoFolha = () => {
    return (
        <div style={{ animation: 'fadeIn 0.5s ease-out' }}>
            <div style={{ marginBottom: '25px' }}>
                <h1 style={{ margin: 0 }}>Conciliação de Folha</h1>
            </div>

            <div className="glass-panel" style={{
                padding: '100px 40px',
                textAlign: 'center',
                display: 'flex',
                flexDirection: 'column',
                alignItems: 'center',
                justifyContent: 'center',
                minHeight: '400px'
            }}>
                <div style={{
                    background: 'rgba(99, 102, 241, 0.1)',
                    padding: '24px',
                    borderRadius: '50%',
                    marginBottom: '24px'
                }}>
                    <UserCog size={64} color="var(--accent-color)" />
                </div>

                <h2 style={{ marginBottom: '16px' }}>Módulo em Desenvolvimento</h2>
                <p style={{
                    color: '#94a3b8',
                    maxWidth: '500px',
                    fontSize: '1.1rem',
                    lineHeight: '1.6'
                }}>
                    Em breve você poderá fazer a conciliação entre a folha de pagamento e escrituração contábil diretamente por aqui.
                </p>

                <div style={{
                    marginTop: '32px',
                    display: 'flex',
                    alignItems: 'center',
                    gap: '10px',
                    color: '#6366f1',
                    fontSize: '0.9rem',
                    fontWeight: 600,
                    padding: '8px 16px',
                    borderRadius: '20px',
                    background: 'rgba(99, 102, 241, 0.1)'
                }}>
                    <AlertCircle size={18} />
                    Funcionalidade sendo preparada
                </div>
            </div>
        </div>
    );
};

export default ConciliacaoFolha;
