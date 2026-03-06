import { useState } from 'react';
import { Plus, Upload, BookOpen, FileText, Search, Trash2, MoreVertical } from 'lucide-react';
import { Button } from '@/components/ui/Button';
import { Card } from '@/components/ui/Card';
import { Badge } from '@/components/ui/Badge';
import { Input } from '@/components/ui/Input';
import { Modal } from '@/components/ui/Modal';
import { Dropdown } from '@/components/ui/Dropdown';
import { EmptyState } from '@/components/common/EmptyState';
import { formatFileSize, formatDate } from '@/lib/formatters';

const mockKBs = [
  {
    id: '1',
    name: 'Product Documentation',
    description: 'Official product docs including API reference and user guides.',
    documentCount: 48,
    totalChunks: 1245,
    totalSizeBytes: 15_200_000,
    embeddingModel: 'text-embedding-3-small',
    updatedAt: '2024-03-01T10:00:00Z',
    documents: [
      { id: 'd1', name: 'api-reference.md', type: 'md', status: 'indexed', sizeBytes: 245000, chunkCount: 32 },
      { id: 'd2', name: 'getting-started.pdf', type: 'pdf', status: 'indexed', sizeBytes: 1200000, chunkCount: 45 },
      { id: 'd3', name: 'faq.md', type: 'md', status: 'indexed', sizeBytes: 89000, chunkCount: 18 },
      { id: 'd4', name: 'changelog.md', type: 'md', status: 'processing', sizeBytes: 56000, chunkCount: 0 },
    ],
  },
  {
    id: '2',
    name: 'Company Policies',
    description: 'Internal policies, refund guidelines, and compliance documents.',
    documentCount: 12,
    totalChunks: 340,
    totalSizeBytes: 4_800_000,
    embeddingModel: 'text-embedding-3-small',
    updatedAt: '2024-02-28T14:00:00Z',
    documents: [
      { id: 'd5', name: 'refund-policy.pdf', type: 'pdf', status: 'indexed', sizeBytes: 320000, chunkCount: 15 },
      { id: 'd6', name: 'privacy-policy.pdf', type: 'pdf', status: 'indexed', sizeBytes: 450000, chunkCount: 22 },
    ],
  },
  {
    id: '3',
    name: 'FAQ Database',
    description: 'Frequently asked questions and their answers.',
    documentCount: 5,
    totalChunks: 120,
    totalSizeBytes: 980_000,
    embeddingModel: 'text-embedding-3-small',
    updatedAt: '2024-02-25T09:00:00Z',
    documents: [],
  },
];

const docStatusVariant: Record<string, 'success' | 'warning' | 'danger'> = {
  indexed: 'success',
  processing: 'warning',
  failed: 'danger',
};

