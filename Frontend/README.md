# Kernal Agent — Cognitive Desktop Copilot

<div align="center">
  <img src="public/logo.svg" alt="Kernal Agent Logo" width="80" height="80" />
  
  **A local-first cognitive agent powered by Gemini 3**
  
  [![Next.js](https://img.shields.io/badge/Next.js-15-black?style=flat-square&logo=next.js)](https://nextjs.org/)
  [![TypeScript](https://img.shields.io/badge/TypeScript-5.0-blue?style=flat-square&logo=typescript)](https://www.typescriptlang.org/)
  [![Tailwind CSS](https://img.shields.io/badge/Tailwind-4.0-38bdf8?style=flat-square&logo=tailwind-css)](https://tailwindcss.com/)
  [![License](https://img.shields.io/badge/License-MIT-green?style=flat-square)](LICENSE)
  
  [Live Demo](https://kernel-agent.vercel.app) • [Documentation](https://docs.kernalagent.com) • [Discord](https://discord.gg/kernalagent)
</div>

---

## ✨ Features

- 🧠 **Multimodal Vision** — Real-time visual parsing using Gemini 3 Vision
- ⚡ **Sub-400ms Latency** — Optimized inference pipeline for near-instant response
- 🖥️ **System-Wide Access** — Works across all applications, not just browsers
- 🗣️ **Natural Language** — Just describe what you want, Kernal figures out the rest
- 🔒 **Local-First** — Your data stays on your machine

---

## 🚀 Quick Start

### Prerequisites

- Node.js 18.17 or later
- npm, yarn, or pnpm

### Installation

```bash
# Clone the repository
git clone https://github.com/ShawnTheCreator/kernalagent.git

# Navigate to the frontend directory
cd kernalagent/Frontend

# Install dependencies
npm install

# Start the development server
npm run dev
```

Open [http://localhost:3000](http://localhost:3000) in your browser.

---

## 📁 Project Structure

```
src/
├── app/                    # Next.js App Router
│   ├── layout.tsx          # Root layout with fonts & metadata
│   ├── page.tsx            # Landing page
│   ├── globals.css         # Global styles & animations
│   ├── login/
│   │   └── page.tsx        # Login page
│   └── signup/
│       └── page.tsx        # Signup page
│
├── components/
│   ├── ui/                 # Reusable UI components
│   │   └── AuthInput.tsx   # Form input with icons
│   ├── layout/             # Layout components
│   │   ├── Navbar.tsx      # Navigation with mobile menu
│   │   ├── Footer.tsx      # Site footer
│   │   └── AuthLayout.tsx  # Auth pages wrapper
│   ├── sections/           # Page sections
│   │   ├── Hero.tsx        # Hero with typing effect
│   │   ├── DemoSection.tsx # Live demo terminal
│   │   ├── BentoFeatures.tsx # Feature grid
│   │   ├── StatsSection.tsx  # Stats counter
│   │   ├── TechSection.tsx   # Architecture diagram
│   │   └── CTA.tsx           # Call to action
│   └── effects/            # Visual effects
│       ├── CursorGlow.tsx  # Mouse-follow glow
│       ├── LogoWall.tsx    # Scrolling logos
│       └── PageTransition.tsx # Page loader
│
├── hooks/                  # Custom React hooks
│   ├── useMousePosition.ts # Track mouse position
│   ├── useScrollProgress.ts # Section scroll progress
│   └── useInView.ts        # Viewport intersection
│
├── lib/                    # Utilities
└── types/                  # TypeScript definitions
```

---

## 🛠️ Tech Stack

| Technology | Purpose |
|------------|---------|
| [Next.js 15](https://nextjs.org/) | React framework with App Router |
| [TypeScript](https://www.typescriptlang.org/) | Type safety |
| [Tailwind CSS 4](https://tailwindcss.com/) | Utility-first styling |
| [Lucide React](https://lucide.dev/) | Icon library |
| [Vercel](https://vercel.com/) | Deployment platform |

---

## 📜 Scripts

```bash
npm run dev      # Start development server
npm run build    # Build for production
npm run start    # Start production server
npm run lint     # Run ESLint
```

---

## 🌐 Deployment

### Deploy to Vercel

[![Deploy with Vercel](https://vercel.com/button)](https://vercel.com/new/clone?repository-url=https://github.com/ShawnTheCreator/kernalagent)

Or deploy manually:

```bash
npm install -g vercel
vercel --prod
```

---

## 🎨 Design System

### Colors

| Name | Value | Usage |
|------|-------|-------|
| `kernel-bg` | `#050505` | Background |
| `kernel-card` | `#0A0A0A` | Cards, panels |
| `kernel-border` | `#1A1A1A` | Borders |
| `white` | `#FFFFFF` | Primary text |
| `zinc-400` | `#A1A1AA` | Secondary text |
| `zinc-600` | `#52525B` | Muted text |

### Typography

- **Headings**: Inter (Bold, Tracking Tighter)
- **Body**: Inter (Regular)
- **Code**: Geist Mono

---

## 🤝 Contributing

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

---

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

---

<div align="center">
  <sub>Built with ❤️ by the Kernal Agent Team</sub>
</div>
