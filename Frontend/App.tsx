
import React, { useEffect, useState, useRef, useCallback } from 'react';
import {
  Download,
  Cpu,
  Eye,
  EyeOff,
  Layers,
  Command,
  CircleDot,
  Monitor,
  Zap,
  MousePointer,
  Sparkles,
  Terminal,
  Play,
  ArrowRight,
  ArrowLeft,
  Quote,
  Menu,
  X,
  Star,
  Users,
  Clock,
  Check,
  Mail,
  Lock,
  User,
  Github
} from 'lucide-react';

// ==================== HOOKS ====================

const useScrollProgress = (ref: React.RefObject<HTMLElement | null>) => {
  const [progress, setProgress] = useState(0);

  useEffect(() => {
    const handleScroll = () => {
      if (!ref.current) return;
      const rect = ref.current.getBoundingClientRect();
      const viewportHeight = window.innerHeight;
      const scrollStart = viewportHeight;
      const scrollEnd = -rect.height;
      const current = rect.top;
      const p = (current - scrollStart) / (scrollEnd - scrollStart);
      setProgress(Math.max(0, Math.min(1, p)));
    };

    window.addEventListener('scroll', handleScroll, { passive: true });
    handleScroll();
    return () => window.removeEventListener('scroll', handleScroll);
  }, [ref]);

  return progress;
};

const useMousePosition = () => {
  const [position, setPosition] = useState({ x: 0, y: 0 });

  useEffect(() => {
    const handleMouseMove = (e: MouseEvent) => {
      setPosition({ x: e.clientX, y: e.clientY });
    };
    window.addEventListener('mousemove', handleMouseMove);
    return () => window.removeEventListener('mousemove', handleMouseMove);
  }, []);

  return position;
};

const useCountUp = (end: number, duration: number = 2000, start: boolean = false) => {
  const [count, setCount] = useState(0);

  useEffect(() => {
    if (!start) return;
    let startTime: number;
    const animate = (timestamp: number) => {
      if (!startTime) startTime = timestamp;
      const progress = Math.min((timestamp - startTime) / duration, 1);
      setCount(Math.floor(progress * end));
      if (progress < 1) requestAnimationFrame(animate);
    };
    requestAnimationFrame(animate);
  }, [end, duration, start]);

  return count;
};

// ==================== CURSOR GLOW ====================

const CursorGlow = () => {
  const { x, y } = useMousePosition();

  return (
    <div
      className="cursor-glow hidden lg:block"
      style={{ left: x, top: y }}
    />
  );
};

// ==================== NAVBAR ====================

const Navbar = () => {
  const [scrolled, setScrolled] = useState(false);
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);

  useEffect(() => {
    const handleScroll = () => setScrolled(window.scrollY > 50);
    window.addEventListener('scroll', handleScroll);
    return () => window.removeEventListener('scroll', handleScroll);
  }, []);

  return (
    <>
      <nav className={`fixed top-0 left-0 right-0 z-50 flex items-center justify-between px-4 md:px-10 py-4 md:py-6 transition-all duration-500 ${scrolled ? 'bg-kernel-bg/80 backdrop-blur-xl border-b border-white/5' : ''}`}>
        <div className="flex items-center space-x-2 md:space-x-3 w-1/4">
          <div className="w-5 h-5 md:w-6 md:h-6 border border-white flex items-center justify-center rotate-45">
            <div className="w-1.5 h-1.5 md:w-2 md:h-2 bg-white"></div>
          </div>
          <span className="font-bold tracking-tighter text-lg md:text-xl uppercase text-white">Kernal</span>
        </div>

        <div className="hidden lg:flex flex-1 justify-center items-center space-x-12 text-[10px] uppercase tracking-[0.3em] font-medium text-white/60">
          <a href="#features" className="hover:text-white transition-colors">Features</a>
          <a href="#demo" className="hover:text-white transition-colors">Demo</a>
          <a href="#tech" className="hover:text-white transition-colors">Architecture</a>
        </div>

        <div className="flex justify-end w-1/4 items-center gap-4">
          <a href="#login" className="hidden md:block text-[10px] uppercase tracking-widest text-zinc-400 hover:text-white transition-colors">
            Sign In
          </a>
          <a href="#signup" className="hidden md:block text-[9px] md:text-[10px] uppercase tracking-widest border border-white/20 px-4 md:px-6 py-2 rounded-full hover:bg-white hover:text-black transition-all duration-500 text-white whitespace-nowrap magnetic-btn">
            Get Started
          </a>
          <button
            className="lg:hidden text-white p-2"
            onClick={() => setMobileMenuOpen(true)}
          >
            <Menu size={24} />
          </button>
        </div>
      </nav>

      {/* Mobile Menu */}
      <div className={`mobile-menu-overlay ${mobileMenuOpen ? 'open' : ''}`} onClick={() => setMobileMenuOpen(false)} />
      <div className={`mobile-menu ${mobileMenuOpen ? 'open' : ''}`}>
        <button
          className="absolute top-6 right-6 text-white"
          onClick={() => setMobileMenuOpen(false)}
        >
          <X size={24} />
        </button>
        <div className="flex flex-col space-y-8 text-xl uppercase tracking-widest">
          <a href="#features" className="text-white/60 hover:text-white transition-colors" onClick={() => setMobileMenuOpen(false)}>Features</a>
          <a href="#demo" className="text-white/60 hover:text-white transition-colors" onClick={() => setMobileMenuOpen(false)}>Demo</a>
          <a href="#tech" className="text-white/60 hover:text-white transition-colors" onClick={() => setMobileMenuOpen(false)}>Architecture</a>
          <div className="pt-8 border-t border-white/10 space-y-4">
            <a href="#login" className="block text-sm text-white/60 hover:text-white transition-colors" onClick={() => setMobileMenuOpen(false)}>Sign In</a>
            <a href="#signup" className="block text-sm uppercase tracking-widest border border-white/20 px-6 py-3 rounded-full hover:bg-white hover:text-black transition-all duration-500 text-white text-center" onClick={() => setMobileMenuOpen(false)}>
              Get Started
            </a>
          </div>
        </div>
      </div>
    </>
  );
};

// ==================== HERO ====================

