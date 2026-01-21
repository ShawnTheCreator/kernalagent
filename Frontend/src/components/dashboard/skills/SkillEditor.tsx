'use client';

import { useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import {
    Plus, Trash2, GripVertical, Save, Play,
    Settings, Timer, Monitor, MousePointer,
    Keyboard, Globe, AppWindow, Type
} from 'lucide-react';
import { createSkill } from '@/lib/skillsApi';

interface ActionStep {
    id: string;
    type: string;
    label: string;
    target: string;
    content: string;
}

const ACTION_TYPES = [
    { value: 'open_app', label: 'Launch App', icon: AppWindow },
    { value: 'click', label: 'Click Element', icon: MousePointer },
    { value: 'type_text', label: 'Type Text', icon: Type },
    { value: 'hotkey', label: 'Keyboard Shortcut', icon: Keyboard },
    { value: 'navigate', label: 'Open URL', icon: Globe },
    { value: 'wait', label: 'Wait', icon: Timer },
];

const DEFAULT_ACTION: Omit<ActionStep, 'id'> = {
    type: 'open_app',
    label: 'New Action',
    target: '',
    content: '',
};

export function SkillEditor({ onSave, onCancel }: { onSave?: () => void; onCancel?: () => void }) {
    const [skillName, setSkillName] = useState('');
    const [description, setDescription] = useState('');
    const [actions, setActions] = useState<ActionStep[]>([]);
    const [selectedActionId, setSelectedActionId] = useState<string | null>(null);
    const [inputDelay, setInputDelay] = useState(500);
    const [waitForUI, setWaitForUI] = useState(true);
    const [failureStrategy, setFailureStrategy] = useState('retry');
    const [isSaving, setIsSaving] = useState(false);

    const selectedAction = actions.find(a => a.id === selectedActionId);

    const addAction = () => {
        const newAction: ActionStep = {
            ...DEFAULT_ACTION,
            id: `action_${Date.now()}`,
            label: `Action ${actions.length + 1}`,
        };
        setActions([...actions, newAction]);
        setSelectedActionId(newAction.id);
    };

    const removeAction = (id: string) => {
        setActions(actions.filter(a => a.id !== id));
        if (selectedActionId === id) {
            setSelectedActionId(null);
        }
    };

    const updateAction = (id: string, updates: Partial<ActionStep>) => {
        setActions(actions.map(a =>
            a.id === id ? { ...a, ...updates } : a
        ));
    };

    const handleSave = async () => {
        if (!skillName.trim() || actions.length === 0) return;

        setIsSaving(true);
        try {
            const steps = actions.map((action, index) => ({
                action: action.type,
                parameters: {
                    target: action.target,
                    content: action.content,
                },
                delay: inputDelay,
                order: index + 1,
            }));

            await createSkill({
                name: skillName,
                intent_signature: `skill:${skillName.toLowerCase().replace(/\s+/g, '_')}`,
                description: description || `Manual skill: ${skillName}`,
                steps,
            });

            // Reset form
            setSkillName('');
            setDescription('');
            setActions([]);
            setSelectedActionId(null);

            onSave?.();
        } catch (error) {
            console.error('Failed to save skill:', error);
        }
        setIsSaving(false);
    };

    const getActionIcon = (type: string) => {
        const actionType = ACTION_TYPES.find(t => t.value === type);
        return actionType?.icon || Settings;
    };

    return (
        <div className="bg-[#0a0a0a] border border-white/[0.05] rounded-xl overflow-hidden h-full flex flex-col">
            {/* Header */}
            <div className="px-4 py-3 border-b border-white/[0.05]">
                <h2 className="text-sm font-medium text-zinc-300">Skill Editor</h2>
                <p className="text-[10px] text-zinc-600 mt-0.5">Create skills manually with action sequences</p>
            </div>

            <div className="flex-1 flex overflow-hidden">
                {/* Left: Action Sequence */}
                <div className="flex-1 flex flex-col border-r border-white/[0.05]">
                    {/* Skill Name */}
                    <div className="p-4 border-b border-white/[0.05] space-y-3">
                        <input
                            type="text"
                            value={skillName}
                            onChange={(e) => setSkillName(e.target.value)}
                            placeholder="Skill name..."
                            className="w-full bg-white/[0.03] border border-white/[0.05] rounded-lg px-3 py-2 text-sm text-white placeholder:text-zinc-600 focus:outline-none focus:border-white/20"
                        />
                        <input
                            type="text"
                            value={description}
                            onChange={(e) => setDescription(e.target.value)}
                            placeholder="Description (optional)..."
                            className="w-full bg-white/[0.03] border border-white/[0.05] rounded-lg px-3 py-2 text-xs text-zinc-400 placeholder:text-zinc-600 focus:outline-none focus:border-white/20"
                        />
                    </div>

                    {/* Action Steps */}
                    <div className="flex-1 overflow-y-auto p-4 space-y-2">
                        <AnimatePresence>
                            {actions.map((action, index) => {
                                const Icon = getActionIcon(action.type);
                                return (
                                    <motion.div
                                        key={action.id}
                                        initial={{ opacity: 0, y: -10 }}
                                        animate={{ opacity: 1, y: 0 }}
                                        exit={{ opacity: 0, x: -20 }}
                                        onClick={() => setSelectedActionId(action.id)}
                                        className={`flex items-center gap-3 p-3 rounded-lg cursor-pointer transition-all ${selectedActionId === action.id
                                            ? 'bg-indigo-500/20 border border-indigo-500/50'
                                            : 'bg-white/[0.03] border border-white/[0.05] hover:border-white/10'
                                            }`}
                                    >
                                        <GripVertical size={14} className="text-zinc-600 cursor-grab" />
                                        <div className="w-6 h-6 rounded-md bg-indigo-500/20 flex items-center justify-center">
                                            <Icon size={12} className="text-indigo-400" />
                                        </div>
                                        <div className="flex-1 min-w-0">
                                            <span className="text-xs font-medium text-white">{index + 1}. {action.label}</span>
                                            <p className="text-[10px] text-zinc-500 truncate">
                                                {action.target || action.content || 'No target set'}
                                            </p>
                                        </div>
                                        <button
                                            onClick={(e) => { e.stopPropagation(); removeAction(action.id); }}
                                            className="p-1 rounded hover:bg-red-500/20 text-zinc-500 hover:text-red-400 transition-colors"
                                        >
                                            <Trash2 size={12} />
                                        </button>
                                    </motion.div>
                                );
                            })}
                        </AnimatePresence>

                        {actions.length === 0 && (
                            <div className="text-center py-8">
                                <p className="text-sm text-zinc-500">No actions yet</p>
                                <p className="text-xs text-zinc-600 mt-1">Add actions to build your skill</p>
                            </div>
                        )}
                    </div>

                    {/* Add Action Button */}
                    <div className="p-4 border-t border-white/[0.05]">
                        <button
                            onClick={addAction}
                            className="w-full flex items-center justify-center gap-2 py-2.5 bg-white/[0.03] hover:bg-white/[0.05] border border-white/[0.05] hover:border-white/10 rounded-lg text-sm text-zinc-400 hover:text-white transition-colors"
                        >
                            <Plus size={14} />
                            Add Action
                        </button>
                    </div>
                </div>

                {/* Right: Action Properties */}
                <div className="w-72 flex flex-col">
                    <div className="px-4 py-3 border-b border-white/[0.05]">
                        <h3 className="text-xs font-medium text-zinc-400 uppercase tracking-wider">Action Properties</h3>
                    </div>

                    {selectedAction ? (
                        <div className="flex-1 overflow-y-auto p-4 space-y-4">
                            {/* Action Label */}
                            <div>
                                <label className="text-[10px] uppercase tracking-wider text-zinc-600 mb-1.5 block">Action Label</label>
                                <input
                                    type="text"
                                    value={selectedAction.label}
                                    onChange={(e) => updateAction(selectedAction.id, { label: e.target.value })}
                                    className="w-full bg-white/[0.03] border border-white/[0.05] rounded-lg px-3 py-2 text-sm text-white focus:outline-none focus:border-white/20"
                                />
                            </div>

                            {/* Action Type */}
                            <div>
                                <label className="text-[10px] uppercase tracking-wider text-zinc-600 mb-1.5 block">Action Type</label>
                                <select
                                    value={selectedAction.type}
                                    onChange={(e) => updateAction(selectedAction.id, { type: e.target.value })}
                                    className="w-full bg-white/[0.03] border border-white/[0.05] rounded-lg px-3 py-2 text-sm text-white focus:outline-none focus:border-white/20 appearance-none cursor-pointer"
                                >
                                    {ACTION_TYPES.map(type => (
                                        <option key={type.value} value={type.value} className="bg-zinc-900">
                                            {type.label}
                                        </option>
                                    ))}
                                </select>
                            </div>

                            {/* Target */}
                            <div>
                                <label className="text-[10px] uppercase tracking-wider text-zinc-600 mb-1.5 block">Target</label>
                                <input
                                    type="text"
                                    value={selectedAction.target}
                                    onChange={(e) => updateAction(selectedAction.id, { target: e.target.value })}
                                    placeholder={selectedAction.type === 'open_app' ? 'notepad.exe' : 'Element name...'}
                                    className="w-full bg-white/[0.03] border border-white/[0.05] rounded-lg px-3 py-2 text-sm text-white placeholder:text-zinc-600 focus:outline-none focus:border-white/20"
                                />
                            </div>

                            {/* Content (for type_text) */}
                            {(selectedAction.type === 'type_text' || selectedAction.type === 'hotkey') && (
                                <div>
                                    <label className="text-[10px] uppercase tracking-wider text-zinc-600 mb-1.5 block">
                                        {selectedAction.type === 'hotkey' ? 'Keys' : 'Content'}
                                    </label>
                                    <input
                                        type="text"
                                        value={selectedAction.content}
                                        onChange={(e) => updateAction(selectedAction.id, { content: e.target.value })}
                                        placeholder={selectedAction.type === 'hotkey' ? 'ctrl+s' : 'Text to type...'}
                                        className="w-full bg-white/[0.03] border border-white/[0.05] rounded-lg px-3 py-2 text-sm text-white placeholder:text-zinc-600 focus:outline-none focus:border-white/20"
                                    />
                                </div>
                            )}

                            <hr className="border-white/[0.05]" />

                            {/* Input Delay */}
                            <div>
                                <label className="text-[10px] uppercase tracking-wider text-zinc-600 mb-1.5 block">Input Delay (ms)</label>
                                <input
                                    type="number"
                                    value={inputDelay}
                                    onChange={(e) => setInputDelay(parseInt(e.target.value) || 0)}
                                    min={0}
                                    max={10000}
                                    step={100}
                                    className="w-full bg-white/[0.03] border border-white/[0.05] rounded-lg px-3 py-2 text-sm text-white focus:outline-none focus:border-white/20"
                                />
                            </div>

                            {/* Wait for UI */}
                            <div className="flex items-center justify-between">
                                <label className="text-[10px] uppercase tracking-wider text-zinc-600">Wait for UI Stability</label>
                                <button
                                    onClick={() => setWaitForUI(!waitForUI)}
                                    className={`relative w-10 h-5 rounded-full transition-colors ${waitForUI ? 'bg-indigo-500' : 'bg-zinc-700'}`}
                                >
                                    <span className={`absolute top-0.5 left-0.5 w-4 h-4 rounded-full bg-white transition-transform ${waitForUI ? 'translate-x-5' : ''}`} />
                                </button>
                            </div>

                            {/* Failure Strategy */}
                            <div>
                                <label className="text-[10px] uppercase tracking-wider text-zinc-600 mb-1.5 block">On Failure Strategy</label>
                                <select
                                    value={failureStrategy}
                                    onChange={(e) => setFailureStrategy(e.target.value)}
                                    className="w-full bg-white/[0.03] border border-white/[0.05] rounded-lg px-3 py-2 text-sm text-white focus:outline-none focus:border-white/20 appearance-none cursor-pointer"
                                >
                                    <option value="retry" className="bg-zinc-900">Retry 3 Times</option>
                                    <option value="skip" className="bg-zinc-900">Skip Action</option>
                                    <option value="stop" className="bg-zinc-900">Stop Skill</option>
                                </select>
                            </div>
                        </div>
                    ) : (
                        <div className="flex-1 flex items-center justify-center">
                            <p className="text-xs text-zinc-600">Select an action to edit</p>
                        </div>
                    )}

                    {/* Save Button */}
                    <div className="p-4 border-t border-white/[0.05] space-y-2">
                        <button
                            onClick={handleSave}
                            disabled={!skillName.trim() || actions.length === 0 || isSaving}
                            className="w-full flex items-center justify-center gap-2 py-2.5 bg-indigo-500 hover:bg-indigo-600 disabled:bg-zinc-700 disabled:text-zinc-500 rounded-lg text-sm text-white font-medium transition-colors"
                        >
                            <Save size={14} />
                            {isSaving ? 'Saving...' : 'Save Skill'}
                        </button>
                        {onCancel && (
                            <button
                                onClick={onCancel}
                                className="w-full py-2 text-sm text-zinc-500 hover:text-white transition-colors"
                            >
                                Cancel
                            </button>
                        )}
                    </div>
                </div>
            </div>
        </div>
    );
}
