import { Link } from 'react-router-dom';

export default function NotFoundPage() {
  return (
    <div className="flex min-h-[60vh] flex-col items-center justify-center text-center">
      <h1 className="text-6xl font-bold text-surface-300">404</h1>
      <p className="mt-4 text-lg text-surface-600">Page not found</p>
      <p className="mt-2 text-sm text-surface-500">
        The page you are looking for does not exist or has been moved.
      </p>
      <Link
        to="/"
        className="mt-6 rounded-lg bg-brand-600 px-4 py-2 text-sm font-medium text-white hover:bg-brand-700"
      >
        Back to Dashboard
      </Link>
    </div>
  );
}