const Hero = () => {
  const [scrollY, setScrollY] = useState(0);
  const containerRef = useRef<HTMLElement>(null);
  const progress = useScrollProgress(containerRef);
  const [typedText, setTypedText] = useState('');
  const fullText = 'Synthesized.';
  const { x, y } = useMousePosition();

  useEffect(() => {
    const handleScroll = () => setScrollY(window.pageYOffset);
    window.addEventListener('scroll', handleScroll, { passive: true });
    return () => window.removeEventListener('scroll', handleScroll);
  }, []);

  useEffect(() => {
    let i = 0;
    const timer = setInterval(() => {
      if (i <= fullText.length) {
        setTypedText(fullText.slice(0, i));
        i++;
      } else {
        clearInterval(timer);
      }
    }, 100);
    return () => clearInterval(timer);
  }, []);

  return (
    <section ref={containerRef} className="relative min-h-screen flex flex-col items-center justify-center px-6 overflow-hidden parallax-bg pt-20">
      {/* Floating Elements */}
      <div
        className="absolute top-20 left-[10%] opacity-20 floating hidden lg:block"
        style={{ transform: `translate(${(x - window.innerWidth / 2) * 0.02}px, ${(y - window.innerHeight / 2) * 0.02}px)` }}
      >
        <div className="w-24 h-24 border border-blue-500/30 rounded-xl rotate-12"></div>
      </div>
      <div
        className="absolute bottom-40 right-[15%] opacity-20 floating-delayed hidden lg:block"
        style={{ transform: `translate(${(x - window.innerWidth / 2) * -0.015}px, ${(y - window.innerHeight / 2) * -0.015}px)` }}
      >
        <div className="w-16 h-16 border border-purple-500/30 rounded-full"></div>
      </div>
      <div
        className="absolute top-1/3 right-[8%] opacity-10 hidden lg:block"
        style={{ transform: `translate(${(x - window.innerWidth / 2) * 0.03}px, ${(y - window.innerHeight / 2) * 0.03}px)` }}
      >
        <Terminal size={80} className="text-blue-500" />
      </div>

      {/* Background Effects */}
      <div
        className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[160vw] h-[160vh] opacity-10 pointer-events-none transition-transform duration-150 ease-out"
        style={{ transform: `translate(-50%, -50%) translateY(${scrollY * 0.3}px) rotate(${scrollY * 0.02}deg)` }}
      >
        <div className="absolute inset-0 bg-[radial-gradient(circle_at_center,_#1e1b4b_0%,_transparent_70%)] blur-[160px]"></div>
      </div>

      <div
        className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[140vw] h-[140vh] opacity-20 pointer-events-none transition-transform duration-100 ease-out"
        style={{ transform: `translate(-50%, -50%) translateY(${scrollY * 0.15}px) scale(${1 + scrollY * 0.0001})` }}
      >
        <div className="absolute inset-0 bg-[radial-gradient(circle_at_center,_#3b82f6_0%,_transparent_60%)] blur-[120px] animate-slow-pulse"></div>
      </div>

      {/* Content */}
      <div
        className="relative z-10 w-full max-w-6xl text-center space-y-6 md:space-y-8 transition-all duration-300 ease-out"
        style={{
          transform: `perspective(1000px) rotateX(${progress * 15}deg) scale(${1 - progress * 0.2})`,
          opacity: 1 - progress * 0.5
        }}
      >
        {/* Badge */}
        <div className="inline-flex items-center space-x-2 px-4 py-2 rounded-full border border-white/10 bg-white/5 backdrop-blur-sm mb-2 animate-in fade-in duration-1000">
          <CircleDot size={10} className="text-white animate-pulse" />
          <span className="text-[8px] md:text-[10px] font-mono tracking-widest uppercase text-zinc-400">Gemini 3 Cognitive Layer Activated</span>
          <span className="text-[8px] md:text-[10px] font-mono tracking-widest uppercase text-white">• LIVE</span>
        </div>

        {/* Main Title */}
        <h1 className="text-5xl sm:text-7xl md:text-[100px] lg:text-[120px] font-bold tracking-[-0.06em] leading-[0.9] mb-4 md:mb-8 animate-in slide-in-from-bottom-8 duration-1000">
          The Desktop,<br />
          <span className="text-zinc-400">{typedText}</span>
          <span className="typing-cursor"></span>
        </h1>

        {/* Subtitle */}
        <p className="text-lg md:text-2xl text-zinc-400 max-w-2xl mx-auto font-light tracking-tight leading-relaxed animate-in fade-in slide-in-from-bottom-12 duration-1000 delay-200">
          A native cognitive agent that <span className="text-white font-medium">sees</span>, <span className="text-white font-medium">understands</span>, and <span className="text-white font-medium">executes</span> across your operating system.
        </p>

        {/* CTAs */}
        <div className="flex flex-col sm:flex-row items-center justify-center space-y-6 sm:space-y-0 sm:space-x-8 pt-8 md:pt-10 animate-in fade-in duration-1000 delay-500">
          <button className="group flex items-center space-x-3 bg-white text-black px-8 py-4 rounded-full font-bold uppercase tracking-widest text-xs hover:scale-105 transition-all duration-500 magnetic-btn">
            <Download size={18} />
            <span>Install for Windows</span>
          </button>

          <a href="#demo" className="group flex items-center space-x-2 text-[10px] uppercase tracking-[0.2em] text-zinc-400 hover:text-white transition-colors">
            <Play size={14} className="group-hover:scale-110 transition-transform" />
            <span>Watch Demo</span>
            <ArrowRight size={12} className="group-hover:translate-x-1 transition-transform" />
          </a>
        </div>

        {/* Stats Row */}
        <div className="flex justify-center gap-12 pt-12 animate-in fade-in duration-1000 delay-700">
          <div className="text-center">
            <div className="text-2xl md:text-3xl font-bold text-white">2.5K+</div>
            <div className="text-[10px] uppercase tracking-widest text-zinc-600 mt-1">Active Users</div>
          </div>
          <div className="text-center">
            <div className="text-2xl md:text-3xl font-bold text-white">&lt;400ms</div>
            <div className="text-[10px] uppercase tracking-widest text-zinc-600 mt-1">Response Time</div>
          </div>
          <div className="text-center">
            <div className="text-2xl md:text-3xl font-bold text-white">100%</div>
            <div className="text-[10px] uppercase tracking-widest text-zinc-600 mt-1">Local Execution</div>
          </div>
        </div>
      </div>


    </section>
  );
};

// ==================== LOGO WALL ====================

const LogoWall = () => {
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
};

// ==================== DEMO SECTION ====================

