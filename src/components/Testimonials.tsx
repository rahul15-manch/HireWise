"use client";

import { motion } from "framer-motion";

const testimonials = [
    {
        name: "Sarah Chen",
        role: "Head of Engineering at TechFlow",
        text: "HireWise has completely transformed how we hire. The AI analysis is spot on and saves our senior devs hours of screening time.",
        avatar: "S"
    },
    {
        name: "Marcus Rodriguez",
        role: "Technical Recruiter at Nexus AI",
        text: "The proctoring system is the best I've seen. It's subtle but effective, giving us full confidence in our remote technical assessments.",
        avatar: "M"
    },
    {
        name: "Jessica Wu",
        role: "VPE at ScaleReady",
        text: "Async interviews are a game changer for candidate experience. We've seen a 40% increase in candidate completion rates.",
        avatar: "J"
    }
];

export default function Testimonials() {
    return (
        <section className="py-24 bg-black" id="testimonials">
            <div className="container mx-auto px-6">
                <h2 className="text-4xl font-bold text-center mb-16">
                    Loved by <span className="text-gradient">Fast-Growing Teams</span>
                </h2>

                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-8">
                    {testimonials.map((t, index) => (
                        <motion.div
                            key={index}
                            initial={{ opacity: 0, scale: 0.95 }}
                            whileInView={{ opacity: 1, scale: 1 }}
                            viewport={{ once: true }}
                            transition={{ delay: index * 0.1 }}
                            className="glass-card p-8 rounded-3xl flex flex-col justify-between border-blue-500/10"
                        >
                            <p className="text-gray-300 italic mb-8">"{t.text}"</p>
                            <div className="flex items-center gap-4">
                                <div className="w-12 h-12 rounded-full bg-gradient-to-br from-blue-500 to-purple-600 flex items-center justify-center font-bold text-lg">
                                    {t.avatar}
                                </div>
                                <div>
                                    <div className="font-bold">{t.name}</div>
                                    <div className="text-gray-500 text-sm">{t.role}</div>
                                </div>
                            </div>
                        </motion.div>
                    ))}
                </div>
            </div>
        </section>
    );
}
