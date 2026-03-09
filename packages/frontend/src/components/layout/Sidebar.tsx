import { NavLink } from 'react-router-dom';
import { clsx } from 'clsx';
import {
  LayoutDashboard,
  MessageSquare,
  Bot,
  BookOpen,
  GitBranch,
  Wrench,
  ShieldCheck,
  FileText,
  Radio,
  BarChart3,
  ScrollText,
  Settings,
  Plug,
  ChevronLeft,
  ChevronRight,
} from 'lucide-react';
import { useUIStore } from '@/stores/uiStore';

const navItems = [
  { to: '/dashboard', label: 'Dashboard', icon: LayoutDashboard },
  { to: '/conversations', label: 'Conversations', icon: MessageSquare },
  { to: '/agents', label: 'Agents', icon: Bot },
  { to: '/knowledge', label: 'Knowledge Base', icon: BookOpen },
  { to: '/workflows', label: 'Workflows', icon: GitBranch },
  { to: '/tools', label: 'Tools', icon: Wrench },
  { to: '/actions', label: 'Action Queue', icon: ShieldCheck },
  { to: '/prompts', label: 'Prompts', icon: FileText },
  { to: '/channels', label: 'Channels', icon: Radio },
  { to: '/analytics', label: 'Analytics', icon: BarChart3 },
  { to: '/audit', label: 'Audit Log', icon: ScrollText },
];

const settingsItems = [
  { to: '/settings', label: 'General', icon: Settings },
  { to: '/settings/connectors', label: 'Integrations', icon: Plug },
];

export function Sidebar() {
  const { sidebarCollapsed, toggleSidebarCollapsed } = useUIStore();

  return (
    <aside
      className={clsx(
        'flex h-screen flex-col border-r border-surface-200 bg-white transition-all duration-300',
        sidebarCollapsed ? 'w-16' : 'w-64',
      )}
    >
      {/* Logo */}
      <div className="flex h-16 items-center border-b border-surface-200 px-4">
        <div className="flex items-center gap-2">
          <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-brand-600">
            <span className="text-sm font-bold text-white">A</span>
          </div>
          {!sidebarCollapsed && (
            <span className="text-lg font-bold text-surface-900">AutonoCX</span>
          )}
        </div>
      </div>

      {/* Navigation */}
      <nav className="flex-1 overflow-y-auto px-3 py-4">
        <div className="space-y-1">
          {navItems.map((item) => (
            <NavLink
              key={item.to}
              to={item.to}
              className={({ isActive }) =>
                clsx(
                  'flex items-center gap-3 rounded-lg px-3 py-2 text-sm font-medium transition-colors',
                  isActive
                    ? 'bg-brand-50 text-brand-700'
                    : 'text-surface-600 hover:bg-surface-50 hover:text-surface-900',
                  sidebarCollapsed && 'justify-center px-2',
                )
              }
              title={sidebarCollapsed ? item.label : undefined}
            >
              <item.icon className="h-5 w-5 shrink-0" />
              {!sidebarCollapsed && <span>{item.label}</span>}
            </NavLink>
          ))}
        </div>

        <div className="mt-6 border-t border-surface-100 pt-4">
          {!sidebarCollapsed && (
            <p className="mb-2 px-3 text-xs font-semibold uppercase tracking-wider text-surface-400">
              Settings
            </p>
          )}
          <div className="space-y-1">
            {settingsItems.map((item) => (
              <NavLink
                key={item.to}
                to={item.to}
                className={({ isActive }) =>
                  clsx(
                    'flex items-center gap-3 rounded-lg px-3 py-2 text-sm font-medium transition-colors',
                    isActive
                      ? 'bg-brand-50 text-brand-700'
                      : 'text-surface-600 hover:bg-surface-50 hover:text-surface-900',
                    sidebarCollapsed && 'justify-center px-2',
                  )
                }
                title={sidebarCollapsed ? item.label : undefined}
              >
                <item.icon className="h-5 w-5 shrink-0" />
                {!sidebarCollapsed && <span>{item.label}</span>}
              </NavLink>
            ))}
          </div>
        </div>
      </nav>

      {/* Collapse button */}
      <div className="border-t border-surface-200 p-3">
        <button
          onClick={toggleSidebarCollapsed}
          className="flex w-full items-center justify-center rounded-lg p-2 text-surface-400 hover:bg-surface-50 hover:text-surface-600 transition-colors"
        >
          {sidebarCollapsed ? (
            <ChevronRight className="h-5 w-5" />
          ) : (
            <ChevronLeft className="h-5 w-5" />
          )}
        </button>
      </div>
    </aside>
  );
}