export default function KnowledgeBasePage() {
  const [selectedKB, setSelectedKB] = useState<typeof mockKBs[number] | null>(null);
  const [showCreateModal, setShowCreateModal] = useState(false);
  const [searchQuery, setSearchQuery] = useState('');

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-surface-900">Knowledge Base</h1>
          <p className="mt-1 text-surface-500">Manage documents that power your AI agents</p>
        </div>
        <Button leftIcon={<Plus className="h-4 w-4" />} onClick={() => setShowCreateModal(true)}>
          Create Knowledge Base
        </Button>
      </div>

      <div className="grid grid-cols-1 gap-6 lg:grid-cols-3">
        {/* KB List */}
        <div className="space-y-3">
          {mockKBs.map((kb) => (
            <Card
              key={kb.id}
              padding="md"
              hover
              className={selectedKB?.id === kb.id ? 'ring-2 ring-brand-500' : ''}
              onClick={() => setSelectedKB(kb)}
            >
              <div className="flex items-start justify-between">
                <div className="flex items-center gap-3">
                  <div className="flex h-9 w-9 items-center justify-center rounded-lg bg-brand-50">
                    <BookOpen className="h-4.5 w-4.5 text-brand-600" />
                  </div>
                  <div>
                    <h3 className="text-sm font-semibold text-surface-800">{kb.name}</h3>
                    <p className="text-xs text-surface-500">
                      {kb.documentCount} docs &middot; {formatFileSize(kb.totalSizeBytes)}
                    </p>
                  </div>
                </div>
                <Dropdown
                  trigger={
                    <button className="rounded p-1 text-surface-400 hover:bg-surface-50">
                      <MoreVertical className="h-4 w-4" />
                    </button>
                  }
                  items={[
                    { id: 'delete', label: 'Delete', icon: <Trash2 className="h-4 w-4" />, onClick: () => {}, variant: 'danger' },
                  ]}
                />
              </div>
              <p className="mt-2 text-xs text-surface-500 line-clamp-2">{kb.description}</p>
            </Card>
          ))}
        </div>

        {/* KB Detail */}
        <div className="lg:col-span-2">
          {selectedKB ? (
            <Card padding="none">
              <div className="border-b border-surface-200 px-6 py-4">
                <div className="flex items-center justify-between">
                  <div>
                    <h2 className="text-lg font-semibold text-surface-900">{selectedKB.name}</h2>
                    <p className="mt-1 text-sm text-surface-500">{selectedKB.description}</p>
                  </div>
                  <Button variant="outline" size="sm" leftIcon={<Upload className="h-4 w-4" />}>
                    Upload Document
                  </Button>
                </div>
                <div className="mt-4 flex gap-4 text-sm text-surface-600">
                  <span>{selectedKB.documentCount} documents</span>
                  <span>&middot;</span>
                  <span>{selectedKB.totalChunks} chunks</span>
                  <span>&middot;</span>
                  <span>{formatFileSize(selectedKB.totalSizeBytes)}</span>
                  <span>&middot;</span>
                  <span>Updated {formatDate(selectedKB.updatedAt)}</span>
                </div>
              </div>

              {/* Search */}
              <div className="border-b border-surface-200 px-6 py-3">
                <Input
                  placeholder="Search documents or test a query..."
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                  leftIcon={<Search className="h-4 w-4" />}
                />
              </div>

              {/* Documents */}
              <div className="divide-y divide-surface-100">
                {selectedKB.documents.length === 0 ? (
                  <div className="px-6 py-12">
                    <EmptyState
                      icon={<FileText className="h-12 w-12" />}
                      title="No documents yet"
                      description="Upload documents to start building this knowledge base."
                      action={
                        <Button variant="outline" size="sm" leftIcon={<Upload className="h-4 w-4" />}>
                          Upload Document
                        </Button>
                      }
                    />
                  </div>
                ) : (
                  selectedKB.documents.map((doc) => (
                    <div key={doc.id} className="flex items-center justify-between px-6 py-3">
                      <div className="flex items-center gap-3">
                        <FileText className="h-5 w-5 text-surface-400" />
                        <div>
                          <p className="text-sm font-medium text-surface-800">{doc.name}</p>
                          <p className="text-xs text-surface-500">
                            {formatFileSize(doc.sizeBytes)} &middot; {doc.chunkCount} chunks
                          </p>
                        </div>
                      </div>
                      <div className="flex items-center gap-3">
                        <Badge variant={docStatusVariant[doc.status]} dot size="sm">
                          {doc.status}
                        </Badge>
                        <button className="rounded p-1 text-surface-400 hover:text-danger-500">
                          <Trash2 className="h-4 w-4" />
                        </button>
                      </div>
                    </div>
                  ))
                )}
              </div>
            </Card>
          ) : (
            <div className="flex h-full items-center justify-center">
              <EmptyState
                icon={<BookOpen className="h-12 w-12" />}
                title="Select a knowledge base"
                description="Choose a knowledge base from the list to view its documents."
              />
            </div>
          )}
        </div>
      </div>

      {/* Create KB Modal */}
      <Modal isOpen={showCreateModal} onClose={() => setShowCreateModal(false)} title="Create Knowledge Base">
        <div className="space-y-4">
          <Input label="Name" placeholder="e.g., Product Documentation" />
          <div>
            <label className="mb-1.5 block text-sm font-medium text-surface-700">Description</label>
            <textarea
              rows={3}
              placeholder="Describe the purpose of this knowledge base..."
              className="w-full rounded-lg border border-surface-300 px-3 py-2 text-sm focus:border-brand-500 focus:outline-none focus:ring-2 focus:ring-brand-500/20"
            />
          </div>
          <div className="flex justify-end gap-3 pt-2">
            <Button variant="outline" onClick={() => setShowCreateModal(false)}>
              Cancel
            </Button>
            <Button>Create</Button>
          </div>
        </div>
      </Modal>
    </div>
  );
}
