import { Component, type ErrorInfo, type ReactNode } from 'react';
import { useRouteError, isRouteErrorResponse, Link } from 'react-router-dom';
import { AlertTriangle, Home, RefreshCw } from 'lucide-react';
import { Button } from '@/components/ui/Button';

// For React Router error boundary
export function ErrorBoundary() {
  const error = useRouteError();

  if (isRouteErrorResponse(error)) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-surface-50 p-8">
        <div className="text-center">
          <h1 className="text-6xl font-bold text-surface-300">{error.status}</h1>
          <p className="mt-4 text-xl font-semibold text-surface-800">{error.statusText}</p>
          <p className="mt-2 text-surface-500">
            {error.data?.message || 'Something went wrong.'}
          </p>
          <div className="mt-6 flex gap-3 justify-center">
            <Link to="/dashboard">
              <Button variant="primary" leftIcon={<Home className="h-4 w-4" />}>
                Go Home
              </Button>
            </Link>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="flex min-h-screen items-center justify-center bg-surface-50 p-8">
      <div className="text-center">
        <AlertTriangle className="mx-auto h-16 w-16 text-warning-500" />
        <h1 className="mt-4 text-2xl font-bold text-surface-900">Something went wrong</h1>
        <p className="mt-2 text-surface-500">An unexpected error occurred. Please try again.</p>
        <div className="mt-6 flex gap-3 justify-center">
          <Button
            variant="outline"
            leftIcon={<RefreshCw className="h-4 w-4" />}
            onClick={() => window.location.reload()}
          >
            Reload Page
          </Button>
          <Link to="/dashboard">
            <Button variant="primary" leftIcon={<Home className="h-4 w-4" />}>
              Go Home
            </Button>
          </Link>
        </div>
      </div>
    </div>
  );
}

// For class component error boundary (wrapping children)
interface Props {
  children: ReactNode;
  fallback?: ReactNode;
}

interface State {
  hasError: boolean;
}

export class ErrorBoundaryWrapper extends Component<Props, State> {
  constructor(props: Props) {
    super(props);
    this.state = { hasError: false };
  }

  static getDerivedStateFromError(): State {
    return { hasError: true };
  }

  componentDidCatch(error: Error, errorInfo: ErrorInfo) {
    console.error('Error caught by boundary:', error, errorInfo);
  }

  render() {
    if (this.state.hasError) {
      return (
        this.props.fallback ?? (
          <div className="flex h-64 items-center justify-center">
            <div className="text-center">
              <AlertTriangle className="mx-auto h-12 w-12 text-warning-500" />
              <p className="mt-4 text-surface-600">Something went wrong loading this section.</p>
              <Button
                variant="outline"
                size="sm"
                className="mt-4"
                onClick={() => this.setState({ hasError: false })}
              >
                Try Again
              </Button>
            </div>
          </div>
        )
      );
    }

    return this.props.children;
  }
}
