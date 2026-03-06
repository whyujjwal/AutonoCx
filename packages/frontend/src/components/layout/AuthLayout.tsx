import { Outlet, Navigate } from 'react-router-dom';
import { useAuthStore } from '@/stores/authStore';

export function AuthLayout() {
  const isAuthenticated = useAuthStore((s) => s.isAuthenticated);

  if (isAuthenticated) {
    return <Navigate to="/dashboard" replace />;
  }

  return (
    <div className="flex min-h-screen">
      {/* Left panel - branding */}
      <div className="hidden lg:flex lg:w-1/2 items-center justify-center bg-brand-600 p-12">
        <div className="max-w-md text-center">
          <div className="mb-8 flex justify-center">
            <div className="flex h-16 w-16 items-center justify-center rounded-2xl bg-white/20">
              <span className="text-3xl font-bold text-white">A</span>
            </div>
          </div>
          <h1 className="mb-4 text-3xl font-bold text-white">AutonoCX</h1>
          <p className="text-lg text-brand-100">
            Autonomous Customer Experience Platform. Empower your support with AI-driven agents,
            intelligent workflows, and human-in-the-loop oversight.
          </p>
        </div>
      </div>

      {/* Right panel - form */}
      <div className="flex w-full items-center justify-center p-8 lg:w-1/2">
        <div className="w-full max-w-md">
          <div className="mb-8 lg:hidden">
            <div className="flex items-center gap-2">
              <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-brand-600">
                <span className="text-lg font-bold text-white">A</span>
              </div>
              <span className="text-xl font-bold text-surface-900">AutonoCX</span>
            </div>
          </div>
          <Outlet />
        </div>
      </div>
    </div>
  );
}
