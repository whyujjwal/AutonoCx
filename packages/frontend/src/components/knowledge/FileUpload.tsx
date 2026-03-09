import { useCallback, useRef, useState, type DragEvent } from 'react';
import { Upload, File, X } from 'lucide-react';
import { clsx } from 'clsx';
import { Button } from '@/components/ui/Button';
import { formatFileSize } from '@/lib/formatters';

const ACCEPTED_TYPES = ['.pdf', '.docx', '.txt', '.md', '.csv', '.json'];
const ACCEPTED_MIME_TYPES = [
  'application/pdf',
  'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
  'text/plain',
  'text/markdown',
  'text/csv',
  'application/json',
];
const MAX_SIZE_BYTES = 50 * 1024 * 1024; // 50MB

interface FileUploadProps {
  onUpload: (file: File) => Promise<void>;
  isUploading: boolean;
  uploadProgress: number;
}

export function FileUpload({ onUpload, isUploading, uploadProgress }: FileUploadProps) {
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [dragOver, setDragOver] = useState(false);
  const [validationError, setValidationError] = useState<string | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const validateFile = useCallback((file: File): string | null => {
    const extension = '.' + file.name.split('.').pop()?.toLowerCase();
    const isValidType =
      ACCEPTED_TYPES.includes(extension) || ACCEPTED_MIME_TYPES.includes(file.type);
    if (!isValidType) {
      return `Unsupported file type. Accepted: ${ACCEPTED_TYPES.join(', ')}`;
    }
    if (file.size > MAX_SIZE_BYTES) {
      return `File too large. Maximum size is ${formatFileSize(MAX_SIZE_BYTES)}.`;
    }
    return null;
  }, []);

  const handleFileSelect = useCallback(
    (file: File) => {
      const error = validateFile(file);
      if (error) {
        setValidationError(error);
        setSelectedFile(null);
        return;
      }
      setValidationError(null);
      setSelectedFile(file);
    },
    [validateFile],
  );

  const handleDrop = useCallback(
    (e: DragEvent<HTMLDivElement>) => {
      e.preventDefault();
      e.stopPropagation();
      setDragOver(false);

      const file = e.dataTransfer.files[0];
      if (file) {
        handleFileSelect(file);
      }
    },
    [handleFileSelect],
  );

  const handleDragOver = useCallback((e: DragEvent<HTMLDivElement>) => {
    e.preventDefault();
    e.stopPropagation();
    setDragOver(true);
  }, []);

  const handleDragLeave = useCallback((e: DragEvent<HTMLDivElement>) => {
    e.preventDefault();
    e.stopPropagation();
    setDragOver(false);
  }, []);

  const handleInputChange = useCallback(
    (e: React.ChangeEvent<HTMLInputElement>) => {
      const file = e.target.files?.[0];
      if (file) {
        handleFileSelect(file);
      }
      // Reset input so the same file can be re-selected
      e.target.value = '';
    },
    [handleFileSelect],
  );

  const handleUploadClick = useCallback(async () => {
    if (!selectedFile) return;
    await onUpload(selectedFile);
    setSelectedFile(null);
  }, [selectedFile, onUpload]);

  const clearSelection = useCallback(() => {
    setSelectedFile(null);
    setValidationError(null);
  }, []);

  return (
    <div className="space-y-4">
      <input
        ref={fileInputRef}
        type="file"
        accept={ACCEPTED_TYPES.join(',')}
        onChange={handleInputChange}
        className="hidden"
      />

      <div
        onDrop={handleDrop}
        onDragOver={handleDragOver}
        onDragLeave={handleDragLeave}
        onClick={() => !isUploading && fileInputRef.current?.click()}
        className={clsx(
          'flex cursor-pointer flex-col items-center justify-center rounded-lg border-2 border-dashed px-6 py-8 transition-colors',
          dragOver
            ? 'border-brand-500 bg-brand-50'
            : 'border-surface-300 hover:border-brand-400 hover:bg-surface-50',
          isUploading && 'pointer-events-none opacity-60',
        )}
      >
        <Upload
          className={clsx(
            'mb-3 h-8 w-8',
            dragOver ? 'text-brand-500' : 'text-surface-400',
          )}
        />
        <p className="text-sm font-medium text-surface-700">
          {dragOver ? 'Drop file here' : 'Drag and drop a file, or click to browse'}
        </p>
        <p className="mt-1 text-xs text-surface-500">
          {ACCEPTED_TYPES.join(', ')} &mdash; max {formatFileSize(MAX_SIZE_BYTES)}
        </p>
      </div>

      {validationError && (
        <p className="text-sm text-danger-600">{validationError}</p>
      )}

      {selectedFile && (
        <div className="flex items-center justify-between rounded-lg border border-surface-200 bg-surface-50 px-4 py-3">
          <div className="flex items-center gap-3 overflow-hidden">
            <File className="h-5 w-5 shrink-0 text-surface-500" />
            <div className="min-w-0">
              <p className="truncate text-sm font-medium text-surface-800">
                {selectedFile.name}
              </p>
              <p className="text-xs text-surface-500">
                {formatFileSize(selectedFile.size)}
              </p>
            </div>
          </div>

          <div className="flex items-center gap-2">
            {!isUploading && (
              <button
                onClick={(e) => {
                  e.stopPropagation();
                  clearSelection();
                }}
                className="rounded p-1 text-surface-400 hover:text-surface-600"
              >
                <X className="h-4 w-4" />
              </button>
            )}
          </div>
        </div>
      )}

      {isUploading && (
        <div className="space-y-1">
          <div className="flex items-center justify-between text-xs text-surface-600">
            <span>Uploading...</span>
            <span>{uploadProgress}%</span>
          </div>
          <div className="h-2 overflow-hidden rounded-full bg-surface-200">
            <div
              className="h-full rounded-full bg-brand-500 transition-all duration-300"
              style={{ width: `${uploadProgress}%` }}
            />
          </div>
        </div>
      )}

      {selectedFile && !isUploading && (
        <Button
          className="w-full"
          leftIcon={<Upload className="h-4 w-4" />}
          onClick={handleUploadClick}
        >
          Upload {selectedFile.name}
        </Button>
      )}
    </div>
  );
}
