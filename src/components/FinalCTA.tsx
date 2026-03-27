"use client";

import { motion } from "framer-motion";
import { ArrowRight } from "lucide-react";

export default function FinalCTA() {
    return (
        <section className="py-24 relative overflow-hidden">
            <div className="absolute inset-0 bg-blue-600/20 blur-[120px] rounded-full scale-150 -z-10" />

            <div className="container mx-auto px-6">
                <motion.div
                    initial={{ opacity: 0, y: 20 }}
                    whileInView={{ opacity: 1, y: 0 }}
                    viewport={{ once: true }}
                    className="glass-card p-12 lg:p-20 rounded-[3rem] text-center relative overflow-hidden border-white/10"
                >
                    <div className="absolute top-0 left-0 w-full h-1 bg-gradient-to-r from-transparent via-blue-500 to-transparent" />

                    <h2 className="text-4xl lg:text-5xl font-bold mb-8 max-w-3xl mx-auto leading-tight">
                        Ready to Transform Your Hiring Process?
                    </h2>
                    <p className="text-gray-400 mb-12 text-lg lg:text-xl max-w-2xl mx-auto">
                        Join forward-thinking companies already using HireWise to find their next technical superstars.
                    </p>

                    <a href="http://localhost:8000/login" className="px-10 py-5 bg-white text-black font-bold rounded-full hover:bg-gray-200 transition-all flex items-center gap-2 mx-auto shadow-2xl shadow-white/10 group scale-110 no-underline w-fit">
                        Start Using HireWise
                        <ArrowRight className="w-5 h-5 group-hover:translate-x-1 transition-transform" />
                    </a>
                </motion.div>
            </div>
        </section>
    );
}
