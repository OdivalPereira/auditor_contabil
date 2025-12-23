import React, { createContext, useContext, useState, useEffect } from 'react';
import api from './api/client';

const AppContext = createContext();

const STORAGE_KEYS = {
    UPLOAD_STATUS: 'auditor_upload_status',
    RECONCILE_RESULTS: 'auditor_reconcile_results',
    TOLERANCE: 'auditor_tolerance'
};

export const AppProvider = ({ children }) => {
    // Load from localStorage on mount
    const loadFromStorage = (key, defaultValue) => {
        try {
            const stored = localStorage.getItem(key);
            return stored ? JSON.parse(stored) : defaultValue;
        } catch (e) {
            console.error(`Failed to load ${key} from localStorage`, e);
            return defaultValue;
        }
    };

    // Persistent state across navigations
    const [ledgerFile, setLedgerFile] = useState(null);
    const [bankFiles, setBankFiles] = useState([]);
    const [reconcileResults, setReconcileResults] = useState(() =>
        loadFromStorage(STORAGE_KEYS.RECONCILE_RESULTS, null)
    );
    const [uploadStatus, setUploadStatus] = useState(() =>
        loadFromStorage(STORAGE_KEYS.UPLOAD_STATUS, { ledger_count: 0, bank_count: 0, ledger_name: null })
    );
    const [lastTolerance, setLastTolerance] = useState(() =>
        loadFromStorage(STORAGE_KEYS.TOLERANCE, 3)
    );

    // Auto-save to localStorage when data changes
    useEffect(() => {
        try {
            localStorage.setItem(STORAGE_KEYS.UPLOAD_STATUS, JSON.stringify(uploadStatus));
        } catch (e) {
            console.error('Failed to save upload status to localStorage', e);
        }
    }, [uploadStatus]);

    useEffect(() => {
        try {
            if (reconcileResults) {
                localStorage.setItem(STORAGE_KEYS.RECONCILE_RESULTS, JSON.stringify(reconcileResults));
            }
        } catch (e) {
            console.error('Failed to save reconcile results to localStorage', e);
        }
    }, [reconcileResults]);

    useEffect(() => {
        try {
            localStorage.setItem(STORAGE_KEYS.TOLERANCE, JSON.stringify(lastTolerance));
        } catch (e) {
            console.error('Failed to save tolerance to localStorage', e);
        }
    }, [lastTolerance]);

    // Check backend status on mount or tab switch (via pages)
    const refreshUploadStatus = async () => {
        try {
            const res = await api.get('/upload/status');
            setUploadStatus(res.data);
        } catch (err) {
            console.error("Failed to fetch upload status", err);
        }
    };

    const clearAll = async () => {
        try {
            await api.post('/upload/clear');
            setLedgerFile(null);
            setBankFiles([]);
            setReconcileResults(null);
            setUploadStatus({ ledger_count: 0, bank_count: 0, ledger_name: null });

            // Clear localStorage
            localStorage.removeItem(STORAGE_KEYS.UPLOAD_STATUS);
            localStorage.removeItem(STORAGE_KEYS.RECONCILE_RESULTS);
            localStorage.removeItem(STORAGE_KEYS.TOLERANCE);

            console.log('All data cleared from memory and storage');
        } catch (err) {
            console.error("Failed to clear data", err);
        }
    };

    // Clear server data when browser/tab closes
    useEffect(() => {
        const handleBeforeUnload = (e) => {
            // Use sendBeacon for reliable data sending during page unload
            // This ensures the request is sent even if the page is closing
            const blob = new Blob([JSON.stringify({})], { type: 'application/json' });
            navigator.sendBeacon(`${api.defaults.baseURL}/upload/clear`, blob);

            // Note: We don't clear localStorage here because we want
            // the data to persist across page reloads for better UX
        };

        window.addEventListener('beforeunload', handleBeforeUnload);

        return () => {
            window.removeEventListener('beforeunload', handleBeforeUnload);
        };
    }, []);


    return (
        <AppContext.Provider value={{
            ledgerFile, setLedgerFile,
            bankFiles, setBankFiles,
            reconcileResults, setReconcileResults,
            uploadStatus, setUploadStatus, refreshUploadStatus,
            lastTolerance, setLastTolerance,
            clearAll
        }}>
            {children}
        </AppContext.Provider>
    );
};

export const useApp = () => useContext(AppContext);
