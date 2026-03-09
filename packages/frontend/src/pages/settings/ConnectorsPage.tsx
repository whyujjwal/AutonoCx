import { useCallback, useEffect, useState } from 'react';
import {
  Plug,
  PlugZap,
  Settings2,
  Trash2,
  RefreshCw,
  ChevronDown,
  ChevronUp,
} from 'lucide-react';
import { Card } from '@/components/ui/Card';
import { Button } from '@/components/ui/Button';
import { Badge } from '@/components/ui/Badge';
import { Input } from '@/components/ui/Input';
import { Modal } from '@/components/ui/Modal';
import { connectorsApi } from '@/api/connectors.api';
import { useNotificationStore } from '@/stores/notificationStore';
import { formatRelativeTime } from '@/lib/formatters';
import type {
  ConnectorConfig,
  ConnectorAvailable,
  ConnectorOperation,
} from '@/types/connector.types';

const statusBadgeVariant: Record<ConnectorConfig['status'], 'success' | 'warning' | 'danger'> = {
  connected: 'success',
  disconnected: 'warning',
  error: 'danger',
};

export default function ConnectorsPage() {
  const { addToast } = useNotificationStore();

  const [available, setAvailable] = useState<ConnectorAvailable[]>([]);
  const [configured, setConfigured] = useState<ConnectorConfig[]>([]);
  const [loading, setLoading] = useState(true);

  // modal state
  const [configureType, setConfigureType] = useState<string | null>(null);
  const [configureDisplayName, setConfigureDisplayName] = useState('');
  const [subdomain, setSubdomain] = useState('');
  const [email, setEmail] = useState('');
  const [apiToken, setApiToken] = useState('');
  const [submitting, setSubmitting] = useState(false);

  // test / disconnect loading per-connector
  const [testingType, setTestingType] = useState<string | null>(null);
  const [removingType, setRemovingType] = useState<string | null>(null);

  // operations expand state
  const [expandedType, setExpandedType] = useState<string | null>(null);
  const [operations, setOperations] = useState<Record<string, ConnectorOperation[]>>({});
  const [operationsLoading, setOperationsLoading] = useState<string | null>(null);

  const configuredTypes = new Set(configured.map((c) => c.connector_type));

  const fetchData = useCallback(async () => {
    setLoading(true);
    try {
      const [availRes, configRes] = await Promise.all([
        connectorsApi.listAvailable(),
        connectorsApi.list(),
      ]);
      setAvailable(availRes.data);
      setConfigured(configRes.data);
    } catch {
      addToast({ type: 'error', title: 'Failed to load connectors' });
    } finally {
      setLoading(false);
    }
  }, [addToast]);

  useEffect(() => {
    void fetchData();
  }, [fetchData]);

  // ---------- Configure modal ----------

  function openConfigureModal(connectorType: string, displayName: string) {
    setConfigureType(connectorType);
    setConfigureDisplayName(displayName);
    setSubdomain('');
    setEmail('');
    setApiToken('');
  }

  function closeConfigureModal() {
    setConfigureType(null);
  }

  async function handleConfigure() {
    if (configureType === null) return;
    setSubmitting(true);
    try {
      await connectorsApi.configure(configureType, {
        config: {
          subdomain,
          email,
          api_token: apiToken,
        },
      });
      addToast({ type: 'success', title: `${configureDisplayName} connected` });
      closeConfigureModal();
      await fetchData();
    } catch {
      addToast({ type: 'error', title: `Failed to configure ${configureDisplayName}` });
    } finally {
      setSubmitting(false);
    }
  }

  // ---------- Test ----------

  async function handleTest(connectorType: string, displayName: string | null) {
    setTestingType(connectorType);
    try {
      const res = await connectorsApi.test(connectorType);
      const health = res.data;
      if (health.status === 'ok') {
        addToast({ type: 'success', title: `${displayName ?? connectorType} is healthy` });
      } else {
        addToast({
          type: 'warning',
          title: `${displayName ?? connectorType}: ${health.error ?? 'unhealthy'}`,
        });
      }
      await fetchData();
    } catch {
      addToast({ type: 'error', title: `Failed to test ${displayName ?? connectorType}` });
    } finally {
      setTestingType(null);
    }
  }

  // ---------- Remove ----------

  async function handleRemove(connectorType: string, displayName: string | null) {
    setRemovingType(connectorType);
    try {
      await connectorsApi.remove(connectorType);
      addToast({ type: 'success', title: `${displayName ?? connectorType} disconnected` });
      await fetchData();
    } catch {
      addToast({ type: 'error', title: `Failed to disconnect ${displayName ?? connectorType}` });
    } finally {
      setRemovingType(null);
    }
  }

  // ---------- Operations ----------

  async function toggleOperations(connectorType: string) {
    if (expandedType === connectorType) {
      setExpandedType(null);
      return;
    }
    setExpandedType(connectorType);
    if (operations[connectorType]) return;
    setOperationsLoading(connectorType);
    try {
      const res = await connectorsApi.getOperations(connectorType);
      setOperations((prev) => ({ ...prev, [connectorType]: res.data }));
    } catch {
      addToast({ type: 'error', title: 'Failed to load operations' });
    } finally {
      setOperationsLoading(null);
    }
  }

  // ---------- Render ----------

  if (loading) {
    return (
      <div className="space-y-6">
        <div>
          <h1 className="text-2xl font-bold text-surface-900">Integrations</h1>
          <p className="mt-1 text-surface-500">Connect external systems to power your AI agents</p>
        </div>
        <div className="rounded-lg border border-surface-200 bg-white p-12 text-center text-surface-500">
          Loading connectors...
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-8">
      {/* Header */}
      <div>
        <h1 className="text-2xl font-bold text-surface-900">Integrations</h1>
        <p className="mt-1 text-surface-500">
          Connect external systems to power your AI agents
        </p>
      </div>

      {/* Available connectors */}
      <section className="space-y-4">
        <h2 className="text-lg font-semibold text-surface-800">Available Connectors</h2>
        {available.length === 0 ? (
          <Card>
            <p className="text-center text-surface-500">No connectors available.</p>
          </Card>
        ) : (
          <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
            {available.map((conn) => {
              const isConfigured = configuredTypes.has(conn.connector_type);
              return (
                <Card key={conn.connector_type}>
                  <div className="flex items-start justify-between">
                    <div className="flex items-center gap-3">
                      <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-brand-50">
                        <Plug className="h-5 w-5 text-brand-600" />
                      </div>
                      <div>
                        <p className="font-medium text-surface-900">{conn.display_name}</p>
                        <p className="text-xs text-surface-500">{conn.connector_type}</p>
                      </div>
                    </div>
                    {isConfigured ? (
                      <Badge variant="success" dot>
                        Connected
                      </Badge>
                    ) : (
                      <Button
                        size="sm"
                        variant="outline"
                        leftIcon={<Settings2 className="h-4 w-4" />}
                        onClick={() =>
                          openConfigureModal(conn.connector_type, conn.display_name)
                        }
                      >
                        Configure
                      </Button>
                    )}
                  </div>
                </Card>
              );
            })}
          </div>
        )}
      </section>

      {/* Connected connectors */}
      {configured.length > 0 && (
        <section className="space-y-4">
          <h2 className="text-lg font-semibold text-surface-800">Connected Integrations</h2>
          <div className="space-y-4">
            {configured.map((conn) => {
              const isExpanded = expandedType === conn.connector_type;
              const ops = operations[conn.connector_type];
              const isOpsLoading = operationsLoading === conn.connector_type;

              return (
                <Card key={conn.id} padding="none">
                  <div className="flex items-center justify-between p-6">
                    <div className="flex items-center gap-4">
                      <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-brand-50">
                        <PlugZap className="h-5 w-5 text-brand-600" />
                      </div>
                      <div>
                        <p className="font-medium text-surface-900">
                          {conn.display_name ?? conn.connector_type}
                        </p>
                        <div className="mt-1 flex items-center gap-3">
                          <Badge variant={statusBadgeVariant[conn.status]} dot size="sm">
                            {conn.status}
                          </Badge>
                          {conn.last_health_check_at && (
                            <span className="text-xs text-surface-400">
                              Last checked {formatRelativeTime(conn.last_health_check_at)}
                            </span>
                          )}
                        </div>
                        {conn.error_message && (
                          <p className="mt-1 text-xs text-danger-500">{conn.error_message}</p>
                        )}
                      </div>
                    </div>
                    <div className="flex items-center gap-2">
                      <Button
                        size="sm"
                        variant="outline"
                        leftIcon={<RefreshCw className="h-3.5 w-3.5" />}
                        isLoading={testingType === conn.connector_type}
                        onClick={() => handleTest(conn.connector_type, conn.display_name)}
                      >
                        Test
                      </Button>
                      <Button
                        size="sm"
                        variant="danger"
                        leftIcon={<Trash2 className="h-3.5 w-3.5" />}
                        isLoading={removingType === conn.connector_type}
                        onClick={() => handleRemove(conn.connector_type, conn.display_name)}
                      >
                        Disconnect
                      </Button>
                      <button
                        onClick={() => toggleOperations(conn.connector_type)}
                        className="ml-1 rounded-lg p-2 text-surface-400 hover:bg-surface-50 hover:text-surface-600 transition-colors"
                        title="View operations"
                      >
                        {isExpanded ? (
                          <ChevronUp className="h-4 w-4" />
                        ) : (
                          <ChevronDown className="h-4 w-4" />
                        )}
                      </button>
                    </div>
                  </div>

                  {/* Operations panel */}
                  {isExpanded && (
                    <div className="border-t border-surface-200 bg-surface-50 px-6 py-4">
                      <p className="mb-3 text-sm font-medium text-surface-700">
                        Available Operations
                      </p>
                      {isOpsLoading ? (
                        <p className="text-sm text-surface-400">Loading operations...</p>
                      ) : ops && ops.length > 0 ? (
                        <div className="space-y-2">
                          {ops.map((op) => (
                            <div
                              key={op.name}
                              className="flex items-start justify-between rounded-lg border border-surface-200 bg-white px-4 py-3"
                            >
                              <div>
                                <p className="text-sm font-medium text-surface-800">
                                  {op.display_name}
                                </p>
                                <p className="text-xs text-surface-500">{op.description}</p>
                              </div>
                              <div className="flex shrink-0 items-center gap-2">
                                <Badge
                                  variant={
                                    op.risk_level === 'high'
                                      ? 'danger'
                                      : op.risk_level === 'medium'
                                        ? 'warning'
                                        : 'success'
                                  }
                                  size="sm"
                                >
                                  {op.risk_level}
                                </Badge>
                                {op.requires_approval && (
                                  <Badge variant="outline" size="sm">
                                    Approval required
                                  </Badge>
                                )}
                              </div>
                            </div>
                          ))}
                        </div>
                      ) : (
                        <p className="text-sm text-surface-400">No operations found.</p>
                      )}
                    </div>
                  )}
                </Card>
              );
            })}
          </div>
        </section>
      )}

      {/* Configure modal */}
      <Modal
        isOpen={configureType !== null}
        onClose={closeConfigureModal}
        title={`Configure ${configureDisplayName}`}
        size="md"
      >
        <div className="space-y-4">
          <Input
            label="Subdomain"
            placeholder="yourcompany"
            value={subdomain}
            onChange={(e) => setSubdomain(e.target.value)}
            hint="Your Zendesk subdomain (e.g. yourcompany.zendesk.com)"
          />
          <Input
            label="Email"
            type="email"
            placeholder="admin@example.com"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
          />
          <Input
            label="API Token"
            type="password"
            placeholder="Enter your API token"
            value={apiToken}
            onChange={(e) => setApiToken(e.target.value)}
          />
          <div className="flex justify-end gap-3 pt-2">
            <Button variant="outline" onClick={closeConfigureModal}>
              Cancel
            </Button>
            <Button
              onClick={handleConfigure}
              isLoading={submitting}
              disabled={!subdomain || !email || !apiToken}
              leftIcon={<PlugZap className="h-4 w-4" />}
            >
              Test &amp; Connect
            </Button>
          </div>
        </div>
      </Modal>
    </div>
  );
}
