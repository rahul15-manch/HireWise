import Hero from "@/components/Hero";
import Features from "@/components/Features";
import HowItWorks from "@/components/HowItWorks";
import Stats from "@/components/Stats";
import Testimonials from "@/components/Testimonials";
import FinalCTA from "@/components/FinalCTA";
import Footer from "@/components/Footer";

export default function Home() {
  return (
    <main className="min-h-screen bg-black">
      {/* Navigation (Simple) */}
      <nav className="fixed top-0 w-full z-50 bg-black/50 backdrop-blur-xl border-b border-white/5">
        <div className="container mx-auto px-6 h-20 flex items-center justify-between">
          <div className="flex items-center gap-2">
            <img src="/logo.png" alt="HireWise Logo" className="h-10 w-auto" />
          </div>
          <div className="hidden md:flex items-center gap-8 text-sm text-gray-400">
            <a href="#features" className="hover:text-white transition-colors">Features</a>
            <a href="#how-it-works" className="hover:text-white transition-colors">How it works</a>
            <a href="#testimonials" className="hover:text-white transition-colors">Testimonials</a>
            <a href="http://localhost:8000/login" className="px-5 py-2 bg-white text-black font-semibold rounded-full hover:bg-gray-200 transition-all decoration-none">
              Launch App
            </a>
          </div>
        </div>
      </nav>

      <Hero />
      <Stats />
      <Features />
      <HowItWorks />
      <Testimonials />
      <FinalCTA />
      <Footer />
    </main>
  );
}
