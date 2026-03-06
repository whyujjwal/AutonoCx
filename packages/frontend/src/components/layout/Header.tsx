import { Bell, Search, LogOut, User, Settings } from 'lucide-react';
import { useNavigate } from 'react-router-dom';
import { Avatar } from '@/components/ui/Avatar';
import { Dropdown } from '@/components/ui/Dropdown';
import { useAuthStore } from '@/stores/authStore';

export function Header() {
  const navigate = useNavigate();
  const { user, logout } = useAuthStore();

  const handleLogout = async () => {
    await logout();
    navigate('/login');
  };

  return (
    <header className="flex h-16 items-center justify-between border-b border-surface-200 bg-white px-6">
      {/* Search bar */}
      <div className="relative w-full max-w-md">
        <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-surface-400" />
        <input
          type="text"
          placeholder="Search conversations, agents, tools..."
          className="w-full rounded-lg border border-surface-200 bg-surface-50 py-2 pl-10 pr-4 text-sm text-surface-700 placeholder:text-surface-400 focus:border-brand-500 focus:bg-white focus:outline-none focus:ring-2 focus:ring-brand-500/20"
        />
      </div>

      {/* Right side */}
      <div className="flex items-center gap-3">
        {/* Notifications */}
        <button className="relative rounded-lg p-2 text-surface-500 hover:bg-surface-50 hover:text-surface-700 transition-colors">
          <Bell className="h-5 w-5" />
          <span className="absolute right-1.5 top-1.5 h-2 w-2 rounded-full bg-danger-500" />
        </button>

        {/* User menu */}
        <Dropdown
          trigger={
            <div className="flex items-center gap-2">
              <Avatar name={user?.name ?? 'User'} size="sm" />
              <div className="hidden md:block text-left">
                <p className="text-sm font-medium text-surface-800">{user?.name ?? 'User'}</p>
                <p className="text-xs text-surface-500">{user?.role ?? 'admin'}</p>
              </div>
            </div>
          }
          items={[
            {
              id: 'profile',
              label: 'Profile',
              icon: <User className="h-4 w-4" />,
              onClick: () => navigate('/settings'),
            },
            {
              id: 'settings',
              label: 'Settings',
              icon: <Settings className="h-4 w-4" />,
              onClick: () => navigate('/settings'),
            },
            {
              id: 'logout',
              label: 'Log Out',
              icon: <LogOut className="h-4 w-4" />,
              onClick: handleLogout,
              variant: 'danger',
              divider: true,
            },
          ]}
        />
      </div>
    </header>
  );
}
