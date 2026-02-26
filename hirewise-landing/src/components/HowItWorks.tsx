"use client";

import { motion } from "framer-motion";
import { UserPlus, Cpu, Mic, FileCheck } from "lucide-react";

const steps = [
    {
        title: "Recruiter creates interview",
        description: "Set up roles and specific requirements.",
        icon: <UserPlus className="w-8 h-8" />,
    },
    {
        title: "AI generates questions",
        description: "Gemini 1.5 Flash creates role-specific tests.",
        icon: <Cpu className="w-8 h-8" />,
    },
    {
        title: "Candidate completes interview",
        description: "Async voice and code assessment.",
        icon: <Mic className="w-8 h-8" />,
    },
    {
        title: "AI scores + review",
        description: "Recruiter reviews automated evaluations.",
        icon: <FileCheck className="w-8 h-8" />,
    }
];

export default function HowItWorks() {
    return (
        <section className="py-24 bg-zinc-950 relative" id="how-it-works">
            <div className="container mx-auto px-6">
                <div className="text-center mb-20">
                    <h2 className="text-4xl font-bold mb-4">How <span className="text-gradient">HireWise</span> Works</h2>
                    <p className="text-gray-400">Transform your hiring process in four simple steps.</p>
                </div>

                <div className="relative">
                    {/* Connecting Line (Desktop) */}
                    <div className="hidden lg:block absolute top-1/2 left-0 w-full h-0.5 bg-gradient-to-r from-blue-500/20 via-purple-500/40 to-blue-500/20 -translate-y-16" />

                    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-12">
                        {steps.map((step, index) => (
                            <motion.div
                                key={index}
                                initial={{ opacity: 0, y: 30 }}
                                whileInView={{ opacity: 1, y: 0 }}
                                viewport={{ once: true }}
                                transition={{ delay: index * 0.2 }}
                                className="relative z-10 flex flex-col items-center text-center"
                            >
                                <div className="w-20 h-20 bg-black border border-white/10 rounded-2xl flex items-center justify-center mb-6 shadow-xl glow-blue group animate-pulse">
                                    <div className="text-blue-500 group-hover:scale-110 transition-transform">
                                        {step.icon}
                                    </div>
                                    {/* Step Number */}
                                    <div className="absolute -top-3 -right-3 w-8 h-8 bg-blue-600 rounded-full flex items-center justify-center text-xs font-bold border-2 border-black">
                                        {index + 1}
                                    </div>
                                </div>
                                <h3 className="text-xl font-bold mb-3">{step.title}</h3>
                                <p className="text-gray-400 text-sm leading-relaxed">
                                    {step.description}
                                </p>
                            </motion.div>
                        ))}
                    </div>
                </div>
            </div>
        </section>
    );
}
