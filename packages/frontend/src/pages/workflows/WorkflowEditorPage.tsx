import { useState } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { ArrowLeft, Save, Plus, Trash2, GripVertical } from 'lucide-react';
import { Button } from '@/components/ui/Button';
import { Input } from '@/components/ui/Input';
import { Select } from '@/components/ui/Select';
import { Card, CardHeader, CardTitle } from '@/components/ui/Card';
import { Badge } from '@/components/ui/Badge';

interface WorkflowStep {
  id: string;
  type: string;
  name: string;
  config: Record<string, string>;
}

export default function WorkflowEditorPage() {
  const { id } = useParams();
  const navigate = useNavigate();
  const isNew = !id;

  const [name, setName] = useState(isNew ? '' : 'Refund Processing');
  const [description, setDescription] = useState(isNew ? '' : 'Automates refund requests with approval workflow.');
  const [triggerType, setTriggerType] = useState(isNew ? '' : 'action_request');

  const [steps, setSteps] = useState<WorkflowStep[]>(
    isNew
      ? []
      : [
          { id: '1', type: 'condition', name: 'Check refund amount', config: { field: 'amount', operator: 'gt', value: '100' } },
          { id: '2', type: 'human_review', name: 'Manager approval', config: { assignTo: 'manager' } },
          { id: '3', type: 'action', name: 'Process refund', config: { tool: 'process_refund' } },
          { id: '4', type: 'action', name: 'Send confirmation', config: { tool: 'send_email' } },
        ],
  );

  const addStep = () => {
    setSteps([
      ...steps,
      {
        id: `step-${Date.now()}`,
        type: 'action',
        name: 'New Step',
        config: {},
      },
    ]);
  };

  const removeStep = (stepId: string) => {
    setSteps(steps.filter((s) => s.id !== stepId));
  };

  const updateStep = (stepId: string, field: keyof WorkflowStep, value: string) => {
    setSteps(steps.map((s) => (s.id === stepId ? { ...s, [field]: value } : s)));
  };

  const stepTypeColors: Record<string, string> = {
    condition: 'bg-amber-50 text-amber-700',
    action: 'bg-brand-50 text-brand-700',
    llm_call: 'bg-violet-50 text-violet-700',
    tool_call: 'bg-cyan-50 text-cyan-700',
    human_review: 'bg-rose-50 text-rose-700',
    delay: 'bg-surface-100 text-surface-600',
  };

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <button
            onClick={() => navigate('/workflows')}
            className="rounded-lg p-1.5 text-surface-400 hover:bg-surface-100"
          >
            <ArrowLeft className="h-5 w-5" />
          </button>
          <div>
            <h1 className="text-2xl font-bold text-surface-900">
              {isNew ? 'Create Workflow' : 'Edit Workflow'}
            </h1>
            <p className="mt-1 text-surface-500">
              {isNew ? 'Design an automated workflow' : `Editing ${name}`}
            </p>
          </div>
        </div>
        <div className="flex gap-2">
          <Button variant="outline" onClick={() => navigate('/workflows')}>Cancel</Button>
          <Button leftIcon={<Save className="h-4 w-4" />}>
            {isNew ? 'Create' : 'Save'}
          </Button>
        </div>
      </div>

      <div className="grid grid-cols-1 gap-6 lg:grid-cols-3">
        <div className="lg:col-span-2 space-y-6">
          <Card padding="md">
            <CardHeader>
              <CardTitle>Workflow Details</CardTitle>
            </CardHeader>
            <div className="space-y-4">
              <Input label="Name" value={name} onChange={(e) => setName(e.target.value)} placeholder="Workflow name" />
              <div>
                <label className="mb-1.5 block text-sm font-medium text-surface-700">Description</label>
                <textarea
                  value={description}
                  onChange={(e) => setDescription(e.target.value)}
                  rows={2}
                  className="w-full rounded-lg border border-surface-300 px-3 py-2 text-sm focus:border-brand-500 focus:outline-none focus:ring-2 focus:ring-brand-500/20"
                  placeholder="Describe what this workflow does"
                />
              </div>
              <Select
                label="Trigger"
                value={triggerType}
                onChange={(e) => setTriggerType(e.target.value)}
                options={[
                  { value: 'action_request', label: 'Action Request' },
                  { value: 'conversation_created', label: 'Conversation Created' },
                  { value: 'conversation_escalated', label: 'Conversation Escalated' },
                  { value: 'conversation_resolved', label: 'Conversation Resolved' },
                  { value: 'customer_created', label: 'Customer Created' },
                  { value: 'schedule', label: 'Scheduled' },
                ]}
                placeholder="Select trigger"
              />
            </div>
          </Card>

          {/* Steps */}
          <Card padding="md">
            <CardHeader>
              <CardTitle>Steps</CardTitle>
            </CardHeader>
            <div className="space-y-3">
              {steps.map((step, index) => (
                <div
                  key={step.id}
                  className="flex items-start gap-3 rounded-lg border border-surface-200 p-4"
                >
                  <div className="mt-1 cursor-grab text-surface-300">
                    <GripVertical className="h-4 w-4" />
                  </div>
                  <div className="flex h-6 w-6 items-center justify-center rounded-full bg-surface-100 text-xs font-semibold text-surface-600 shrink-0">
                    {index + 1}
                  </div>
                  <div className="flex-1 space-y-3">
                    <div className="flex items-center gap-2">
                      <Input
                        value={step.name}
                        onChange={(e) => updateStep(step.id, 'name', e.target.value)}
                        className="flex-1"
                      />
                      <Badge className={stepTypeColors[step.type] ?? stepTypeColors.action} size="md">
                        {step.type}
                      </Badge>
                    </div>
                    <Select
                      value={step.type}
                      onChange={(e) => updateStep(step.id, 'type', e.target.value)}
                      options={[
                        { value: 'condition', label: 'Condition' },
                        { value: 'action', label: 'Action' },
                        { value: 'llm_call', label: 'LLM Call' },
                        { value: 'tool_call', label: 'Tool Call' },
                        { value: 'human_review', label: 'Human Review' },
                        { value: 'delay', label: 'Delay' },
                      ]}
                    />
                  </div>
                  <button
                    onClick={() => removeStep(step.id)}
                    className="mt-1 rounded p-1 text-surface-400 hover:text-danger-500"
                  >
                    <Trash2 className="h-4 w-4" />
                  </button>
                </div>
              ))}
              <Button variant="outline" className="w-full" leftIcon={<Plus className="h-4 w-4" />} onClick={addStep}>
                Add Step
              </Button>
            </div>
          </Card>
        </div>

        <div className="space-y-6">
          <Card padding="md">
            <CardHeader>
              <CardTitle>Summary</CardTitle>
            </CardHeader>
            <div className="space-y-3 text-sm">
              <div className="flex justify-between">
                <span className="text-surface-500">Steps</span>
                <span className="font-medium text-surface-700">{steps.length}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-surface-500">Trigger</span>
                <span className="font-medium text-surface-700">{triggerType || 'Not set'}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-surface-500">Status</span>
                <Badge variant="warning" size="sm">draft</Badge>
              </div>
            </div>
          </Card>
        </div>
      </div>
    </div>
  );
}
