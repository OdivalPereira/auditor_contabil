import { BrowserRouter, Routes, Route, NavLink } from 'react-router-dom';
import { LayoutDashboard, FileSpreadsheet, UploadCloud, FileType, CheckCircle, AlertCircle, ChevronLeft, ChevronRight } from 'lucide-react';
import { useApp } from './AppContext';
import Dashboard from './pages/Dashboard';
import Conciliation from './pages/Conciliation';
import Upload from './pages/Upload';
import Extractor from './pages/Extractor';
import { useEffect, useState } from 'react';

function App() {
    const { uploadStatus, refreshUploadStatus } = useApp();
    const [sidebarCollapsed, setSidebarCollapsed] = useState(false);

    useEffect(() => {
        refreshUploadStatus();
    }, []);

    const hasData = uploadStatus.ledger_count > 0;

    return (
        <BrowserRouter>
            <div className="layout-container">
                <aside className="sidebar" style={{ width: sidebarCollapsed ? '70px' : '220px' }}>
                    {/* Header with collapse button */}
                    <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '20px' }}>
                        {!sidebarCollapsed && (
                            <div style={{ fontSize: '1.3rem', fontWeight: 'bold', background: 'linear-gradient(to right, #fff, #94a3b8)', WebkitBackgroundClip: 'text', WebkitTextFillColor: 'transparent' }}>
                                Auditor Contábil
                            </div>
                        )}
                        <button
                            onClick={() => setSidebarCollapsed(!sidebarCollapsed)}
                            style={{
                                background: 'transparent',
                                border: 'none',
                                color: 'rgba(255,255,255,0.3)',
                                cursor: 'pointer',
                                padding: '4px',
                                display: 'flex',
                                alignItems: 'center',
                                justifyContent: 'center',
                                transition: 'all 0.2s',
                                marginLeft: sidebarCollapsed ? 'auto' : '0'
                            }}
                            onMouseEnter={(e) => e.currentTarget.style.color = 'rgba(255,255,255,0.7)'}
                            onMouseLeave={(e) => e.currentTarget.style.color = 'rgba(255,255,255,0.3)'}
                            title={sidebarCollapsed ? 'Expandir' : 'Recolher'}
                        >
                            {sidebarCollapsed ? <ChevronRight size={18} /> : <ChevronLeft size={18} />}
                        </button>
                    </div>

                    <nav>
                        <NavLink to="/" className={({ isActive }) => `nav-item ${isActive ? 'active' : ''}`} title="Dashboard">
                            <LayoutDashboard size={20} style={{ marginRight: sidebarCollapsed ? 0 : 10 }} />
                            {!sidebarCollapsed && 'Dashboard'}
                        </NavLink>
                        <NavLink to="/extractor" className={({ isActive }) => `nav-item ${isActive ? 'active' : ''}`} title="Conversor PDF">
                            <FileType size={20} style={{ marginRight: sidebarCollapsed ? 0 : 10 }} />
                            {!sidebarCollapsed && 'Conversor PDF'}
                        </NavLink>
                        <NavLink to="/conciliation" className={({ isActive }) => `nav-item ${isActive ? 'active' : ''}`} title="Conciliação">
                            <FileSpreadsheet size={20} style={{ marginRight: sidebarCollapsed ? 0 : 10 }} />
                            {!sidebarCollapsed && 'Conciliação'}
                        </NavLink>
                        <NavLink to="/upload" className={({ isActive }) => `nav-item ${isActive ? 'active' : ''}`} title="Dados e Upload">
                            <UploadCloud size={20} style={{ marginRight: sidebarCollapsed ? 0 : 10 }} />
                            {!sidebarCollapsed && 'Dados e Upload'}
                        </NavLink>
                    </nav>

                    {/* Status Indicator at Sidebar Bottom */}
                    {!sidebarCollapsed && (
                        <div style={{ marginTop: 'auto', padding: '15px 0', borderTop: '1px solid rgba(255,255,255,0.05)', fontSize: '0.8rem' }}>
                            <div style={{ display: 'flex', alignItems: 'center', gap: '8px', color: hasData ? '#34d399' : '#94a3b8' }}>
                                {hasData ? <CheckCircle size={14} /> : <AlertCircle size={14} />}
                                {hasData ? "Dados Prontos" : "Aguardando Upload"}
                            </div>
                            {hasData && (
                                <div style={{ marginTop: 5, opacity: 0.6, fontSize: '0.75rem' }}>
                                    {uploadStatus.ledger_count} lançamentos<br />
                                    {uploadStatus.bank_count} transações
                                </div>
                            )}
                        </div>
                    )}
                </aside>

                <main className="main-content">
                    <Routes>
                        <Route path="/" element={<Dashboard />} />
                        <Route path="/extractor" element={<Extractor />} />
                        <Route path="/conciliation" element={<Conciliation />} />
                        <Route path="/upload" element={<Upload />} />
                    </Routes>
                </main>
            </div>
        </BrowserRouter>
    );
}

export default App;
