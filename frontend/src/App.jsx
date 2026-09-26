import React, { useState, useEffect } from 'react';
import { AuthProvider, useAuth } from './context/AuthContext.jsx';
import LoginPage from './pages/LoginPage.jsx';
import RegisterPage from './pages/RegisterPage.jsx';
import BatchUpload from './components/BatchUpload.jsx';
import DashboardMetrics from './components/DashboardMetrics.jsx';
import ParcelTable from './components/ParcelTable.jsx';
import ParcelDetailModal from './components/ParcelDetailModal.jsx';
import RuleManagement from './components/RuleManagement.jsx';
import AdminSystemAlerts from './components/AdminSystemAlerts.jsx';
import OperatorWorkAlerts from './components/OperatorWorkAlerts.jsx';
import AuditLogTable from './components/AuditLogTable.jsx';

function MainApp() {
  const { user, loading: authLoading, logout } = useAuth();
  const [authView, setAuthView] = useState('login'); // 'login' or 'register'
  const [healthStatus, setHealthStatus] = useState({ status: 'connecting', database: 'unknown' });
  const [selectedParcel, setSelectedParcel] = useState(null);

  useEffect(() => {
    fetch('/api/health')
      .then((res) => res.json())
      .then((data) => setHealthStatus(data))
      .catch(() => setHealthStatus({ status: 'offline', database: 'unavailable' }));
  }, []);

  if (authLoading) {
    return (
      <div className="app-container" style={{ justifyContent: 'center', alignItems: 'center' }}>
        <p>Loading application...</p>
      </div>
    );
  }

  const isDbUnavailable = healthStatus.database === 'unavailable' || healthStatus.status === 'offline';
  const isAdminOrOperator = user && (user.role === 'admin' || user.role === 'operator');
  const isAdmin = user && user.role === 'admin';
  const isOperator = user && user.role === 'operator';

  return (
    <div className="app-container">
      <header className="header">
        <h1>Parcel Routing System</h1>
        {user ? (
          <div className="user-badge">
            <span>Logged in as <strong>{user.fullName}</strong></span>
            <span className="role-tag">{user.role}</span>
            <button
              className="btn btn-secondary"
              style={{ width: 'auto', padding: '0.3rem 0.75rem', fontSize: '0.8rem' }}
              onClick={logout}
            >
              Logout
            </button>
          </div>
        ) : (
          <span className={`status-badge ${healthStatus.database === 'connected' ? 'status-success' : 'status-failed'}`}>
            API: {healthStatus.status} | DB: {healthStatus.database}
          </span>
        )}
      </header>

      <main className="main-content">
        {!user ? (
          <div className="auth-container">
            {authView === 'login' ? (
              <LoginPage onNavigateRegister={() => setAuthView('register')} />
            ) : (
              <RegisterPage onNavigateLogin={() => setAuthView('login')} />
            )}
          </div>
        ) : (
          <>
            {isDbUnavailable ? (
              <section className="card" style={{ borderColor: 'var(--primary-accent)', backgroundColor: '#fef2f2' }}>
                <h2 style={{ color: 'var(--primary-accent)' }}>Database Error</h2>
                <div className="empty-state" style={{ backgroundColor: 'transparent', borderColor: 'transparent' }}>
                  <p style={{ color: 'var(--primary-accent)', fontWeight: 600 }}>
                    Database unavailable: Cannot connect to MongoDB database. Please ensure MongoDB service is running.
                  </p>
                </div>
              </section>
            ) : (
              <>
                {isAdmin && <AdminSystemAlerts />}
                {isOperator && <OperatorWorkAlerts />}
                {isAdminOrOperator && <DashboardMetrics />}
                {isAdminOrOperator && <BatchUpload />}
                {isAdminOrOperator && <RuleManagement userRole={user.role} />}
                
                <ParcelTable userRole={user.role} onSelectParcel={(p) => setSelectedParcel(p)} />
                {isAdmin && <AuditLogTable />}

                {selectedParcel && (
                  <ParcelDetailModal parcel={selectedParcel} onClose={() => setSelectedParcel(null)} />
                )}
              </>
            )}
          </>
        )}
      </main>
    </div>
  );
}

export default function App() {
  return (
    <AuthProvider>
      <MainApp />
    </AuthProvider>
  );
}
