import { useCallback, useEffect, useRef, useState } from 'react';
import { Plus, Upload, BookOpen, FileText, Search, Trash2, MoreVertical } from 'lucide-react';
import { Button } from '@/components/ui/Button';
import { Card } from '@/components/ui/Card';
import { Badge } from '@/components/ui/Badge';
import { Input } from '@/components/ui/Input';
import { Modal } from '@/components/ui/Modal';
import { Dropdown } from '@/components/ui/Dropdown';
import { EmptyState } from '@/components/common/EmptyState';
import { Spinner, PageSpinner } from '@/components/ui/Spinner';
import { FileUpload } from '@/components/knowledge/FileUpload';
import { formatFileSize, formatDate } from '@/lib/formatters';
import { knowledgeApi } from '@/api/knowledge.api';
import { useNotificationStore } from '@/stores/notificationStore';
import type { KnowledgeBase, KBDocument, DocumentStatus } from '@/types/knowledge.types';

const docStatusVariant: Record<DocumentStatus, 'success' | 'warning' | 'danger'> = {
  pending: 'warning',
  processing: 'warning',
  indexed: 'success',
  failed: 'danger',
};

export default function KnowledgeBasePage() {
  const addToast = useNotificationStore((s) => s.addToast);

  // --- KB list state ---
  const [knowledgeBases, setKnowledgeBases] = useState<KnowledgeBase[]>([]);
  const [kbLoading, setKbLoading] = useState(true);
  const [kbError, setKbError] = useState<string | null>(null);

  // --- Selected KB + documents ---
  const [selectedKBId, setSelectedKBId] = useState<string | null>(null);
  const [documents, setDocuments] = useState<KBDocument[]>([]);
  const [docsLoading, setDocsLoading] = useState(false);
  const [docsError, setDocsError] = useState<string | null>(null);

  // --- Create modal ---
  const [showCreateModal, setShowCreateModal] = useState(false);
  const [createName, setCreateName] = useState('');
  const [createDescription, setCreateDescription] = useState('');
  const [creating, setCreating] = useState(false);

  // --- Upload modal ---
  const [showUploadModal, setShowUploadModal] = useState(false);
  const [isUploading, setIsUploading] = useState(false);
  const [uploadProgress, setUploadProgress] = useState(0);

  // --- Search ---
  const [searchQuery, setSearchQuery] = useState('');

  // --- Polling refs ---
  const pollingTimerRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const pollingDocIdRef = useRef<string | null>(null);

  const selectedKB = knowledgeBases.find((kb) => kb.id === selectedKBId) ?? null;

  // --- Fetch KBs ---
  const fetchKBs = useCallback(async () => {
    setKbLoading(true);
    setKbError(null);
    try {
      const res = await knowledgeApi.listKBs({ page_size: 100 });
      setKnowledgeBases(res.data.items);
    } catch {
      setKbError('Failed to load knowledge bases');
    } finally {
      setKbLoading(false);
    }
  }, []);

  useEffect(() => {
    void fetchKBs();
  }, [fetchKBs]);

  // --- Fetch documents for selected KB ---
  const fetchDocuments = useCallback(async (kbId: string) => {
    setDocsLoading(true);
    setDocsError(null);
    try {
      const res = await knowledgeApi.listDocuments(kbId, { page_size: 200 });
      setDocuments(res.data.items);
    } catch {
      setDocsError('Failed to load documents');
    } finally {
      setDocsLoading(false);
    }
  }, []);

  useEffect(() => {
    if (selectedKBId) {
      void fetchDocuments(selectedKBId);
    } else {
      setDocuments([]);
    }
  }, [selectedKBId, fetchDocuments]);

  // --- Cleanup polling on unmount ---
  useEffect(() => {
    return () => {
      if (pollingTimerRef.current) {
        clearInterval(pollingTimerRef.current);
      }
    };
  }, []);

  // --- Create KB ---
  const handleCreateKB = useCallback(async () => {
    if (!createName.trim()) return;
    setCreating(true);
    try {
      await knowledgeApi.createKB({
        name: createName.trim(),
        description: createDescription.trim() || undefined,
      });
      addToast({ type: 'success', title: 'Knowledge base created' });
      setShowCreateModal(false);
      setCreateName('');
      setCreateDescription('');
      await fetchKBs();
    } catch {
      addToast({ type: 'error', title: 'Failed to create knowledge base' });
    } finally {
      setCreating(false);
    }
  }, [createName, createDescription, addToast, fetchKBs]);

  // --- Delete KB ---
  const handleDeleteKB = useCallback(
    async (kbId: string) => {
      try {
        await knowledgeApi.deleteKB(kbId);
        addToast({ type: 'success', title: 'Knowledge base deleted' });
        if (selectedKBId === kbId) {
          setSelectedKBId(null);
          setDocuments([]);
        }
        await fetchKBs();
      } catch {
        addToast({ type: 'error', title: 'Failed to delete knowledge base' });
      }
    },
    [selectedKBId, addToast, fetchKBs],
  );

  // --- Poll document status until indexed or failed ---
  const pollDocumentStatus = useCallback(
    (kbId: string, docId: string) => {
      if (pollingTimerRef.current) {
        clearInterval(pollingTimerRef.current);
      }
      pollingDocIdRef.current = docId;

      pollingTimerRef.current = setInterval(async () => {
        try {
          const res = await knowledgeApi.getDocument(kbId, docId);
          const doc = res.data;

          setDocuments((prev) =>
            prev.map((d) => (d.id === docId ? doc : d)),
          );

          if (doc.status === 'indexed') {
            clearInterval(pollingTimerRef.current!);
            pollingTimerRef.current = null;
            pollingDocIdRef.current = null;
            addToast({ type: 'success', title: 'Document indexed successfully' });
            void fetchKBs();
          } else if (doc.status === 'failed') {
            clearInterval(pollingTimerRef.current!);
            pollingTimerRef.current = null;
            pollingDocIdRef.current = null;
            addToast({
              type: 'error',
              title: 'Document processing failed',
              message: doc.error_message ?? 'Unknown error',
            });
          }
        } catch {
          // Silently retry on network errors
        }
      }, 3000);
    },
    [addToast, fetchKBs],
  );

  // --- Upload document ---
  const handleUploadDocument = useCallback(
    async (file: File) => {
      if (!selectedKBId) return;
      setIsUploading(true);
      setUploadProgress(0);
      try {
        const res = await knowledgeApi.uploadDocument(selectedKBId, file, (progress) => {
          setUploadProgress(progress);
        });
        const uploadedDoc = res.data;
        setDocuments((prev) => [uploadedDoc, ...prev]);
        addToast({ type: 'success', title: 'Document uploaded', message: 'Processing started...' });
        setShowUploadModal(false);

        if (uploadedDoc.status === 'pending' || uploadedDoc.status === 'processing') {
          pollDocumentStatus(selectedKBId, uploadedDoc.id);
        }

        void fetchKBs();
      } catch {
        addToast({ type: 'error', title: 'Upload failed' });
      } finally {
        setIsUploading(false);
        setUploadProgress(0);
      }
    },
    [selectedKBId, addToast, pollDocumentStatus, fetchKBs],
  );

  // --- Delete document ---
  const handleDeleteDocument = useCallback(
    async (docId: string) => {
      if (!selectedKBId) return;
      try {
        await knowledgeApi.deleteDocument(selectedKBId, docId);
        setDocuments((prev) => prev.filter((d) => d.id !== docId));
        addToast({ type: 'success', title: 'Document deleted' });
        if (pollingDocIdRef.current === docId && pollingTimerRef.current) {
          clearInterval(pollingTimerRef.current);
          pollingTimerRef.current = null;
          pollingDocIdRef.current = null;
        }
        void fetchKBs();
      } catch {
        addToast({ type: 'error', title: 'Failed to delete document' });
      }
    },
    [selectedKBId, addToast, fetchKBs],
  );

  // --- Filter documents by search ---
  const filteredDocuments = searchQuery.trim()
    ? documents.filter((d) =>
        d.filename.toLowerCase().includes(searchQuery.toLowerCase()),
      )
    : documents;

  // --- Loading state ---
  if (kbLoading) {
    return <PageSpinner />;
  }

  // --- Error state ---
  if (kbError) {
    return (
      <div className="flex h-64 flex-col items-center justify-center gap-4">
        <p className="text-sm text-danger-600">{kbError}</p>
        <Button variant="outline" size="sm" onClick={() => void fetchKBs()}>
          Retry
        </Button>
      </div>
    );
  }

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
          {knowledgeBases.length === 0 ? (
            <EmptyState
              icon={<BookOpen className="h-12 w-12" />}
              title="No knowledge bases"
              description="Create your first knowledge base to get started."
              action={
                <Button
                  variant="outline"
                  size="sm"
                  leftIcon={<Plus className="h-4 w-4" />}
                  onClick={() => setShowCreateModal(true)}
                >
                  Create Knowledge Base
                </Button>
              }
            />
          ) : (
            knowledgeBases.map((kb) => (
              <Card
                key={kb.id}
                padding="md"
                hover
                className={selectedKBId === kb.id ? 'ring-2 ring-brand-500' : ''}
                onClick={() => setSelectedKBId(kb.id)}
              >
                <div className="flex items-start justify-between">
                  <div className="flex items-center gap-3">
                    <div className="flex h-9 w-9 items-center justify-center rounded-lg bg-brand-50">
                      <BookOpen className="h-4.5 w-4.5 text-brand-600" />
                    </div>
                    <div>
                      <h3 className="text-sm font-semibold text-surface-800">{kb.name}</h3>
                      <p className="text-xs text-surface-500">
                        {kb.document_count} docs
                      </p>
                    </div>
                  </div>
                  <Dropdown
                    trigger={
                      <button
                        className="rounded p-1 text-surface-400 hover:bg-surface-50"
                        onClick={(e) => e.stopPropagation()}
                      >
                        <MoreVertical className="h-4 w-4" />
                      </button>
                    }
                    items={[
                      {
                        id: 'delete',
                        label: 'Delete',
                        icon: <Trash2 className="h-4 w-4" />,
                        onClick: () => void handleDeleteKB(kb.id),
                        variant: 'danger',
                      },
                    ]}
                  />
                </div>
                <p className="mt-2 text-xs text-surface-500 line-clamp-2">{kb.description}</p>
              </Card>
            ))
          )}
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
                  <Button
                    variant="outline"
                    size="sm"
                    leftIcon={<Upload className="h-4 w-4" />}
                    onClick={() => setShowUploadModal(true)}
                  >
                    Upload Document
                  </Button>
                </div>
                <div className="mt-4 flex gap-4 text-sm text-surface-600">
                  <span>{selectedKB.document_count} documents</span>
                  <span>&middot;</span>
                  <span>{selectedKB.total_chunks} chunks</span>
                  <span>&middot;</span>
                  <span>Updated {formatDate(selectedKB.updated_at)}</span>
                </div>
              </div>

              {/* Search */}
              <div className="border-b border-surface-200 px-6 py-3">
                <Input
                  placeholder="Search documents..."
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                  leftIcon={<Search className="h-4 w-4" />}
                />
              </div>

              {/* Documents */}
              <div className="divide-y divide-surface-100">
                {docsLoading ? (
                  <div className="flex items-center justify-center py-12">
                    <Spinner size="md" />
                  </div>
                ) : docsError ? (
                  <div className="flex flex-col items-center justify-center gap-3 px-6 py-12">
                    <p className="text-sm text-danger-600">{docsError}</p>
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={() => void fetchDocuments(selectedKBId!)}
                    >
                      Retry
                    </Button>
                  </div>
                ) : filteredDocuments.length === 0 ? (
                  <div className="px-6 py-12">
                    <EmptyState
                      icon={<FileText className="h-12 w-12" />}
                      title={searchQuery.trim() ? 'No matching documents' : 'No documents yet'}
                      description={
                        searchQuery.trim()
                          ? 'Try a different search term.'
                          : 'Upload documents to start building this knowledge base.'
                      }
                      action={
                        !searchQuery.trim() ? (
                          <Button
                            variant="outline"
                            size="sm"
                            leftIcon={<Upload className="h-4 w-4" />}
                            onClick={() => setShowUploadModal(true)}
                          >
                            Upload Document
                          </Button>
                        ) : undefined
                      }
                    />
                  </div>
                ) : (
                  filteredDocuments.map((doc) => (
                    <div key={doc.id} className="flex items-center justify-between px-6 py-3">
                      <div className="flex items-center gap-3">
                        <FileText className="h-5 w-5 text-surface-400" />
                        <div>
                          <p className="text-sm font-medium text-surface-800">{doc.filename}</p>
                          <p className="text-xs text-surface-500">
                            {doc.file_size_bytes ? formatFileSize(doc.file_size_bytes) : '—'} &middot; {doc.chunk_count} chunks
                          </p>
                        </div>
                      </div>
                      <div className="flex items-center gap-3">
                        <Badge variant={docStatusVariant[doc.status]} dot size="sm">
                          {doc.status}
                        </Badge>
                        <button
                          onClick={() => void handleDeleteDocument(doc.id)}
                          className="rounded p-1 text-surface-400 hover:text-danger-500"
                        >
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
          <Input
            label="Name"
            placeholder="e.g., Product Documentation"
            value={createName}
            onChange={(e) => setCreateName(e.target.value)}
          />
          <div>
            <label className="mb-1.5 block text-sm font-medium text-surface-700">Description</label>
            <textarea
              rows={3}
              placeholder="Describe the purpose of this knowledge base..."
              value={createDescription}
              onChange={(e) => setCreateDescription(e.target.value)}
              className="w-full rounded-lg border border-surface-300 px-3 py-2 text-sm focus:border-brand-500 focus:outline-none focus:ring-2 focus:ring-brand-500/20"
            />
          </div>
          <div className="flex justify-end gap-3 pt-2">
            <Button variant="outline" onClick={() => setShowCreateModal(false)} disabled={creating}>
              Cancel
            </Button>
            <Button
              onClick={() => void handleCreateKB()}
              isLoading={creating}
              disabled={!createName.trim()}
            >
              Create
            </Button>
          </div>
        </div>
      </Modal>

      {/* Upload Document Modal */}
      <Modal
        isOpen={showUploadModal}
        onClose={() => {
          if (!isUploading) setShowUploadModal(false);
        }}
        title="Upload Document"
      >
        <FileUpload
          onUpload={handleUploadDocument}
          isUploading={isUploading}
          uploadProgress={uploadProgress}
        />
      </Modal>
    </div>
  );
}