const DemoSection = () => {
  const [activeDemo, setActiveDemo] = useState(0);
  const demos = [
    { title: 'Voice Command', desc: 'Open Chrome and search for weather', icon: <Command size={20} /> },
    { title: 'Visual Analysis', desc: 'Analyzing screen elements...', icon: <Eye size={20} /> },
    { title: 'Auto Execute', desc: 'Clicking on search bar...', icon: <MousePointer size={20} /> },
  ];

  useEffect(() => {
    const timer = setInterval(() => {
      setActiveDemo((prev) => (prev + 1) % demos.length);
    }, 3000);
    return () => clearInterval(timer);
  }, []);

  return (
    <section id="demo" className="py-24 md:py-40 px-6">
      <div className="max-w-6xl mx-auto">
        <div className="text-center mb-16">
          <span className="text-[10px] uppercase tracking-[0.4em] text-white font-bold">Live Demo</span>
          <h2 className="text-4xl md:text-5xl font-bold tracking-tighter mt-4">See Kernal Agent in Action</h2>
          <p className="text-zinc-500 mt-4 max-w-xl mx-auto">Watch how Kernal Agent understands your intent and executes complex workflows automatically.</p>
        </div>

        <div className="grid lg:grid-cols-2 gap-12 items-center">
          {/* Demo Window */}
          <div className="demo-window">
            <div className="demo-titlebar">
              <div className="demo-dot demo-dot-red"></div>
              <div className="demo-dot demo-dot-yellow"></div>
              <div className="demo-dot demo-dot-green"></div>
              <span className="ml-4 text-xs text-zinc-500 font-mono">kernel-agent.exe</span>
            </div>
            <div className="demo-content relative">
              <div className="space-y-4">
                <div className="flex items-center gap-3 text-zinc-400">
                  <Sparkles size={16} className="text-white" />
                  <span className="text-sm font-mono">Kernal Agent v0.1.2-alpha</span>
                </div>
                <div className="h-px bg-zinc-800 my-4"></div>

                {/* Animated Demo Steps */}
                {demos.map((demo, i) => (
                  <div
                    key={i}
                    className={`flex items-center gap-3 p-3 rounded-lg transition-all duration-500 ${activeDemo >= i ? 'bg-white/5 border border-white/10' : 'opacity-30'}`}
                  >
                    <div className={`${activeDemo >= i ? 'text-white' : 'text-zinc-600'}`}>
                      {activeDemo > i ? <Check size={20} className="text-white" /> : demo.icon}
                    </div>
                    <div>
                      <div className="text-sm font-medium text-white">{demo.title}</div>
                      <div className="text-xs text-zinc-500 font-mono">{demo.desc}</div>
                    </div>
                    {activeDemo === i && (
                      <div className="ml-auto">
                        <div className="w-2 h-2 bg-white rounded-full animate-pulse"></div>
                      </div>
                    )}
                  </div>
                ))}

                <div className="mt-6 p-4 bg-white/10 border border-white/20 rounded-lg">
                  <div className="flex items-center gap-2 text-white">
                    <Check size={16} />
                    <span className="text-sm font-medium">Task completed successfully</span>
                  </div>
                </div>
              </div>

              {/* Animated Cursor */}
              <div
                className="absolute w-4 h-4 pointer-events-none transition-all duration-300"
                style={{
                  top: `${80 + activeDemo * 60}px`,
                  left: '40%',
                }}
              >
                <MousePointer size={16} className="text-white drop-shadow-lg" />
              </div>
            </div>
          </div>

          {/* Demo Description */}
          <div className="space-y-8">
            <h3 className="text-3xl font-bold tracking-tight">Intelligent Desktop Automation</h3>
            <p className="text-zinc-400 leading-relaxed">
              Kernal Agent uses Gemini 3's multimodal capabilities to understand exactly what you want,
              analyze your screen in real-time, and execute actions with pixel-perfect precision.
            </p>
            <div className="space-y-4">
              {[
                { icon: <Eye size={20} />, title: 'Visual Understanding', desc: 'Sees and understands any UI, legacy or modern' },
                { icon: <Zap size={20} />, title: 'Instant Execution', desc: 'Sub-400ms response time for seamless automation' },
                { icon: <Monitor size={20} />, title: 'System-Wide Access', desc: 'Works across all applications, not just browsers' },
              ].map((item, i) => (
                <div key={i} className="flex items-start gap-4 p-4 rounded-xl bg-white/[0.02] border border-white/5 hover:border-white/30 transition-colors">
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
  );
};

// ==================== BENTO FEATURES ====================

const BentoFeatures = () => {
  const ref = useRef<HTMLElement>(null);
  const [inView, setInView] = useState(false);

  useEffect(() => {
    const observer = new IntersectionObserver(([entry]) => {
      if (entry.isIntersecting) setInView(true);
    }, { threshold: 0.1 });
    if (ref.current) observer.observe(ref.current);
    return () => observer.disconnect();
  }, []);

  return (
    <section id="features" ref={ref} className="py-24 md:py-40 px-6 bg-zinc-950/30">
      <div className="max-w-7xl mx-auto">
        <div className="text-center mb-16">
          <span className="text-[10px] uppercase tracking-[0.4em] text-white font-bold">Capabilities</span>
          <h2 className="text-4xl md:text-5xl font-bold tracking-tighter mt-4">Built Different</h2>
          <p className="text-zinc-500 mt-4 max-w-xl mx-auto">Everything you need for autonomous desktop control.</p>
        </div>

        <div className={`bento-grid ${inView ? 'stagger-in' : ''}`}>
          {/* Large Feature */}
          <div className="bento-item bento-large flex flex-col justify-between">
            <div>
              <div className="text-white mb-4"><Eye size={32} /></div>
              <h3 className="text-2xl font-bold mb-2">Multimodal Vision</h3>
              <p className="text-zinc-500 text-sm">Real-time visual parsing using Gemini 3 Vision. Kernal Agent sees your screen exactly as you do.</p>
            </div>
            <div className="mt-6 p-4 bg-white/[0.02] rounded-xl border border-white/5">
              <div className="grid grid-cols-3 gap-2">
                {[1, 2, 3, 4, 5, 6].map(i => (
                  <div key={i} className="aspect-video bg-white/5 rounded animate-pulse"></div>
                ))}
              </div>
            </div>
          </div>

          {/* Wide Feature */}
          <div className="bento-item bento-wide">
            <div className="flex items-start gap-4">
              <div className="text-white"><Zap size={28} /></div>
              <div>
                <h3 className="text-xl font-bold mb-2">Lightning Fast</h3>
                <p className="text-zinc-500 text-sm">Sub-400ms latency for immediate response. No cloud round-trips.</p>
              </div>
            </div>
            <div className="mt-4 flex items-center gap-2">
              <div className="h-2 flex-1 bg-zinc-800 rounded-full overflow-hidden">
                <div className="h-full w-[85%] bg-white rounded-full"></div>
              </div>
              <span className="text-xs text-zinc-500">~350ms avg</span>
            </div>
          </div>

          {/* Normal Feature */}
          <div className="bento-item">
            <div className="text-white mb-4"><Terminal size={28} /></div>
            <h3 className="text-lg font-bold mb-2">Native Execution</h3>
            <p className="text-zinc-500 text-sm">Direct OS-level control via synthesized inputs.</p>
          </div>

          {/* Normal Feature */}
          <div className="bento-item">
            <div className="text-white mb-4"><Layers size={28} /></div>
            <h3 className="text-lg font-bold mb-2">Context Aware</h3>
            <p className="text-zinc-500 text-sm">Remembers your workflows and adapts to your patterns.</p>
          </div>

          {/* Wide Feature */}
          <div className="bento-item bento-wide">
            <div className="flex items-start gap-4">
              <div className="text-white"><Sparkles size={28} /></div>
              <div>
                <h3 className="text-xl font-bold mb-2">Natural Language</h3>
                <p className="text-zinc-500 text-sm">Just describe what you want. Kernal Agent figures out the rest.</p>
                <div className="mt-3 p-3 bg-zinc-900 rounded-lg font-mono text-xs text-zinc-400">
                  <span className="text-white">"</span>Open Spotify and play my discover weekly<span className="text-white">"</span>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </section>
  );
};

// ==================== TESTIMONIALS ====================

const Testimonials = () => {
  const testimonials = [
    { name: 'Alex Chen', role: 'Software Engineer', company: 'Stripe', quote: 'Kernal Agent has completely changed how I interact with my computer. It\'s like having a second pair of hands.' },
    { name: 'Sarah Miller', role: 'Product Designer', company: 'Figma', quote: 'The visual understanding is incredible. It navigates complex UIs that other tools can\'t handle.' },
    { name: 'James Wilson', role: 'Data Scientist', company: 'Netflix', quote: 'I automate my entire data pipeline setup with Kernal Agent. What took hours now takes minutes.' },
    { name: 'Emily Davis', role: 'DevOps Lead', company: 'Cloudflare', quote: 'The sub-400ms latency is no joke. Kernal Agent feels instant, even for complex multi-step tasks.' },
    { name: 'Michael Brown', role: 'Founder', company: 'TechStartup', quote: 'We deployed Kernal Agent across our team. Productivity is up 40% on repetitive tasks.' },
    { name: 'Lisa Wang', role: 'ML Engineer', company: 'OpenAI', quote: 'Finally, an AI agent that actually works. The Gemini 3 integration is seamless.' },
  ];

  return (
    <section id="testimonials" className="py-24 md:py-40 overflow-hidden">
      <div className="text-center mb-16 px-6">
        <span className="text-[10px] uppercase tracking-[0.4em] text-blue-500 font-bold">Testimonials</span>
        <h2 className="text-4xl md:text-5xl font-bold tracking-tighter mt-4">Loved by Developers</h2>
      </div>

      <div className="relative">
        <div className="testimonial-track">
          {[...testimonials, ...testimonials].map((t, i) => (
            <div key={i} className="testimonial-card">
              <Quote size={24} className="text-blue-500/30 mb-4" />
              <p className="text-zinc-300 mb-6">{t.quote}</p>
              <div className="flex items-center gap-3">
                <div className="w-10 h-10 rounded-full bg-gradient-to-br from-blue-500 to-purple-500 flex items-center justify-center text-white font-bold">
                  {t.name[0]}
                </div>
                <div>
                  <div className="font-medium text-white">{t.name}</div>
                  <div className="text-xs text-zinc-500">{t.role} at {t.company}</div>
                </div>
              </div>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
};

// ==================== STATS SECTION ====================

const StatsSection = () => {
  const ref = useRef<HTMLElement>(null);
  const [inView, setInView] = useState(false);
  const users = useCountUp(2547, 2000, inView);
  const tasks = useCountUp(150000, 2500, inView);
  const uptime = useCountUp(99, 1500, inView);

  useEffect(() => {
    const observer = new IntersectionObserver(([entry]) => {
      if (entry.isIntersecting) setInView(true);
    }, { threshold: 0.2 });
    if (ref.current) observer.observe(ref.current);
    return () => observer.disconnect();
  }, []);

  return (
    <section ref={ref} className="py-24 px-6 border-y border-zinc-900 bg-gradient-to-b from-transparent via-blue-950/5 to-transparent">
      <div className="max-w-5xl mx-auto grid md:grid-cols-4 gap-8 text-center">
        <div>
          <div className="text-4xl md:text-5xl font-bold text-white">{users.toLocaleString()}+</div>
          <div className="text-[10px] uppercase tracking-widest text-zinc-600 mt-2">Active Users</div>
        </div>
        <div>
          <div className="text-4xl md:text-5xl font-bold text-white">{tasks.toLocaleString()}+</div>
          <div className="text-[10px] uppercase tracking-widest text-zinc-600 mt-2">Tasks Executed</div>
        </div>
        <div>
          <div className="text-4xl md:text-5xl font-bold text-white">{uptime}.9%</div>
          <div className="text-[10px] uppercase tracking-widest text-zinc-600 mt-2">Uptime</div>
        </div>
        <div>
          <div className="text-4xl md:text-5xl font-bold text-white flex items-center justify-center gap-1">
            4.9 <Star size={24} className="text-white fill-white" />
          </div>
          <div className="text-[10px] uppercase tracking-widest text-zinc-600 mt-2">User Rating</div>
        </div>
      </div>
    </section>
  );
};

// ==================== TECH SECTION ====================

const TechSection = () => {
  const sectionRef = useRef<HTMLElement>(null);
  const progress = useScrollProgress(sectionRef);

  return (
    <section id="tech" ref={sectionRef} className="py-24 md:py-40 px-6 relative overflow-hidden">
      <div
        className="absolute inset-0 opacity-[0.06] pointer-events-none transition-transform duration-300 ease-out"
        style={{
          backgroundImage: 'linear-gradient(#fff 1px, transparent 1px), linear-gradient(90deg, #fff 1px, transparent 1px)',
          backgroundSize: '60px 60px',
          transform: `translateY(${(progress - 0.5) * 100}px) rotate(${(progress - 0.5) * 5}deg) scale(${1 + Math.abs(progress - 0.5) * 0.1})`
        }}
      ></div>

      <div
        className="absolute top-1/2 left-0 w-full h-[1px] bg-gradient-to-r from-transparent via-white/30 to-transparent transition-transform duration-100"
        style={{ transform: `scaleX(${0.4 + Math.abs(progress - 0.5) * 2.5})` }}
      ></div>

      <div className="max-w-6xl mx-auto grid md:grid-cols-2 gap-12 md:gap-20 items-center relative z-10">
        <div
          className="space-y-6 md:space-y-8 transition-all duration-300 ease-out text-center md:text-left"
          style={{ transform: `translateX(${(progress - 0.5) * -50}px) scale(${0.95 + (1 - Math.abs(progress - 0.5) * 2) * 0.05})` }}
        >
          <span className="text-[10px] uppercase tracking-[0.4em] text-white font-bold">Architecture</span>
          <h2 className="text-4xl md:text-5xl font-bold tracking-tighter leading-none">Cognition Engine: <br /><span className="text-zinc-400">Gemini 3.</span></h2>
          <p className="text-zinc-400 text-base md:text-lg font-light leading-relaxed">
            Kernal Agent runs a custom multimodal cognition stack built on Gemini 3. Visual grounding. Long-horizon reasoning. Deterministic execution.
          </p>
          <div className="grid grid-cols-2 gap-6 md:gap-8 pt-6 md:pt-10">
            <div>
              <div className="text-2xl md:text-3xl font-mono mb-2 text-white">2.0M</div>
              <div className="text-[9px] md:text-[10px] uppercase tracking-widest text-zinc-600">Context Window</div>
            </div>
            <div>
              <div className="text-2xl md:text-3xl font-mono mb-2 text-white">Native</div>
              <div className="text-[9px] md:text-[10px] uppercase tracking-widest text-zinc-600">Deterministic Engine</div>
            </div>
          </div>
        </div>

        <div
          className="relative aspect-square flex items-center justify-center transition-transform duration-300 ease-out scale-75 md:scale-100"
          style={{
            transform: `perspective(1000px) rotateY(${(progress - 0.5) * -45}deg) scale(${0.8 + (1 - Math.abs(progress - 0.5) * 2) * 0.2})`,
            filter: `blur(${Math.abs(progress - 0.5) * 10}px)`
          }}
        >
          <div className="absolute w-full h-full border border-white/5 rounded-full animate-[spin_25s_linear_infinite]"></div>
          <div className="absolute w-[80%] h-[80%] border border-white/10 rounded-full animate-[spin_20s_linear_infinite_reverse]"></div>
          <div className="w-1/3 h-1/3 bg-blue-500/10 rounded-full blur-3xl animate-pulse"></div>

          <div className="relative z-10 flex flex-col items-center justify-center transition-all duration-500">
            <Cpu size={60} className="text-white relative z-10 md:w-20 md:h-20 transition-transform duration-700 hover:rotate-90" />
            <div className="mt-6 text-[8px] md:text-[10px] font-mono tracking-[0.5em] text-white/50 uppercase text-center">Neural Gateway</div>
          </div>
        </div>
      </div>
    </section>
  );
};

// ==================== CTA ====================

const CTA = () => {
  const sectionRef = useRef<HTMLElement>(null);
  const progress = useScrollProgress(sectionRef);
  const [inView, setInView] = useState(false);

  useEffect(() => {
    const observer = new IntersectionObserver(([entry]) => {
      setInView(entry.isIntersecting);
    }, { threshold: 0.2 });
    if (sectionRef.current) observer.observe(sectionRef.current);
    return () => observer.disconnect();
  }, []);

  return (
    <section ref={sectionRef} className="relative py-32 md:py-60 px-6 bg-white text-black text-center overflow-hidden">
      <div className={`absolute inset-0 pointer-events-none transition-all duration-1000 ease-in-out ${inView ? 'opacity-100' : 'opacity-0'}`}>
        <div className={`absolute left-0 top-0 h-full bg-blue-50 transition-all duration-1000 delay-300 ${inView ? 'w-full' : 'w-0'}`}></div>
        <div className={`absolute right-0 top-0 h-full bg-zinc-50 transition-all duration-1000 delay-500 ${inView ? 'w-full' : 'w-0'}`}></div>
      </div>

      <div className="absolute inset-0 z-0 pointer-events-none opacity-20">
        <div className="absolute top-[-10%] left-[-10%] w-[40%] h-[40%] bg-blue-400 blur-[120px] rounded-full animate-[slow-pulse_12s_infinite]"></div>
        <div className="absolute bottom-[-10%] right-[-10%] w-[30%] h-[30%] bg-zinc-400 blur-[100px] rounded-full animate-[slow-pulse_15s_infinite_reverse]"></div>
      </div>

      <div
        className="relative z-10 w-full max-w-4xl mx-auto space-y-8 md:space-y-12 transition-all duration-300 ease-out"
        style={{
          transform: `perspective(1000px) rotateX(${(progress - 0.5) * -15}deg) scale(${0.9 + (1 - Math.abs(progress - 0.5) * 2) * 0.1})`
        }}
      >
        <div className="py-4 md:py-8">
          <h2 className={`text-5xl sm:text-7xl md:text-8xl font-bold tracking-tighter leading-[1.1] md:leading-tight transition-all duration-1000 ease-out transform ${inView ? 'translate-y-0 opacity-100' : 'translate-y-24 opacity-0'}`}>
            Ready to <br /><span className="text-zinc-600">delegate?</span>
          </h2>
        </div>

        <div className={`flex flex-col items-center space-y-6 md:space-y-8 transition-all duration-1000 delay-500 ${inView ? 'opacity-100 translate-y-0' : 'opacity-0 translate-y-8'}`}>
          <button className="bg-black text-white px-10 md:px-16 py-5 md:py-7 rounded-full font-bold uppercase tracking-widest text-xs md:text-sm hover:scale-110 transition-transform duration-500 shadow-[0_20px_50px_rgba(0,0,0,0.15)] relative overflow-hidden group magnetic-btn">
            <span className="relative z-10 flex items-center gap-3">
              <Download size={18} />
              Get the Agent
            </span>
            <div className="absolute inset-0 bg-zinc-800 translate-y-full group-hover:translate-y-0 transition-transform duration-500"></div>
          </button>

          <div className="text-[9px] md:text-xs font-mono uppercase tracking-[0.3em] opacity-40">
            Windows 11 • Local Execution • v0.1.2-Alpha
          </div>

          <div className="flex items-center gap-2 text-sm text-zinc-500">
            <Users size={16} />
            <span>Join 2,500+ developers using Kernal Agent</span>
          </div>
        </div>
      </div>

      <div className={`absolute top-0 left-0 w-12 md:w-20 h-12 md:h-20 border-t border-l border-black/10 transition-all duration-1000 delay-700 ${inView ? 'translate-x-4 md:translate-x-10 translate-y-4 md:translate-y-10 opacity-100' : 'translate-x-0 translate-y-0 opacity-0'}`}></div>
      <div className={`absolute bottom-0 right-0 w-12 md:w-20 h-12 md:h-20 border-b border-r border-black/10 transition-all duration-1000 delay-700 ${inView ? '-translate-x-4 md:-translate-x-10 -translate-y-4 md:-translate-y-10 opacity-100' : 'translate-x-0 translate-y-0 opacity-0'}`}></div>
    </section>
  );
};

// ==================== FOOTER ====================

const Footer = () => (
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
          <div className="flex gap-4 mt-6">
            <a href="#" className="w-10 h-10 rounded-full border border-zinc-800 flex items-center justify-center hover:border-white hover:text-white transition-colors">
              <span className="text-xs font-bold">X</span>
            </a>
            <a href="#" className="w-10 h-10 rounded-full border border-zinc-800 flex items-center justify-center hover:border-white hover:text-white transition-colors">
              <span className="text-xs font-bold">GH</span>
            </a>
            <a href="#" className="w-10 h-10 rounded-full border border-zinc-800 flex items-center justify-center hover:border-white hover:text-white transition-colors">
              <span className="text-xs font-bold">DC</span>
            </a>
          </div>
        </div>

        <div>
          <h4 className="text-white font-bold uppercase tracking-widest text-[10px] mb-4">Product</h4>
          <div className="space-y-3 text-sm">
            <a href="#" className="block hover:text-white transition-colors">Features</a>
            <a href="#" className="block hover:text-white transition-colors">Documentation</a>
            <a href="#" className="block hover:text-white transition-colors">Changelog</a>
            <a href="#" className="block hover:text-white transition-colors">Roadmap</a>
          </div>
        </div>

        <div>
          <h4 className="text-white font-bold uppercase tracking-widest text-[10px] mb-4">Legal</h4>
          <div className="space-y-3 text-sm">
            <a href="#" className="block hover:text-white transition-colors">Privacy Policy</a>
            <a href="#" className="block hover:text-white transition-colors">Terms of Service</a>
            <a href="#" className="block hover:text-white transition-colors">License</a>
          </div>
        </div>
      </div>

      <div className="pt-8 border-t border-zinc-900 flex flex-col md:flex-row justify-between items-center gap-4">
        <div className="text-[10px] font-mono opacity-50">
          GEMINI-3-HACKATHON-ENTRY // 2024
        </div>
        <div className="text-[10px] opacity-50">
          Built with ❤️ and Gemini 3
        </div>
      </div>
    </div>
  </footer>
);

// ==================== AUTH COMPONENTS ====================

const useHash = () => {
  const [hash, setHash] = useState(window.location.hash);

  useEffect(() => {
    const handleHashChange = () => setHash(window.location.hash);
    window.addEventListener('hashchange', handleHashChange);
    return () => window.removeEventListener('hashchange', handleHashChange);
  }, []);

  return hash;
};

interface AuthInputProps {
  type: string;
  placeholder: string;
  icon: React.ReactNode;
  value: string;
  onChange: (e: React.ChangeEvent<HTMLInputElement>) => void;
  showPasswordToggle?: boolean;
}

const AuthInput: React.FC<AuthInputProps> = ({ type, placeholder, icon, value, onChange, showPasswordToggle }) => {
  const [showPassword, setShowPassword] = useState(false);
  const inputType = showPasswordToggle ? (showPassword ? 'text' : 'password') : type;

  return (
    <div className="relative group">
      <div className="absolute left-4 top-1/2 -translate-y-1/2 text-zinc-500 group-focus-within:text-white transition-colors">
        {icon}
      </div>
      <input
        type={inputType}
        placeholder={placeholder}
        value={value}
        onChange={onChange}
        className="w-full bg-white/[0.03] border border-white/10 rounded-xl pl-12 pr-12 py-4 text-white placeholder:text-zinc-600 focus:outline-none focus:border-white/30 focus:bg-white/[0.05] transition-all duration-300"
      />
      {showPasswordToggle && (
        <button
          type="button"
          onClick={() => setShowPassword(!showPassword)}
          className="absolute right-4 top-1/2 -translate-y-1/2 text-zinc-500 hover:text-white transition-colors"
        >
          {showPassword ? <EyeOff size={18} /> : <Eye size={18} />}
        </button>
      )}
    </div>
  );
};

const AuthLayout: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const { x, y } = useMousePosition();

  return (
    <div className="min-h-screen bg-kernel-bg text-white font-sans overflow-hidden noise-overlay relative flex items-center justify-center px-6 py-12">
      {/* Background Elements */}
      <div
        className="cursor-glow hidden lg:block"
        style={{ left: x, top: y }}
      />
      <div className="absolute inset-0 bg-[radial-gradient(circle_at_30%_20%,_#1e1b4b_0%,_transparent_50%)] opacity-20"></div>
      <div className="absolute inset-0 bg-[radial-gradient(circle_at_70%_80%,_#1e1b4b_0%,_transparent_50%)] opacity-10"></div>

      {/* Grid Pattern */}
      <div
        className="absolute inset-0 opacity-[0.03] pointer-events-none"
        style={{
          backgroundImage: 'linear-gradient(#fff 1px, transparent 1px), linear-gradient(90deg, #fff 1px, transparent 1px)',
          backgroundSize: '60px 60px'
        }}
      />

      {/* Back to Home */}
      <a
        href="#"
        className="absolute top-8 left-8 flex items-center gap-2 text-zinc-500 hover:text-white transition-colors text-sm group"
      >
        <ArrowLeft size={16} className="group-hover:-translate-x-1 transition-transform" />
        <span>Back to Home</span>
      </a>

      {/* Logo */}
      <div className="absolute top-8 right-8 flex items-center gap-2">
        <div className="w-5 h-5 border border-white flex items-center justify-center rotate-45">
          <div className="w-1.5 h-1.5 bg-white"></div>
        </div>
        <span className="font-bold tracking-tighter text-lg uppercase">Kernal</span>
      </div>

      {children}
    </div>
  );
};

const LoginPage: React.FC<{ onNavigate: (page: string) => void }> = ({ onNavigate }) => {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [isLoading, setIsLoading] = useState(false);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    setIsLoading(true);
    // Simulate loading
    setTimeout(() => setIsLoading(false), 1500);
  };

  return (
    <AuthLayout>
      <div className="w-full max-w-md">
        {/* Auth Card */}
        <div className="relative">
          {/* Glow effect */}
          <div className="absolute -inset-1 bg-gradient-to-r from-white/10 via-white/5 to-white/10 rounded-2xl blur-xl opacity-50"></div>

          <div className="relative bg-zinc-950/80 backdrop-blur-xl border border-white/10 rounded-2xl p-8 md:p-10">
            {/* Header */}
            <div className="text-center mb-8">
              <h1 className="text-3xl font-bold tracking-tight mb-2">Welcome back</h1>
              <p className="text-zinc-500 text-sm">Sign in to continue to Kernal Agent</p>
            </div>

            {/* Social Login */}
            <div className="grid grid-cols-2 gap-3 mb-6">
              <button className="flex items-center justify-center gap-2 bg-white/[0.03] border border-white/10 rounded-xl py-3 px-4 text-sm text-zinc-400 hover:text-white hover:border-white/30 hover:bg-white/[0.05] transition-all duration-300">
                <svg className="w-5 h-5" viewBox="0 0 24 24" fill="currentColor">
                  <path d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z" />
                  <path d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z" />
                  <path d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z" />
                  <path d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z" />
                </svg>
                Google
              </button>
              <button className="flex items-center justify-center gap-2 bg-white/[0.03] border border-white/10 rounded-xl py-3 px-4 text-sm text-zinc-400 hover:text-white hover:border-white/30 hover:bg-white/[0.05] transition-all duration-300">
                <Github size={18} />
                GitHub
              </button>
            </div>

            {/* Divider */}
            <div className="relative my-6">
              <div className="absolute inset-0 flex items-center">
                <div className="w-full border-t border-white/10"></div>
              </div>
              <div className="relative flex justify-center text-xs">
                <span className="bg-zinc-950 px-4 text-zinc-600 uppercase tracking-widest">or continue with</span>
              </div>
            </div>

            {/* Form */}
            <form onSubmit={handleSubmit} className="space-y-4">
              <AuthInput
                type="email"
                placeholder="Email address"
                icon={<Mail size={18} />}
                value={email}
                onChange={(e) => setEmail(e.target.value)}
              />
              <AuthInput
                type="password"
                placeholder="Password"
                icon={<Lock size={18} />}
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                showPasswordToggle
              />

              {/* Forgot Password */}
              <div className="flex justify-end">
                <a href="#" className="text-xs text-zinc-500 hover:text-white transition-colors">
                  Forgot password?
                </a>
              </div>

              {/* Submit Button */}
              <button
                type="submit"
                disabled={isLoading}
                className="w-full bg-white text-black py-4 rounded-xl font-bold uppercase tracking-widest text-xs hover:bg-zinc-200 transition-all duration-300 disabled:opacity-50 disabled:cursor-not-allowed relative overflow-hidden group"
              >
                <span className={`transition-opacity ${isLoading ? 'opacity-0' : 'opacity-100'}`}>
                  Sign In
                </span>
                {isLoading && (
                  <div className="absolute inset-0 flex items-center justify-center">
                    <div className="w-5 h-5 border-2 border-black/20 border-t-black rounded-full animate-spin"></div>
                  </div>
                )}
              </button>
            </form>

            {/* Footer */}
            <p className="text-center text-sm text-zinc-500 mt-6">
              Don't have an account?{' '}
              <a
                href="#signup"
                className="text-white hover:underline underline-offset-4"
                onClick={(e) => { e.preventDefault(); onNavigate('signup'); }}
              >
                Sign up
              </a>
            </p>
          </div>
        </div>

        {/* Terms */}
        <p className="text-center text-[10px] text-zinc-600 mt-6 max-w-sm mx-auto">
          By continuing, you agree to Kernal Agent's{' '}
          <a href="#" className="text-zinc-500 hover:text-white transition-colors">Terms of Service</a>
          {' '}and{' '}
          <a href="#" className="text-zinc-500 hover:text-white transition-colors">Privacy Policy</a>
        </p>
      </div>
    </AuthLayout>
  );
};

const SignupPage: React.FC<{ onNavigate: (page: string) => void }> = ({ onNavigate }) => {
  const [name, setName] = useState('');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [isLoading, setIsLoading] = useState(false);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    setIsLoading(true);
    setTimeout(() => setIsLoading(false), 1500);
  };

  return (
    <AuthLayout>
      <div className="w-full max-w-md">
        {/* Auth Card */}
        <div className="relative">
          {/* Glow effect */}
          <div className="absolute -inset-1 bg-gradient-to-r from-white/10 via-white/5 to-white/10 rounded-2xl blur-xl opacity-50"></div>

          <div className="relative bg-zinc-950/80 backdrop-blur-xl border border-white/10 rounded-2xl p-8 md:p-10">
            {/* Header */}
            <div className="text-center mb-8">
              <h1 className="text-3xl font-bold tracking-tight mb-2">Create account</h1>
              <p className="text-zinc-500 text-sm">Start automating with Kernal Agent today</p>
            </div>

            {/* Social Login */}
            <div className="grid grid-cols-2 gap-3 mb-6">
              <button className="flex items-center justify-center gap-2 bg-white/[0.03] border border-white/10 rounded-xl py-3 px-4 text-sm text-zinc-400 hover:text-white hover:border-white/30 hover:bg-white/[0.05] transition-all duration-300">
                <svg className="w-5 h-5" viewBox="0 0 24 24" fill="currentColor">
                  <path d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z" />
                  <path d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z" />
                  <path d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z" />
                  <path d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z" />
                </svg>
                Google
              </button>
              <button className="flex items-center justify-center gap-2 bg-white/[0.03] border border-white/10 rounded-xl py-3 px-4 text-sm text-zinc-400 hover:text-white hover:border-white/30 hover:bg-white/[0.05] transition-all duration-300">
                <Github size={18} />
                GitHub
              </button>
            </div>

            {/* Divider */}
            <div className="relative my-6">
              <div className="absolute inset-0 flex items-center">
                <div className="w-full border-t border-white/10"></div>
              </div>
              <div className="relative flex justify-center text-xs">
                <span className="bg-zinc-950 px-4 text-zinc-600 uppercase tracking-widest">or continue with</span>
              </div>
            </div>

            {/* Form */}
            <form onSubmit={handleSubmit} className="space-y-4">
              <AuthInput
                type="text"
                placeholder="Full name"
                icon={<User size={18} />}
                value={name}
                onChange={(e) => setName(e.target.value)}
              />
              <AuthInput
                type="email"
                placeholder="Email address"
                icon={<Mail size={18} />}
                value={email}
                onChange={(e) => setEmail(e.target.value)}
              />
              <AuthInput
                type="password"
                placeholder="Create password"
                icon={<Lock size={18} />}
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                showPasswordToggle
              />

              {/* Password Requirements */}
              <div className="space-y-2 py-2">
                <p className="text-[10px] uppercase tracking-widest text-zinc-600">Password must contain:</p>
                <div className="grid grid-cols-2 gap-2 text-xs">
                  <div className={`flex items-center gap-2 ${password.length >= 8 ? 'text-white' : 'text-zinc-600'}`}>
                    <Check size={12} />
                    <span>8+ characters</span>
                  </div>
                  <div className={`flex items-center gap-2 ${/[A-Z]/.test(password) ? 'text-white' : 'text-zinc-600'}`}>
                    <Check size={12} />
                    <span>Uppercase</span>
                  </div>
                  <div className={`flex items-center gap-2 ${/[0-9]/.test(password) ? 'text-white' : 'text-zinc-600'}`}>
                    <Check size={12} />
                    <span>Number</span>
                  </div>
                  <div className={`flex items-center gap-2 ${/[^A-Za-z0-9]/.test(password) ? 'text-white' : 'text-zinc-600'}`}>
                    <Check size={12} />
                    <span>Special char</span>
                  </div>
                </div>
              </div>

              {/* Submit Button */}
              <button
                type="submit"
                disabled={isLoading}
                className="w-full bg-white text-black py-4 rounded-xl font-bold uppercase tracking-widest text-xs hover:bg-zinc-200 transition-all duration-300 disabled:opacity-50 disabled:cursor-not-allowed relative overflow-hidden group"
              >
                <span className={`transition-opacity ${isLoading ? 'opacity-0' : 'opacity-100'}`}>
                  Create Account
                </span>
                {isLoading && (
                  <div className="absolute inset-0 flex items-center justify-center">
                    <div className="w-5 h-5 border-2 border-black/20 border-t-black rounded-full animate-spin"></div>
                  </div>
                )}
              </button>
            </form>

            {/* Footer */}
            <p className="text-center text-sm text-zinc-500 mt-6">
              Already have an account?{' '}
              <a
                href="#login"
                className="text-white hover:underline underline-offset-4"
                onClick={(e) => { e.preventDefault(); onNavigate('login'); }}
              >
                Sign in
              </a>
            </p>
          </div>
        </div>

        {/* Terms */}
        <p className="text-center text-[10px] text-zinc-600 mt-6 max-w-sm mx-auto">
          By creating an account, you agree to Kernal Agent's{' '}
          <a href="#" className="text-zinc-500 hover:text-white transition-colors">Terms of Service</a>
          {' '}and{' '}
          <a href="#" className="text-zinc-500 hover:text-white transition-colors">Privacy Policy</a>
        </p>
      </div>
    </AuthLayout>
  );
};

// ==================== LANDING PAGE ====================

const LandingPage = () => (
  <div className="min-h-screen selection:bg-white selection:text-black bg-kernel-bg text-white font-sans overflow-x-hidden noise-overlay">
    <CursorGlow />
    <Navbar />
    <main>
      <Hero />
      <LogoWall />
      <DemoSection />
      <BentoFeatures />
      <StatsSection />
      <TechSection />
      <CTA />
    </main>
    <Footer />
  </div>
);

// ==================== PAGE TRANSITION ====================

const PageTransition: React.FC<{ isVisible: boolean }> = ({ isVisible }) => {
  if (!isVisible) return null;

  return (
    <div className="fixed inset-0 z-[100] bg-kernel-bg flex flex-col items-center justify-center">
      {/* Background Pattern */}
      <div
        className="absolute inset-0 opacity-[0.02] pointer-events-none"
        style={{
          backgroundImage: 'linear-gradient(#fff 1px, transparent 1px), linear-gradient(90deg, #fff 1px, transparent 1px)',
          backgroundSize: '60px 60px'
        }}
      />

      {/* Animated Logo */}
      <div className="relative">
        {/* Outer Ring */}
        <div className="absolute -inset-8 border border-white/10 rounded-full animate-[spin_4s_linear_infinite]" />
        <div className="absolute -inset-12 border border-white/5 rounded-full animate-[spin_6s_linear_infinite_reverse]" />

        {/* Glow */}
        <div className="absolute -inset-4 bg-white/5 rounded-full blur-xl animate-pulse" />

        {/* Logo */}
        <div className="relative w-16 h-16 border-2 border-white flex items-center justify-center rotate-45 animate-pulse">
          <div className="w-4 h-4 bg-white animate-ping" style={{ animationDuration: '1.5s' }} />
        </div>
      </div>

      {/* Brand */}
      <div className="mt-12 text-center">
        <h2 className="text-2xl font-bold tracking-tighter uppercase animate-pulse">Kernal</h2>
        <p className="text-[10px] uppercase tracking-[0.4em] text-zinc-600 mt-2">Loading</p>
      </div>

      {/* Progress Bar */}
      <div className="mt-8 w-48 h-[2px] bg-zinc-900 rounded-full overflow-hidden">
        <div className="h-full bg-white rounded-full animate-[loading_1s_ease-in-out_infinite]"
          style={{
            width: '30%',
            animation: 'loading 0.8s ease-in-out infinite'
          }}
        />
      </div>

      {/* Inline keyframes for loading animation */}
      <style>{`
        @keyframes loading {
          0% { transform: translateX(-100%); width: 30%; }
          50% { width: 60%; }
          100% { transform: translateX(400%); width: 30%; }
        }
      `}</style>
    </div>
  );
};

// ==================== APP ====================

export default function App() {
  const [currentPage, setCurrentPage] = useState('home');
  const [isTransitioning, setIsTransitioning] = useState(false);
  const [nextPage, setNextPage] = useState<string | null>(null);
  const hash = useHash();

  useEffect(() => {
    let targetPage = 'home';
    if (hash === '#login') {
      targetPage = 'login';
    } else if (hash === '#signup') {
      targetPage = 'signup';
    }

    // Only transition if page actually changes
    if (targetPage !== currentPage) {
      setNextPage(targetPage);
      setIsTransitioning(true);

      // After transition animation, switch page
      const timer = setTimeout(() => {
        setCurrentPage(targetPage);
        setIsTransitioning(false);
        setNextPage(null);
      }, 800);

      return () => clearTimeout(timer);
    }
  }, [hash]);

  const navigate = (page: string) => {
    if (page === currentPage) return;

    setNextPage(page);
    setIsTransitioning(true);
    window.location.hash = page === 'home' ? '' : page;

    setTimeout(() => {
      setCurrentPage(page);
      setIsTransitioning(false);
      setNextPage(null);
    }, 800);
  };

  const renderPage = () => {
    switch (currentPage) {
      case 'login':
        return <LoginPage onNavigate={navigate} />;
      case 'signup':
        return <SignupPage onNavigate={navigate} />;
      default:
        return <LandingPage />;
    }
  };

  return (
    <>
      <PageTransition isVisible={isTransitioning} />
      <div className={`transition-opacity duration-300 ${isTransitioning ? 'opacity-0' : 'opacity-100'}`}>
        {renderPage()}
      </div>
    </>
  );
}
