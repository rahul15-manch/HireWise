"use client";

import { motion } from "framer-motion";

const stats = [
    { label: "Interviews Automated", value: "10k+", suffix: "" },
    { label: "AI Accuracy", value: "99.8", suffix: "%" },
    { label: "Time Saved", value: "2,500", suffix: " hrs" },
    { label: "Recruiter Satisfaction", value: "98", suffix: "%" }
];

export default function Stats() {
    return (
        <section className="py-20 bg-black border-y border-white/5">
            <div className="container mx-auto px-6">
                <div className="grid grid-cols-2 lg:grid-cols-4 gap-12 lg:gap-8">
                    {stats.map((stat, index) => (
                        <motion.div
                            key={index}
                            initial={{ opacity: 0, scale: 0.5 }}
                            whileInView={{ opacity: 1, scale: 1 }}
                            viewport={{ once: true }}
                            transition={{ duration: 0.5, delay: index * 0.1 }}
                            className="text-center"
                        >
                            <div className="text-4xl lg:text-5xl font-bold text-white mb-2 font-mono">
                                {stat.value}{stat.suffix}
                            </div>
                            <div className="text-gray-500 text-sm uppercase tracking-widest font-semibold">
                                {stat.label}
                            </div>
                        </motion.div>
                    ))}
                </div>
            </div>
        </section>
    );
}
