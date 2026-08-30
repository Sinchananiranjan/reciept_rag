import React, { useState } from 'react';
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { AuthProvider, useAuth } from './context/AuthContext';
import { DataRefreshProvider, useDataRefresh } from './context/DataRefreshContext';
import { Sidebar } from './components/layout/Sidebar';
import { Navbar } from './components/layout/Navbar';
import { ReceiptUploader } from './components/receipts/ReceiptUploader';

import { Login } from './pages/Login';
import { Register } from './pages/Register';
import { Dashboard } from './pages/Dashboard';
import { Receipts } from './pages/Receipts';
import { ReceiptDetails } from './pages/ReceiptDetails';
import { Chat } from './pages/Chat';
import { Analytics } from './pages/Analytics';
import { Settings } from './pages/Settings';

const ProtectedLayout: React.FC<{ children: (openUploadModal: () => void) => React.ReactNode }> = ({ children }) => {
  const { isAuthenticated, isLoading } = useAuth();
  const { notifyDataChanged } = useDataRefresh();
  const [isUploadModalOpen, setIsUploadModalOpen] = useState(false);
  const [globalSearch, setGlobalSearch] = useState('');

  if (isLoading) {
    return (
      <div className="min-h-screen bg-slate-950 flex items-center justify-center text-slate-500 text-xs">
        Initializing ReceiptRAG session...
      </div>
    );
  }

  if (!isAuthenticated) {
    return <Navigate to="/login" replace />;
  }

  return (
    <div className="flex h-screen bg-slate-950 text-slate-100 overflow-hidden">
      <Sidebar />
      <div className="flex-1 flex flex-col min-w-0 overflow-hidden">
        <Navbar
          onOpenUploadModal={() => setIsUploadModalOpen(true)}
          searchQuery={globalSearch}
          onSearchChange={setGlobalSearch}
        />
        <main className="flex-1 overflow-y-auto">
          {children(() => setIsUploadModalOpen(true))}
        </main>
      </div>

      <ReceiptUploader
        isOpen={isUploadModalOpen}
        onClose={() => setIsUploadModalOpen(false)}
        onUploadSuccess={() => {
          notifyDataChanged();
        }}
      />
    </div>
  );
};

export const App: React.FC = () => {
  return (
    <AuthProvider>
      <DataRefreshProvider>
        <BrowserRouter>
          <Routes>
            {/* Public Auth Routes */}
            <Route path="/login" element={<Login />} />
            <Route path="/register" element={<Register />} />

            {/* Protected SaaS Routes */}
            <Route
              path="/dashboard"
              element={
                <ProtectedLayout>
                  {() => <Dashboard />}
                </ProtectedLayout>
              }
            />
            <Route
              path="/receipts"
              element={
                <ProtectedLayout>
                  {(openUploadModal) => <Receipts onOpenUploadModal={openUploadModal} />}
                </ProtectedLayout>
              }
            />
            <Route
              path="/receipts/:id"
              element={
                <ProtectedLayout>
                  {() => <ReceiptDetails />}
                </ProtectedLayout>
              }
            />
            <Route
              path="/chat"
              element={
                <ProtectedLayout>
                  {() => <Chat />}
                </ProtectedLayout>
              }
            />
            <Route
              path="/analytics"
              element={
                <ProtectedLayout>
                  {() => <Analytics />}
                </ProtectedLayout>
              }
            />
            <Route
              path="/settings"
              element={
                <ProtectedLayout>
                  {() => <Settings />}
                </ProtectedLayout>
              }
            />

            <Route path="*" element={<Navigate to="/dashboard" replace />} />
          </Routes>
        </BrowserRouter>
      </DataRefreshProvider>
    </AuthProvider>
  );
};

export default App;
