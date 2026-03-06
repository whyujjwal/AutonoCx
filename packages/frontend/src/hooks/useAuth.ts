import { useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuthStore } from '@/stores/authStore';
import { useNotificationStore } from '@/stores/notificationStore';

export function useAuth() {
  const navigate = useNavigate();
  const { user, isAuthenticated, isLoading, login, register, logout } = useAuthStore();
  const addToast = useNotificationStore((s) => s.addToast);

  const handleLogin = useCallback(
    async (email: string, password: string) => {
      try {
        await login(email, password);
        addToast({ type: 'success', title: 'Welcome back!' });
        navigate('/dashboard');
      } catch {
        addToast({ type: 'error', title: 'Login failed', message: 'Invalid email or password' });
        throw new Error('Login failed');
      }
    },
    [login, navigate, addToast],
  );

  const handleRegister = useCallback(
    async (name: string, email: string, password: string, organizationName: string) => {
      try {
        await register(name, email, password, organizationName);
        addToast({ type: 'success', title: 'Account created successfully!' });
        navigate('/dashboard');
      } catch {
        addToast({ type: 'error', title: 'Registration failed', message: 'Please try again' });
        throw new Error('Registration failed');
      }
    },
    [register, navigate, addToast],
  );

  const handleLogout = useCallback(async () => {
    await logout();
    navigate('/login');
  }, [logout, navigate]);

  return {
    user,
    isAuthenticated,
    isLoading,
    login: handleLogin,
    register: handleRegister,
    logout: handleLogout,
  };
}
