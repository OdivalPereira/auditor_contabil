import { BrowserRouter, Routes, Route, NavLink } from 'react-router-dom';
import { LayoutDashboard, FileSpreadsheet, UploadCloud, FileType } from 'lucide-react';
import Dashboard from './pages/Dashboard';
import Conciliation from './pages/Conciliation';
import Upload from './pages/Upload';
import Extractor from './pages/Extractor';

function App() {
    return (
        <BrowserRouter>
            <div className="layout-container">
                <aside className="sidebar">
                    <div style={{ padding: '0 0 20px 0', fontSize: '1.5rem', fontWeight: 'bold', background: 'linear-gradient(to right, #fff, #94a3b8)', WebkitBackgroundClip: 'text', WebkitTextFillColor: 'transparent' }}>
                        Auditor Contábil
                    </div>

                    <nav>
                        <NavLink to="/" className={({ isActive }) => `nav-item ${isActive ? 'active' : ''}`}>
                            <LayoutDashboard size={20} style={{ marginRight: 10 }} />
                            Dashboard
                        </NavLink>
                        <NavLink to="/extractor" className={({ isActive }) => `nav-item ${isActive ? 'active' : ''}`}>
                            <FileType size={20} style={{ marginRight: 10 }} />
                            Conversor PDF
                        </NavLink>
                        <NavLink to="/conciliation" className={({ isActive }) => `nav-item ${isActive ? 'active' : ''}`}>
                            <FileSpreadsheet size={20} style={{ marginRight: 10 }} />
                            Conciliação
                        </NavLink>
                        <NavLink to="/upload" className={({ isActive }) => `nav-item ${isActive ? 'active' : ''}`}>
                            <UploadCloud size={20} style={{ marginRight: 10 }} />
                            Dados e Upload
                        </NavLink>
                    </nav>
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
