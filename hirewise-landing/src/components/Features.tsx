"use client";

import { motion } from "framer-motion";
import {
    Bot,
    BarChart3,
    ShieldCheck,
    Video,
    Save,
    Users,
    LayoutDashboard
} from "lucide-react";

const features = [
    {
        title: "AI Question Generation",
        description: "Auto-generate role-specific interview questions using Google Gemini 1.5 Flash",
        icon: <Bot className="w-6 h-6 text-blue-400" />,
    },
    {
        title: "AI Technical Analysis",
        description: "Groq Llama 3.3 70B evaluates responses, scores candidates from 0–100, and highlights strengths & weaknesses",
        icon: <BarChart3 className="w-6 h-6 text-purple-400" />,
    },
    {
        title: "AI Proctoring",
        description: "Real-time CV-based proctoring using MediaPipe detects eye movement, head pose, and multiple faces",
        icon: <ShieldCheck className="w-6 h-6 text-green-400" />,
    },
    {
        title: "Video Recording",
        description: "Full interview capture using MediaRecorder API for recruiter review and compliance",
        icon: <Video className="w-6 h-6 text-red-400" />,
    },
    {
        title: "Question Templates",
        description: "Save, reuse, and manage interview question sets across multiple hiring pipelines",
        icon: <Save className="w-6 h-6 text-yellow-400" />,
    },
    {
        title: "Async Interview Flow",
        description: "Candidates complete interviews at their own pace with built-in voice-to-text transcription",
        icon: <Users className="w-6 h-6 text-teal-400" />,
    },
    {
        title: "Recruiter Dashboard",
        description: "Review candidate scores, watch recordings, and analyze integrity reports in one place",
        icon: <LayoutDashboard className="w-6 h-6 text-indigo-400" />,
    }
];

export default function Features() {
    return (
        <section className="py-24 bg-black relative overflow-hidden" id="features">
            <div className="container mx-auto px-6">
                <div className="text-center mb-16">
                    <motion.h2
                        initial={{ opacity: 0, y: 20 }}
                        whileInView={{ opacity: 1, y: 0 }}
                        viewport={{ once: true }}
                        className="text-4xl font-bold mb-4"
                    >
                        Powerful Features for <span className="text-gradient">Modern Hiring</span>
                    </motion.h2>
                    <p className="text-gray-400 max-w-2xl mx-auto">
                        Everything you need to automate your technical screening and find the best talent faster.
                    </p>
                </div>

                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-8">
                    {features.map((feature, index) => (
                        <motion.div
                            key={index}
                            initial={{ opacity: 0, y: 20 }}
                            whileInView={{ opacity: 1, y: 0 }}
                            viewport={{ once: true }}
                            transition={{ delay: index * 0.1 }}
                            whileHover={{ y: -5, transition: { duration: 0.2 } }}
                            className="glass-card p-8 rounded-2xl hover:bg-white/10 transition-colors group relative"
                        >
                            <div className="absolute inset-0 bg-gradient-to-br from-blue-500/5 to-purple-500/5 opacity-0 group-hover:opacity-100 transition-opacity rounded-2xl" />
                            <div className="w-12 h-12 bg-white/5 rounded-xl flex items-center justify-center mb-6 group-hover:scale-110 transition-transform">
                                {feature.icon}
                            </div>
                            <h3 className="text-xl font-semibold mb-3">{feature.title}</h3>
                            <p className="text-gray-400 leading-relaxed text-sm">
                                {feature.description}
                            </p>
                        </motion.div>
                    ))}
                </div>
            </div>
        </section>
    );
}
