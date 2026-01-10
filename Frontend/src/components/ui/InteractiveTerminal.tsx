'use client';

import { useState, useEffect, useRef, KeyboardEvent } from 'react';
import { ChevronRight, Sparkles, Check, Loader2 } from 'lucide-react';

interface Command {
    input: string;
    output: string;
    status: 'success' | 'processing' | 'error';
}

const COMMANDS: Record<string, string> = {
    'help': 'Available commands:\n  open <app>  - Open an application\n  search <query>  - Search the web\n  summarize  - Summarize active document\n  screenshot  - Capture screen\n  email <text>  - Draft an email',
    'open chrome': '✓ Opening Google Chrome...\n✓ Chrome launched successfully',
    'open spotify': '✓ Opening Spotify...\n✓ Playing your Discover Weekly playlist',
    'open notepad': '✓ Opening Notepad...\n✓ New document created',
    'search weather': '✓ Opening Chrome...\n✓ Searching for "weather"\n✓ Results displayed',
    'summarize': '✓ Analyzing active document...\n✓ Generated summary:\n  "Meeting notes from project review discussing Q2 milestones and budget allocations."',
    'screenshot': '✓ Capturing screen...\n✓ Screenshot saved to Desktop/screenshot_001.png',
    'email team': '✓ Opening email client...\n✓ New draft created\n✓ Recipients: team@company.com',
};

export function InteractiveTerminal() {
    const [history, setHistory] = useState<Command[]>([]);
    const [input, setInput] = useState('');
    const [isProcessing, setIsProcessing] = useState(false);
    const [historyIndex, setHistoryIndex] = useState(-1);
    const inputRef = useRef<HTMLInputElement>(null);
    const contentRef = useRef<HTMLDivElement>(null);

    const processCommand = async (cmd: string) => {
        if (!cmd.trim()) return;

        setIsProcessing(true);
        const newCommand: Command = { input: cmd, output: '', status: 'processing' };
        setHistory(prev => [...prev, newCommand]);
        setInput('');
        setHistoryIndex(-1);

        // Simulate processing delay
        await new Promise(resolve => setTimeout(resolve, 500));

        // Find matching command
        const lowerCmd = cmd.toLowerCase().trim();
        let output = COMMANDS[lowerCmd];

        if (!output) {
            // Try partial matches
            const key = Object.keys(COMMANDS).find(k => lowerCmd.startsWith(k.split(' ')[0]));
            if (key) {
                output = COMMANDS[key];
            } else {
                output = `Command not recognized: "${cmd}"\nType "help" for available commands.`;
            }
        }

        // Type out the response
        setHistory(prev => {
            const updated = [...prev];
            updated[updated.length - 1] = { input: cmd, output, status: 'success' };
            return updated;
        });
        setIsProcessing(false);
    };

    const handleKeyDown = (e: KeyboardEvent<HTMLInputElement>) => {
        if (e.key === 'Enter') {
            processCommand(input);
        } else if (e.key === 'ArrowUp') {
            e.preventDefault();
            const commands = history.map(h => h.input);
            if (commands.length > 0) {
                const newIndex = historyIndex < commands.length - 1 ? historyIndex + 1 : historyIndex;
                setHistoryIndex(newIndex);
                setInput(commands[commands.length - 1 - newIndex] || '');
            }
        } else if (e.key === 'ArrowDown') {
            e.preventDefault();
            if (historyIndex > 0) {
                const newIndex = historyIndex - 1;
                setHistoryIndex(newIndex);
                const commands = history.map(h => h.input);
                setInput(commands[commands.length - 1 - newIndex] || '');
            } else {
                setHistoryIndex(-1);
                setInput('');
            }
        }
    };

    useEffect(() => {
        if (contentRef.current) {
            contentRef.current.scrollTop = contentRef.current.scrollHeight;
        }
    }, [history]);

    return (
        <div className="bg-[#0A0A0A] border border-white/10 rounded-xl overflow-hidden">
            {/* Title Bar */}
            <div className="flex items-center px-4 py-3 bg-white/[0.02] border-b border-white/5">
                <div className="flex gap-2">
                    <div className="w-3 h-3 rounded-full bg-[#FF5F57]"></div>
                    <div className="w-3 h-3 rounded-full bg-[#FEBC2E]"></div>
                    <div className="w-3 h-3 rounded-full bg-[#28C840]"></div>
                </div>
                <span className="ml-4 text-xs text-zinc-500 font-mono">kernal-agent.exe — Interactive Mode</span>
            </div>

            {/* Content */}
            <div
                ref={contentRef}
                className="p-4 h-[300px] overflow-y-auto font-mono text-sm"
                onClick={() => inputRef.current?.focus()}
            >
                {/* Welcome Message */}
                <div className="mb-4 text-zinc-400">
                    <div className="flex items-center gap-2 text-white mb-1">
                        <Sparkles size={14} />
                        <span>Kernal Agent v0.1.2-alpha</span>
                    </div>
                    <div className="text-xs text-zinc-600">Type commands to interact. Try &quot;open spotify&quot; or &quot;help&quot;</div>
                </div>

                {/* Command History */}
                {history.map((cmd, i) => (
                    <div key={i} className="mb-3">
                        <div className="flex items-center gap-2 text-white">
                            <ChevronRight size={12} className="text-zinc-600" />
                            <span>{cmd.input}</span>
                        </div>
                        <div className="ml-4 mt-1 text-zinc-400 whitespace-pre-wrap">
                            {cmd.status === 'processing' ? (
                                <span className="flex items-center gap-2">
                                    <Loader2 size={12} className="animate-spin" />
                                    Processing...
                                </span>
                            ) : (
                                cmd.output
                            )}
                        </div>
                    </div>
                ))}

                {/* Input Line */}
                <div className="flex items-center gap-2">
                    <ChevronRight size={12} className="text-zinc-600" />
                    <input
                        ref={inputRef}
                        type="text"
                        value={input}
                        onChange={(e) => setInput(e.target.value)}
                        onKeyDown={handleKeyDown}
                        disabled={isProcessing}
                        placeholder="Type a command..."
                        className="flex-1 bg-transparent text-white outline-none placeholder:text-zinc-700"
                    />
                    {isProcessing && <Loader2 size={14} className="animate-spin text-zinc-500" />}
                </div>
            </div>
        </div>
    );
}
