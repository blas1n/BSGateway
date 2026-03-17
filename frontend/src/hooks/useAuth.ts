import { useCallback, useState } from 'react';
import { setAuthToken } from '../api/client';

interface AuthState {
  isAuthenticated: boolean;
  tenantId: string | null;
  tenantSlug: string | null;
  tenantName: string | null;
}

export function useAuth() {
  const [auth, setAuth] = useState<AuthState>(() => {
    const savedToken = localStorage.getItem('bsg_token');
    if (savedToken) setAuthToken(savedToken);
    return {
      isAuthenticated: !!savedToken,
      tenantId: localStorage.getItem('bsg_tenant_id'),
      tenantSlug: localStorage.getItem('bsg_tenant_slug'),
      tenantName: localStorage.getItem('bsg_tenant_name'),
    };
  });

  const login = useCallback(
    (token: string, tenantId: string, tenantSlug: string, tenantName: string) => {
      setAuthToken(token);
      localStorage.setItem('bsg_token', token);
      localStorage.setItem('bsg_tenant_id', tenantId);
      localStorage.setItem('bsg_tenant_slug', tenantSlug);
      localStorage.setItem('bsg_tenant_name', tenantName);
      setAuth({ isAuthenticated: true, tenantId, tenantSlug, tenantName });
    },
    [],
  );

  const logout = useCallback(() => {
    setAuthToken(null);
    localStorage.removeItem('bsg_token');
    localStorage.removeItem('bsg_tenant_id');
    localStorage.removeItem('bsg_tenant_slug');
    localStorage.removeItem('bsg_tenant_name');
    setAuth({ isAuthenticated: false, tenantId: null, tenantSlug: null, tenantName: null });
  }, []);

  return { ...auth, login, logout };
}
