import { useState } from 'react';
import { Link } from 'react-router-dom';
import { Mail, Lock, User, Building2 } from 'lucide-react';
import { Button } from '@/components/ui/Button';
import { Input } from '@/components/ui/Input';
import { useAuth } from '@/hooks/useAuth';
import { registerSchema } from '@/lib/validators';

export default function RegisterPage() {
  const { register, isLoading } = useAuth();
  const [form, setForm] = useState({
    name: '',
    email: '',
    organizationName: '',
    password: '',
    confirmPassword: '',
  });
  const [errors, setErrors] = useState<Record<string, string>>({});

  const updateField = (field: string, value: string) => {
    setForm((prev) => ({ ...prev, [field]: value }));
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setErrors({});

    const result = registerSchema.safeParse(form);
    if (!result.success) {
      const fieldErrors: Record<string, string> = {};
      result.error.issues.forEach((issue) => {
        const field = issue.path[0];
        if (typeof field === 'string') {
          fieldErrors[field] = issue.message;
        }
      });
      setErrors(fieldErrors);
      return;
    }

    try {
      await register(form.name, form.email, form.password, form.organizationName);
    } catch {
      // Error handled in useAuth
    }
  };

  return (
    <div>
      <h2 className="text-2xl font-bold text-surface-900">Create your account</h2>
      <p className="mt-2 text-surface-500">Get started with AutonoCX for your team</p>

      <form onSubmit={handleSubmit} className="mt-8 space-y-4">
        <Input
          label="Full name"
          type="text"
          placeholder="John Smith"
          value={form.name}
          onChange={(e) => updateField('name', e.target.value)}
          error={errors.name}
          leftIcon={<User className="h-4 w-4" />}
          autoComplete="name"
        />

        <Input
          label="Email address"
          type="email"
          placeholder="you@company.com"
          value={form.email}
          onChange={(e) => updateField('email', e.target.value)}
          error={errors.email}
          leftIcon={<Mail className="h-4 w-4" />}
          autoComplete="email"
        />

        <Input
          label="Organization name"
          type="text"
          placeholder="Acme Corp"
          value={form.organizationName}
          onChange={(e) => updateField('organizationName', e.target.value)}
          error={errors.organizationName}
          leftIcon={<Building2 className="h-4 w-4" />}
        />

        <Input
          label="Password"
          type="password"
          placeholder="At least 8 characters"
          value={form.password}
          onChange={(e) => updateField('password', e.target.value)}
          error={errors.password}
          leftIcon={<Lock className="h-4 w-4" />}
          autoComplete="new-password"
        />

        <Input
          label="Confirm password"
          type="password"
          placeholder="Repeat your password"
          value={form.confirmPassword}
          onChange={(e) => updateField('confirmPassword', e.target.value)}
          error={errors.confirmPassword}
          leftIcon={<Lock className="h-4 w-4" />}
          autoComplete="new-password"
        />

        <Button type="submit" className="w-full" size="lg" isLoading={isLoading}>
          Create account
        </Button>
      </form>

      <p className="mt-6 text-center text-sm text-surface-500">
        Already have an account?{' '}
        <Link to="/login" className="font-medium text-brand-600 hover:text-brand-700">
          Sign in
        </Link>
      </p>
    </div>
  );
}
