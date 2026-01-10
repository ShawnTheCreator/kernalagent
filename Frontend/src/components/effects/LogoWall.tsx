'use client';

export function LogoWall() {
    const logos = ['NVIDIA', 'Microsoft', 'OpenAI', 'Anthropic', 'Google', 'Meta', 'NVIDIA', 'Microsoft', 'OpenAI', 'Anthropic', 'Google', 'Meta'];

    return (
        <section className="py-12 border-y border-zinc-900 overflow-hidden bg-zinc-950/50">
            <div className="text-center mb-8">
                <p className="text-[10px] uppercase tracking-[0.3em] text-zinc-600">Built with technologies from</p>
            </div>
            <div className="relative">
                <div className="logo-wall">
                    {logos.map((logo, i) => (
                        <div key={i} className="logo-item flex items-center justify-center min-w-[120px]">
                            <span className="text-lg font-bold tracking-tight text-white">{logo}</span>
                        </div>
                    ))}
                </div>
            </div>
        </section>
    );
}
