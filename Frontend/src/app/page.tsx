import { Navbar, Footer } from "@/components/layout";
import { CursorGlow, LogoWall } from "@/components/effects";
import { Hero, DemoSection, BentoFeatures, StatsSection, TechSection, CTA } from "@/components/sections";

export default function Home() {
    return (
        <div className="min-h-screen noise-overlay">
            <CursorGlow />
            <Navbar />
            <Hero />
            <LogoWall />
            <DemoSection />
            <BentoFeatures />
            <StatsSection />
            <TechSection />
            <CTA />
            <Footer />
        </div>
    );
}
