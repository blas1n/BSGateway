import { Outlet } from 'react-router-dom';
import { Sidebar } from './Sidebar';

interface LayoutProps {
  onLogout?: () => void;
  tenantSlug?: string | null;
  tenantName?: string | null;
}

export function Layout({ onLogout, tenantSlug, tenantName }: LayoutProps) {
  return (
    <div className="min-h-screen bg-surface text-on-surface antialiased">
      <Sidebar onLogout={onLogout} tenantSlug={tenantSlug} tenantName={tenantName} />
      <main className="ml-64 min-h-screen">
        <Outlet />
      </main>
    </div>
  );
}
