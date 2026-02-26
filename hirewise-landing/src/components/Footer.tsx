"use client";

import { Github, Twitter, Linkedin, Mail } from "lucide-react";

export default function Footer() {
    return (
        <footer className="py-20 bg-black border-t border-white/5">
            <div className="container mx-auto px-6">
                <div className="grid grid-cols-1 md:grid-cols-4 gap-12 mb-16">
                    <div className="col-span-1 md:col-span-2">
                        <div className="flex items-center gap-2 mb-6">
                            <img src="/logo.png" alt="HireWise Logo" className="h-10 w-auto" />
                        </div>
                        <p className="text-gray-500 max-w-sm leading-relaxed">
                            Automating technical screening with intelligent AI evaluation and proctoring. Build your dream team, faster.
                        </p>
                    </div>

                    <div>
                        <h4 className="font-bold mb-6">Quick Links</h4>
                        <ul className="space-y-4 text-gray-500 text-sm">
                            <li><a href="#features" className="hover:text-blue-500 transition-colors">Features</a></li>
                            <li><a href="#how-it-works" className="hover:text-blue-500 transition-colors">How it works</a></li>
                            <li><a href="#testimonials" className="hover:text-blue-500 transition-colors">Testimonials</a></li>
                            <li><a href="/login" className="hover:text-blue-500 transition-colors">Dashboard Login</a></li>
                        </ul>
                    </div>

                    <div>
                        <h4 className="font-bold mb-6">Connect</h4>
                        <div className="flex gap-4">
                            <a href="#" className="w-10 h-10 rounded-full bg-white/5 flex items-center justify-center hover:bg-white/10 transition-colors">
                                <Github className="w-5 h-5" />
                            </a>
                            <a href="#" className="w-10 h-10 rounded-full bg-white/5 flex items-center justify-center hover:bg-white/10 transition-colors">
                                <Twitter className="w-5 h-5" />
                            </a>
                            <a href="#" className="w-10 h-10 rounded-full bg-white/5 flex items-center justify-center hover:bg-white/10 transition-colors">
                                <Linkedin className="w-5 h-5" />
                            </a>
                            <a href="mailto:hello@hirewise.ai" className="w-10 h-10 rounded-full bg-white/5 flex items-center justify-center hover:bg-white/10 transition-colors">
                                <Mail className="w-5 h-5" />
                            </a>
                        </div>
                    </div>
                </div>

                <div className="pt-8 border-t border-white/5 flex flex-col md:flex-row justify-between items-center gap-4 text-gray-600 text-xs">
                    <div>© 2026 HireWise AI. All rights reserved.</div>
                    <div className="flex gap-8">
                        <a href="#" className="hover:text-white transition-colors">Privacy Policy</a>
                        <a href="#" className="hover:text-white transition-colors">Terms of Service</a>
                    </div>
                </div>
            </div>
        </footer>
    );
}
