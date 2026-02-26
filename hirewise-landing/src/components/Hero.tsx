"use client";

import { motion } from "framer-motion";
import { ArrowRight, Play } from "lucide-react";

export default function Hero() {
    return (
        <section className="relative min-height-screen flex items-center justify-center overflow-hidden pt-20">
            {/* Background Blobs */}
            <div className="absolute top-0 -left-4 w-72 h-72 bg-purple-500 rounded-full mix-blend-multiply filter blur-3xl opacity-20 animate-blob" />
            <div className="absolute top-0 -right-4 w-72 h-72 bg-blue-500 rounded-full mix-blend-multiply filter blur-3xl opacity-20 animate-blob animation-delay-2000" />
            <div className="absolute -bottom-8 left-20 w-72 h-72 bg-pink-500 rounded-full mix-blend-multiply filter blur-3xl opacity-20 animate-blob animation-delay-4000" />

            <div className="container mx-auto px-6 relative z-10">
                <div className="flex flex-col lg:flex-row items-center gap-12">
                    {/* Text Content */}
                    <div className="flex-1 text-center lg:text-left">
                        <motion.h1
                            initial={{ opacity: 0, y: 20 }}
                            animate={{ opacity: 1, y: 0 }}
                            transition={{ duration: 0.6 }}
                            className="text-5xl lg:text-7xl font-bold mb-6 tracking-tight"
                        >
                            Smarter Interviews. <br />
                            <span className="text-gradient">Powered by AI.</span>
                        </motion.h1>

                        <motion.p
                            initial={{ opacity: 0, y: 20 }}
                            animate={{ opacity: 1, y: 0 }}
                            transition={{ duration: 0.6, delay: 0.2 }}
                            className="text-xl text-gray-400 mb-10 max-w-2xl mx-auto lg:mx-0 leading-relaxed"
                        >
                            HireWise automates technical screening, AI evaluation, and interview proctoring — all in one intelligent platform.
                        </motion.p>

                        <motion.div
                            initial={{ opacity: 0, y: 20 }}
                            animate={{ opacity: 1, y: 0 }}
                            transition={{ duration: 0.6, delay: 0.4 }}
                            className="flex flex-wrap items-center justify-center lg:justify-start gap-4"
                        >
                            <a href="http://localhost:8000/login" className="px-8 py-4 bg-white text-black font-semibold rounded-full hover:bg-gray-200 transition-all flex items-center gap-2 group no-underline">
                                Get Started
                                <ArrowRight className="w-4 h-4 group-hover:translate-x-1 transition-transform" />
                            </a>
                            <a href="#how-it-works" className="px-8 py-4 bg-white/5 border border-white/10 text-white font-semibold rounded-full hover:bg-white/10 transition-all flex items-center gap-2 no-underline">
                                <Play className="w-4 h-4" />
                                How HireWise Works
                            </a>
                        </motion.div>
                    </div>

                    {/* Illustration / Image */}
                    <motion.div
                        initial={{ opacity: 0, scale: 0.8 }}
                        animate={{ opacity: 1, scale: 1 }}
                        transition={{ duration: 0.8 }}
                        className="flex-1 relative"
                    >
                        <div className="relative z-10 glass-card p-4 rounded-3xl glow-blue">
                            <div className="aspect-video bg-black/40 rounded-2xl overflow-hidden flex items-center justify-center border border-white/5">
                                {/* Mock AI Interface */}
                                <div className="w-full h-full p-8 flex flex-col gap-4">
                                    <div className="h-4 w-1/3 bg-blue-500/20 rounded animate-pulse" />
                                    <div className="h-3 w-3/4 bg-white/5 rounded" />
                                    <div className="h-3 w-1/2 bg-white/5 rounded" />
                                    <div className="mt-auto flex justify-between">
                                        <div className="flex gap-2">
                                            <div className="w-8 h-8 rounded-full bg-purple-500/30" />
                                            <div className="w-8 h-8 rounded-full bg-blue-500/30" />
                                        </div>
                                        <div className="h-8 w-24 bg-blue-600 rounded-lg shadow-lg shadow-blue-500/30" />
                                    </div>
                                </div>
                            </div>
                        </div>
                        {/* Decorative elements */}
                        <div className="absolute -top-10 -right-10 w-32 h-32 bg-blue-500/10 rounded-full blur-2xl" />
                        <div className="absolute -bottom-10 -left-10 w-32 h-32 bg-purple-500/10 rounded-full blur-2xl" />
                    </motion.div>
                </div>
            </div>
        </section>
    );
}
