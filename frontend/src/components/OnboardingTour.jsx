// SPDX-License-Identifier: MIT
// Copyright (c) 2026 ScholarForm AI

'use client';

import React, { useState, useEffect } from 'react';
import { motion } from 'framer-motion';
import { useAuth } from '@/context/AuthContext';
import { X, ChevronRight } from 'lucide-react';

const TOUR_STEPS = [
  {
    target: 'body',
    title: 'Welcome to ScholarForm AI! 🚀',
    content: 'Let\'s take a quick tour to help you get started with formatting your academic documents.',
    position: 'center'
  },
  {
    target: '#upload-zone',
    title: 'Easy Upload',
    content: 'Drag and drop your manuscript here to start the formatting process. We support DOCX and PDF.',
    position: 'bottom'
  },
  {
    target: '.template-selector-trigger',
    title: 'Choose Your Template',
    content: 'Select from 1000+ journal-specific templates like IEEE, APA, Nature, and more.',
    position: 'right'
  },
  {
    target: '#nav-history',
    title: 'Document History',
    content: 'Access all your previously formatted documents and their validation results here.',
    position: 'right'
  },
  {
    target: '#mode-generator',
    title: 'AI Generator',
    content: 'Switch to Generator mode to have AI write or rewrite entire sections of your manuscript.',
    position: 'bottom'
  }
];

export default function OnboardingTour() {
  const { isLoggedIn } = useAuth();
  const [currentStep, setCurrentStep] = useState(0);
  const [isVisible, setIsVisible] = useState(false);
  const [targetRect, setTargetRect] = useState(null);

  useEffect(() => {
    // Only show for logged in users who haven't completed onboarding
    const isCompleted = localStorage.getItem('onboarding_completed');
    if (isLoggedIn && !isCompleted) {
      setIsVisible(true);
    }
  }, [isLoggedIn]);

  useEffect(() => {
    if (!isVisible) return;

    const updateRect = () => {
      const step = TOUR_STEPS[currentStep];
      if (step.target === 'body') {
        setTargetRect({ 
          top: window.innerHeight / 2, 
          left: window.innerWidth / 2, 
          width: 0, 
          height: 0, 
          isCenter: true 
        });
        return;
      }

      const el = document.querySelector(step.target);
      if (el) {
        setTargetRect(el.getBoundingClientRect());
        el.scrollIntoView({ behavior: 'smooth', block: 'center' });
      }
    };

    updateRect();
    window.addEventListener('resize', updateRect);
    return () => window.removeEventListener('resize', updateRect);
  }, [currentStep, isVisible]);

  const handleNext = () => {
    if (currentStep < TOUR_STEPS.length - 1) {
      setCurrentStep(curr => curr + 1);
    } else {
      completeTour();
    }
  };

  const handleBack = () => {
    if (currentStep > 0) {
      setCurrentStep(curr => curr - 1);
    }
  };

  const completeTour = () => {
    setIsVisible(false);
    localStorage.setItem('onboarding_completed', 'true');
  };

  if (!isVisible || !targetRect) return null;

  const currentTourStep = TOUR_STEPS[currentStep];

  return (
    <div className="fixed inset-0 z-[9999] pointer-events-none">
      {/* Dimmer Overlay */}
      <motion.div 
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        exit={{ opacity: 0 }}
        className="absolute inset-0 bg-slate-900/40 backdrop-blur-[2px] pointer-events-auto"
        onClick={completeTour}
      />

      {/* Spotlight Effect */}
      {!targetRect.isCenter && (
        <motion.div
          animate={{
            x: targetRect.left - 8,
            y: targetRect.top - 8,
            width: targetRect.width + 16,
            height: targetRect.height + 16,
          }}
          transition={{ type: 'spring', damping: 25, stiffness: 200 }}
          className="absolute border-2 border-primary shadow-[0_0_0_9999px_rgba(15,23,42,0.6)] rounded-lg pointer-events-none z-10"
        />
      )}

      {/* Tooltip Content */}
      <motion.div
        layout
        initial={{ opacity: 0, scale: 0.9, y: 20 }}
        animate={{ 
          opacity: 1, 
          scale: 1, 
          y: 0,
          left: targetRect.isCenter ? '50%' : Math.min(Math.max(16, targetRect.left), window.innerWidth - 400),
          top: targetRect.isCenter ? '50%' : (targetRect.top + targetRect.height > window.innerHeight - 200 ? targetRect.top - 200 : targetRect.top + targetRect.height + 20),
          translateX: targetRect.isCenter ? '-50%' : 0,
          translateY: targetRect.isCenter ? '-50%' : 0,
        }}
        transition={{ type: 'spring', damping: 20, stiffness: 150 }}
        className="absolute pointer-events-auto w-[calc(100vw-32px)] sm:w-full sm:max-w-full max-w-[380px] bg-white dark:bg-slate-900 shadow-2xl rounded-2xl border border-slate-200 dark:border-slate-800 p-6 z-20"
        style={{
          left: targetRect.isCenter ? '50%' : '16px',
          right: '16px',
          margin: '0 auto',
          maxWidth: '380px'
        }}
      >
        <div className="flex justify-between items-start mb-4">
          <h3 className="text-lg font-bold text-slate-900 dark:text-white leading-tight">
            {currentTourStep.title}
          </h3>
          <button 
            onClick={completeTour}
            className="p-1 hover:bg-slate-100 dark:hover:bg-white/10 rounded-lg text-slate-400"
          >
            <X size={18} />
          </button>
        </div>

        <p className="text-[15px] text-slate-600 dark:text-slate-400 mb-6 leading-relaxed">
          {currentTourStep.content}
        </p>

        <div className="flex items-center justify-between mt-auto">
          <div className="flex gap-1.5">
            {TOUR_STEPS.map((_, idx) => (
              <div 
                key={idx}
                className={`h-1.5 rounded-full transition-all duration-300 ${
                  idx === currentStep ? 'w-4 bg-primary' : 'w-1.5 bg-slate-200 dark:bg-slate-800 outline outline-1 outline-slate-300 dark:outline-slate-700'
                }`}
              />
            ))}
          </div>

          <div className="flex items-center gap-3">
            {currentStep > 0 && (
              <button
                onClick={handleBack}
                className="text-sm font-semibold text-slate-500 hover:text-slate-900 dark:hover:text-white transition-colors"
              >
                Back
              </button>
            )}
            <button
              onClick={handleNext}
              className="px-4 py-2 bg-primary hover:bg-primary-hover text-white rounded-xl text-sm font-bold shadow-lg shadow-primary/20 transition-all flex items-center gap-1.5"
            >
              {currentStep === TOUR_STEPS.length - 1 ? 'Finish' : 'Next'}
              <ChevronRight size={16} />
            </button>
          </div>
        </div>
      </motion.div>
    </div>
  );
}
