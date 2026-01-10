import { Navbar, Footer } from "@/components/layout";
import { CursorGlow, LogoWall, NeuralNetwork3D } from "@/components/effects";
import { Hero, BentoFeatures, StatsSection, TechSection, CTA } from "@/components/sections";
import { InteractiveTerminal } from "@/components/ui";
import { Eye, Zap, Monitor } from "lucide-react";

export default function Home() {
  return (
    <div className="min-h-screen noise-overlay">
      {/* 3D Neural Network Background */}
      <NeuralNetwork3D />

      <CursorGlow />
      <Navbar />
      <main>
        <Hero />
        <LogoWall />

        {/* Interactive Demo Section */}
        <section id="demo" className="py-24 md:py-40 px-6">
          <div className="max-w-6xl mx-auto">
            <div className="grid lg:grid-cols-2 gap-12 items-start">
              {/* Interactive Terminal */}
              <InteractiveTerminal />

              {/* Demo Description */}
              <div className="space-y-8">
                <h3 className="text-3xl md:text-4xl font-bold tracking-tight">Intelligent Desktop Automation</h3>
                <p className="text-zinc-400 leading-relaxed">
                  Kernal Agent uses Gemini 3&apos;s multimodal capabilities to understand exactly what you want,
                  analyze your screen in real-time, and execute actions with pixel-perfect precision.
                </p>
                <p className="text-sm text-zinc-500">
                  👆 Try typing commands in the terminal! (e.g., &quot;open spotify&quot;, &quot;help&quot;)
                </p>
                <div className="space-y-4">
                  {[
                    { icon: <Eye size={20} />, title: 'Visual Understanding', desc: 'Sees and understands any UI, legacy or modern' },
                    { icon: <Zap size={20} />, title: 'Instant Execution', desc: 'Sub-400ms response time for seamless automation' },
                    { icon: <Monitor size={20} />, title: 'System-Wide Access', desc: 'Works across all applications, not just browsers' },
                  ].map((item, i) => (
                    <div key={i} className="flex items-start gap-4 p-4 rounded-xl bg-white/[0.02] border border-white/5 hover:border-white/30 transition-colors touch-feedback">
                      <div className="text-white">{item.icon}</div>
                      <div>
                        <div className="font-medium text-white">{item.title}</div>
                        <div className="text-sm text-zinc-500">{item.desc}</div>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            </div>
          </div>
        </section>

        <BentoFeatures />
        <StatsSection />
        <TechSection />
        <CTA />
      </main>
      <Footer />
    </div>
  );
}
