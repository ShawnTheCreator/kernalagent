'use client';

// Simple SVG logo components
const logos = [
    {
        name: 'NVIDIA',
        svg: (
            <svg viewBox="0 0 351 80" className="h-6 w-auto" fill="currentColor">
                <path d="M0 40C0 17.909 17.909 0 40 0h271c22.091 0 40 17.909 40 40s-17.909 40-40 40H40C17.909 80 0 62.091 0 40z" fillOpacity="0" />
                <text x="175" y="52" textAnchor="middle" fontSize="40" fontWeight="bold" fill="currentColor">NVIDIA</text>
            </svg>
        )
    },
    {
        name: 'Microsoft',
        svg: (
            <svg viewBox="0 0 23 23" className="h-5 w-5" fill="currentColor">
                <path d="M0 0h11v11H0zM12 0h11v11H12zM0 12h11v11H0zM12 12h11v11H12z" />
            </svg>
        )
    },
    {
        name: 'OpenAI',
        svg: (
            <svg viewBox="0 0 24 24" className="h-5 w-5" fill="currentColor">
                <path d="M22.282 9.821a5.985 5.985 0 0 0-.516-4.91 6.046 6.046 0 0 0-6.51-2.9A6.065 6.065 0 0 0 4.981 4.18a5.985 5.985 0 0 0-3.998 2.9 6.046 6.046 0 0 0 .743 7.097 5.98 5.98 0 0 0 .51 4.911 6.051 6.051 0 0 0 6.515 2.9A5.985 5.985 0 0 0 13.26 24a6.056 6.056 0 0 0 5.772-4.206 5.99 5.99 0 0 0 3.997-2.9 6.056 6.056 0 0 0-.747-7.073zM13.26 22.43a4.476 4.476 0 0 1-2.876-1.04l.141-.081 4.779-2.758a.795.795 0 0 0 .392-.681v-6.737l2.02 1.168a.071.071 0 0 1 .038.052v5.583a4.504 4.504 0 0 1-4.494 4.494zM3.6 18.304a4.47 4.47 0 0 1-.535-3.014l.142.085 4.783 2.759a.771.771 0 0 0 .78 0l5.843-3.369v2.332a.08.08 0 0 1-.033.062L9.74 19.95a4.5 4.5 0 0 1-6.14-1.646zM2.34 7.896a4.485 4.485 0 0 1 2.366-1.973V11.6a.766.766 0 0 0 .388.676l5.815 3.355-2.02 1.168a.076.076 0 0 1-.071 0l-4.83-2.786A4.504 4.504 0 0 1 2.34 7.896zm16.597 3.855l-5.833-3.387L15.119 7.2a.076.076 0 0 1 .071 0l4.83 2.791a4.494 4.494 0 0 1-.676 8.105v-5.678a.79.79 0 0 0-.407-.667zm2.01-3.023l-.141-.085-4.774-2.782a.776.776 0 0 0-.785 0L9.409 9.23V6.897a.066.066 0 0 1 .028-.061l4.83-2.787a4.5 4.5 0 0 1 6.68 4.66zm-12.64 4.135l-2.02-1.164a.08.08 0 0 1-.038-.057V6.075a4.5 4.5 0 0 1 7.375-3.453l-.142.08L8.704 5.46a.795.795 0 0 0-.393.681zm1.097-2.365l2.602-1.5 2.607 1.5v2.999l-2.597 1.5-2.607-1.5z" />
            </svg>
        )
    },
    {
        name: 'Anthropic',
        svg: (
            <svg viewBox="0 0 24 24" className="h-5 w-5" fill="currentColor">
                <path d="M17.304 3.541l-5.296 16.918H7.921L13.217 3.54h4.087zm-10.608 0L12 20.459h-4.08L2.616 3.541h4.08z" />
            </svg>
        )
    },
    {
        name: 'Google',
        svg: (
            <svg viewBox="0 0 24 24" className="h-5 w-5" fill="currentColor">
                <path d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z" />
                <path d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z" />
                <path d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z" />
                <path d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z" />
            </svg>
        )
    },
    {
        name: 'Meta',
        svg: (
            <svg viewBox="0 0 24 24" className="h-5 w-5" fill="currentColor">
                <path d="M12.04 7.08c1.56 0 3.06.79 4.47 2.47.88 1.05 1.67 2.39 2.27 3.63.52 1.08.92 2.13 1.13 2.93.25.94.22 1.55-.15 1.87-.26.22-.65.26-1.05.1-.58-.23-1.32-.83-2.12-1.75-1.02-1.16-2.12-2.78-3.1-4.52a25.9 25.9 0 0 1-1.45-2.95c-.28-.69-.48-1.29-.48-1.62 0-.16.15-.16.48-.16zm-8.08 0c.33 0 .48 0 .48.16 0 .33-.2.93-.48 1.62a25.9 25.9 0 0 1-1.45 2.95c-.98 1.74-2.08 3.36-3.1 4.52-.8.92-1.54 1.52-2.12 1.75-.4.16-.79.12-1.05-.1-.37-.32-.4-.93-.15-1.87.21-.8.61-1.85 1.13-2.93.6-1.24 1.39-2.58 2.27-3.63 1.41-1.68 2.91-2.47 4.47-2.47z" />
            </svg>
        )
    },
];

export function LogoWall() {
    // Double the logos for seamless infinite scroll
    const doubledLogos = [...logos, ...logos];

    return (
        <section className="py-12 border-y border-zinc-900 overflow-hidden bg-zinc-950/50">
            <div className="text-center mb-8">
                <p className="text-[10px] uppercase tracking-[0.3em] text-zinc-600">Built with technologies from</p>
            </div>
            <div className="relative logo-wall-track">
                <div className="logo-wall-content">
                    {doubledLogos.map((logo, i) => (
                        <div
                            key={`${logo.name}-${i}`}
                            className="logo-item flex items-center justify-center gap-2 min-w-[140px] text-zinc-500 hover:text-white transition-colors duration-300"
                            aria-label={logo.name}
                        >
                            {logo.svg}
                            <span className="text-sm font-medium tracking-tight">{logo.name}</span>
                        </div>
                    ))}
                </div>
            </div>
        </section>
    );
}

