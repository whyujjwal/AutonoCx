import { createBrowserRouter } from 'react-router-dom';
import App from './App';
import { AuthLayout } from '@/components/layout/AuthLayout';
import { DashboardLayout } from '@/components/layout/DashboardLayout';
import { ProtectedRoute } from '@/components/common/ProtectedRoute';
import { ErrorBoundary } from '@/components/common/ErrorBoundary';

import LoginPage from '@/pages/auth/LoginPage';
import RegisterPage from '@/pages/auth/RegisterPage';
import DashboardPage from '@/pages/dashboard/DashboardPage';
import ConversationsPage from '@/pages/conversations/ConversationsPage';
import ConversationDetailPage from '@/pages/conversations/ConversationDetailPage';
import AgentsPage from '@/pages/agents/AgentsPage';
import AgentConfigPage from '@/pages/agents/AgentConfigPage';
import KnowledgeBasePage from '@/pages/knowledge/KnowledgeBasePage';
import WorkflowsPage from '@/pages/workflows/WorkflowsPage';
import WorkflowEditorPage from '@/pages/workflows/WorkflowEditorPage';
import ToolsPage from '@/pages/tools/ToolsPage';
import ToolConfigPage from '@/pages/tools/ToolConfigPage';
import ActionQueuePage from '@/pages/actions/ActionQueuePage';
import ActionHistoryPage from '@/pages/actions/ActionHistoryPage';
import PromptsPage from '@/pages/prompts/PromptsPage';
import PromptEditorPage from '@/pages/prompts/PromptEditorPage';
import ChannelsPage from '@/pages/channels/ChannelsPage';
import AnalyticsPage from '@/pages/analytics/AnalyticsPage';
import AuditLogPage from '@/pages/audit/AuditLogPage';
import SettingsPage from '@/pages/settings/SettingsPage';
import UsersPage from '@/pages/settings/UsersPage';
import SecurityPage from '@/pages/settings/SecurityPage';
import ConnectorsPage from '@/pages/settings/ConnectorsPage';
import NotFoundPage from '@/pages/NotFoundPage';

export const router = createBrowserRouter([
  {
    path: '/',
    element: <App />,
    errorElement: <ErrorBoundary />,
    children: [
      {
        element: <AuthLayout />,
        children: [
          { path: 'login', element: <LoginPage /> },
          { path: 'register', element: <RegisterPage /> },
        ],
      },
      {
        element: (
          <ProtectedRoute>
            <DashboardLayout />
          </ProtectedRoute>
        ),
        children: [
          { index: true, element: <DashboardPage /> },
          { path: 'dashboard', element: <DashboardPage /> },
          { path: 'conversations', element: <ConversationsPage /> },
          { path: 'conversations/:id', element: <ConversationDetailPage /> },
          { path: 'agents', element: <AgentsPage /> },
          { path: 'agents/new', element: <AgentConfigPage /> },
          { path: 'agents/:id', element: <AgentConfigPage /> },
          { path: 'knowledge', element: <KnowledgeBasePage /> },
          { path: 'workflows', element: <WorkflowsPage /> },
          { path: 'workflows/new', element: <WorkflowEditorPage /> },
          { path: 'workflows/:id', element: <WorkflowEditorPage /> },
          { path: 'tools', element: <ToolsPage /> },
          { path: 'tools/new', element: <ToolConfigPage /> },
          { path: 'tools/:id', element: <ToolConfigPage /> },
          { path: 'actions', element: <ActionQueuePage /> },
          { path: 'actions/history', element: <ActionHistoryPage /> },
          { path: 'prompts', element: <PromptsPage /> },
          { path: 'prompts/new', element: <PromptEditorPage /> },
          { path: 'prompts/:id', element: <PromptEditorPage /> },
          { path: 'channels', element: <ChannelsPage /> },
          { path: 'analytics', element: <AnalyticsPage /> },
          { path: 'audit', element: <AuditLogPage /> },
          { path: 'settings', element: <SettingsPage /> },
          { path: 'settings/users', element: <UsersPage /> },
          { path: 'settings/security', element: <SecurityPage /> },
          { path: 'settings/connectors', element: <ConnectorsPage /> },
        ],
      },
      { path: '*', element: <NotFoundPage /> },
    ],
  },
]);
