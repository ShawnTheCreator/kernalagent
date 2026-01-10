import Link from 'next/link';

export function Footer() {
    return (
        <footer className="py-12 md:py-20 px-6 md:px-10 border-t border-zinc-900 bg-kernel-bg text-zinc-500">
            <div className="max-w-7xl mx-auto">
                <div className="grid md:grid-cols-4 gap-12 mb-12">
                    <div className="md:col-span-2">
                        <div className="flex items-center gap-3 mb-4">
                            <div className="w-6 h-6 border border-white flex items-center justify-center rotate-45">
                                <div className="w-2 h-2 bg-white"></div>
                            </div>
                            <span className="text-white font-bold tracking-tighter text-xl uppercase">Kernal</span>
                        </div>
                        <p className="text-sm text-zinc-500 max-w-sm">
                            A native cognitive agent that sees, understands, and executes across your operating system.
                        </p>
                        <div className="flex gap-4 mt-6" role="list" aria-label="Social media links">
                            <a href="#" className="w-10 h-10 rounded-full border border-zinc-800 flex items-center justify-center hover:border-white hover:text-white transition-colors" aria-label="Follow us on X (Twitter)">
                                <span className="text-xs font-bold" aria-hidden="true">X</span>
                            </a>
                            <a href="#" className="w-10 h-10 rounded-full border border-zinc-800 flex items-center justify-center hover:border-white hover:text-white transition-colors" aria-label="View our GitHub repository">
                                <span className="text-xs font-bold" aria-hidden="true">GH</span>
                            </a>
                            <a href="#" className="w-10 h-10 rounded-full border border-zinc-800 flex items-center justify-center hover:border-white hover:text-white transition-colors" aria-label="Join our Discord community">
                                <span className="text-xs font-bold" aria-hidden="true">DC</span>
                            </a>
                        </div>
                    </div>

                    <div>
                        <h4 className="text-white text-xs uppercase tracking-widest mb-4">Product</h4>
                        <ul className="space-y-3 text-sm">
                            <li><a href="#features" className="hover:text-white transition-colors">Features</a></li>
                            <li><a href="#demo" className="hover:text-white transition-colors">Demo</a></li>
                            <li><a href="#" className="hover:text-white transition-colors">Changelog</a></li>
                            <li><a href="#" className="hover:text-white transition-colors">Roadmap</a></li>
                        </ul>
                    </div>

                    <div>
                        <h4 className="text-white text-xs uppercase tracking-widest mb-4">Resources</h4>
                        <ul className="space-y-3 text-sm">
                            <li><a href="#" className="hover:text-white transition-colors">Documentation</a></li>
                            <li><a href="#" className="hover:text-white transition-colors">API Reference</a></li>
                            <li><a href="#" className="hover:text-white transition-colors">GitHub</a></li>
                            <li><a href="#" className="hover:text-white transition-colors">Discord</a></li>
                        </ul>
                    </div>
                </div>

                <div className="pt-8 border-t border-zinc-900 flex flex-col md:flex-row justify-between items-center gap-4 text-xs text-zinc-600">
                    <div>© 2025 Kernal Agent. All rights reserved.</div>
                    <div className="flex gap-6">
                        <Link href="#" className="hover:text-white transition-colors">Privacy</Link>
                        <Link href="#" className="hover:text-white transition-colors">Terms</Link>
                    </div>
                </div>

                <div className="mt-8 text-center text-[10px] text-zinc-700 tracking-widest">
                    Built with ❤️ and Gemini 3
                </div>
            </div>
        </footer>
    );
}
