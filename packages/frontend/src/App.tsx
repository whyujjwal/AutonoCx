import { Outlet } from 'react-router-dom';
import { Toast } from '@/components/ui/Toast';

export default function App() {
  return (
    <>
      <Outlet />
      <Toast />
    </>
  );
}
