// SPDX-License-Identifier: MIT
// Copyright (c) 2026 ScholarForm AI

import React, { useCallback, useState, useEffect } from 'react';
import { Edit2, Trash2, Plus, GripVertical, Check, X, RefreshCw, ArrowRight } from 'lucide-react';
import { motion, Reorder } from 'framer-motion';

const OutlineApproval = React.memo(({ outline, onApprove, onEdit, onRegenerate }) => {
  const [sections, setSections] = useState([]);
  const [editingId, setEditingId] = useState(null);
  const [editTitle, setEditTitle] = useState("");
  const [editWordCount, setEditWordCount] = useState("");

  const buildOutline = useCallback((nextSections) => ({
    ...(outline || {}),
    sections: nextSections.map((s, index) => ({
      number: index + 1,
      sectionNumber: index + 1,
      title: s.title,
      expectedWordCount: s.expectedWordCount
    }))
  }), [outline]);

  useEffect(() => {
    if (outline && outline.sections) {
      const incomingSections = outline.sections.map((s, index) => ({
        id: `section-${Date.now()}-${index}`,
        title: s.title || s.section || `Section ${index + 1}`,
        expectedWordCount: s.expectedWordCount || s.wordCount || 0
      }));
      const signature = (list) => list.map(item => `${item.title}:${item.expectedWordCount}`).join('|');
      if (signature(incomingSections) !== signature(sections)) {
        // Intialize with unique IDs for drag and drop
        setSections(incomingSections);
      }
    }
  }, [outline, sections]);

  const handleEditClick = (section) => {
    setEditingId(section.id);
    setEditTitle(section.title);
    setEditWordCount(section.expectedWordCount.toString());
  };

  const handleSaveEdit = useCallback((id) => {
    const nextSections = sections.map(s => 
      s.id === id 
        ? { ...s, title: editTitle, expectedWordCount: parseInt(editWordCount, 10) || 0 }
        : s
    );
    setSections(nextSections);
    if (onEdit) {
      onEdit(buildOutline(nextSections));
    }
    setEditingId(null);
  }, [sections, editTitle, editWordCount, onEdit, buildOutline]);

  const handleCancelEdit = () => {
    setEditingId(null);
  };

  const handleDelete = (id) => {
    const nextSections = sections.filter(s => s.id !== id);
    setSections(nextSections);
    if (onEdit) {
      onEdit(buildOutline(nextSections));
    }
  };

  const handleAddSection = () => {
    const newSection = {
      id: `section-${Date.now()}`,
      title: "New Section",
      expectedWordCount: 500
    };
    const nextSections = [...sections, newSection];
    setSections(nextSections);
    if (onEdit) {
      onEdit(buildOutline(nextSections));
    }
    // Automatically enter edit mode for the new section
    setEditingId(newSection.id);
    setEditTitle(newSection.title);
    setEditWordCount("500");
  };

  const handleApprove = useCallback(() => {
    const cleanOutline = buildOutline(sections);
    onApprove(cleanOutline);
  }, [buildOutline, sections, onApprove]);

  const handleRegenerate = () => {
    if (onRegenerate) {
      onRegenerate();
      return;
    }
    if (onEdit) {
      onEdit(buildOutline(sections));
    }
  };

  useEffect(() => {
    const handleKeyDown = (event) => {
      const isMod = event.ctrlKey || event.metaKey;
      if (!isMod) return;

      const key = event.key.toLowerCase();
      if (key === 's' && editingId) {
        event.preventDefault();
        handleSaveEdit(editingId);
        return;
      }

      if (event.key === 'Enter') {
        event.preventDefault();
        if (editingId) {
          handleSaveEdit(editingId);
        } else {
          handleApprove();
        }
      }
    };

    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [editingId, handleApprove, handleSaveEdit]);

  return (
    <div className="flex flex-col h-full bg-white dark:bg-zinc-900 border border-zinc-200 dark:border-zinc-800 rounded-xl overflow-hidden shadow-sm">
      <div className="p-4 border-b border-zinc-200 dark:border-zinc-800 bg-zinc-50 dark:bg-zinc-800/50">
        <h3 className="text-lg font-semibold text-zinc-900 dark:text-white flex items-center gap-2">
          <span className="flex-shrink-0 w-2 h-2 rounded-full bg-amber-500 animate-pulse"></span>
          Review Outline
        </h3>
        <p className="text-sm text-zinc-500 dark:text-zinc-400 mt-1">
          Review, edit, and reorganize the proposed document structure before generation begins.
        </p>
      </div>

      <div className="flex-1 overflow-y-auto p-4 custom-scrollbar">
        <Reorder.Group 
          axis="y" 
          values={sections} 
          onReorder={(nextSections) => {
            setSections(nextSections);
            if (onEdit) {
              onEdit(buildOutline(nextSections));
            }
          }} 
          className="space-y-3"
        >
          {sections.map((section, index) => (
            <Reorder.Item key={section.id} value={section} id={section.id}>
              <motion.div 
                layout
                initial={{ opacity: 0, y: 10 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0, scale: 0.95 }}
                className={`group relative flex items-center gap-3 p-3 rounded-lg border ${
                  editingId === section.id 
                    ? 'border-indigo-500 ring-1 ring-indigo-500 bg-indigo-50/50 dark:bg-indigo-500/10' 
                    : 'border-zinc-200 dark:border-zinc-800 bg-white dark:bg-zinc-900 hover:border-zinc-300 dark:hover:border-zinc-700'
                } transition-colors`}
              >
                
                {/* Drag Handle */}
                <div className="cursor-grab active:cursor-grabbing text-zinc-400 hover:text-zinc-600 dark:hover:text-zinc-300 transition-colors p-1">
                  <GripVertical className="w-4 h-4" />
                </div>

                {/* Number Badge */}
                <div className="flex items-center justify-center w-6 h-6 rounded-full bg-zinc-100 dark:bg-zinc-800 text-xs font-medium text-zinc-600 dark:text-zinc-400">
                  {index + 1}
                </div>

                {/* Content */}
                <div className="flex-1 min-w-0">
                  {editingId === section.id ? (
                    <div className="flex flex-col gap-2">
                      <input
                        type="text"
                        value={editTitle}
                        onChange={(e) => setEditTitle(e.target.value)}
                        className="w-full px-2 py-1 text-sm bg-white dark:bg-zinc-950 border border-zinc-300 dark:border-zinc-700 rounded focus:outline-none focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500 text-zinc-900 dark:text-zinc-100"
                        placeholder="Section Title"
                        autoFocus
                      />
                      <div className="flex items-center gap-2">
                        <span className="text-xs text-zinc-500 dark:text-zinc-400">Words:</span>
                        <input
                          type="number"
                          value={editWordCount}
                          onChange={(e) => setEditWordCount(e.target.value)}
                          className="w-20 px-2 py-1 text-xs bg-white dark:bg-zinc-950 border border-zinc-300 dark:border-zinc-700 rounded focus:outline-none focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500 text-zinc-900 dark:text-zinc-100"
                          placeholder="Counts"
                        />
                      </div>
                    </div>
                  ) : (
                    <div className="flex flex-col">
                      <span className="text-sm font-medium text-zinc-900 dark:text-zinc-100 truncate">
                        {section.title}
                      </span>
                      <span className="text-xs text-zinc-500 dark:text-zinc-400">
                        ~{section.expectedWordCount} words
                      </span>
                    </div>
                  )}
                </div>

                {/* Actions */}
                <div className="flex items-center gap-1 opacity-0 group-hover:opacity-100 focus-within:opacity-100 transition-opacity">
                  {editingId === section.id ? (
                    <>
                      <button 
                        onClick={() => handleSaveEdit(section.id)}
                        className="p-1.5 text-green-600 hover:bg-green-50 dark:hover:bg-green-500/10 rounded-md transition-colors"
                        title="Save (Ctrl+S or Ctrl+Enter)"
                      >
                        <Check className="w-4 h-4" />
                      </button>
                      <button 
                        onClick={handleCancelEdit}
                        className="p-1.5 text-zinc-500 hover:bg-zinc-100 dark:hover:bg-zinc-800 rounded-md transition-colors"
                        title="Cancel"
                      >
                        <X className="w-4 h-4" />
                      </button>
                    </>
                  ) : (
                    <>
                      <button 
                        onClick={() => handleEditClick(section)}
                        className="p-1.5 text-zinc-500 hover:text-indigo-600 hover:bg-indigo-50 dark:hover:text-indigo-400 dark:hover:bg-indigo-500/10 rounded-md transition-colors"
                        title="Edit Section"
                      >
                        <Edit2 className="w-4 h-4" />
                      </button>
                      <button 
                        onClick={() => handleDelete(section.id)}
                        className="p-1.5 text-zinc-500 hover:text-red-600 hover:bg-red-50 dark:hover:text-red-400 dark:hover:bg-red-500/10 rounded-md transition-colors"
                        title="Delete Section"
                      >
                        <Trash2 className="w-4 h-4" />
                      </button>
                    </>
                  )}
                </div>

              </motion.div>
            </Reorder.Item>
          ))}
        </Reorder.Group>

        <button
          onClick={handleAddSection}
          className="mt-4 w-full flex items-center justify-center gap-2 py-3 border-2 border-dashed border-zinc-200 dark:border-zinc-800 rounded-lg text-sm font-medium text-zinc-500 dark:text-zinc-400 hover:text-zinc-900 dark:hover:text-zinc-100 hover:border-zinc-300 dark:hover:border-zinc-700 hover:bg-zinc-50 dark:hover:bg-zinc-800/50 transition-all"
        >
          <Plus className="w-4 h-4" />
          Add Section
        </button>
      </div>

      <div className="p-4 border-t border-zinc-200 dark:border-zinc-800 bg-zinc-50 dark:bg-zinc-800/50 flex flex-col sm:flex-row gap-3">
        <button
          onClick={handleRegenerate}
          className="flex-1 flex items-center justify-center gap-2 px-4 py-2.5 bg-white dark:bg-zinc-900 border border-zinc-300 dark:border-zinc-700 rounded-lg text-sm font-medium text-zinc-700 dark:text-zinc-300 hover:bg-zinc-50 dark:hover:bg-zinc-800 transition-colors shadow-sm"
        >
          <RefreshCw className="w-4 h-4" />
          Regenerate Outline
        </button>
        <button
          onClick={handleApprove}
          className="flex-1 flex items-center justify-center gap-2 px-4 py-2.5 bg-indigo-600 hover:bg-indigo-700 text-white rounded-lg text-sm font-medium transition-colors shadow-sm"
          title="Proceed (Ctrl+Enter)"
        >
          Proceed to Write
          <ArrowRight className="w-4 h-4" />
        </button>
      </div>
    </div>
  );
});

OutlineApproval.displayName = 'OutlineApproval';

export default OutlineApproval;
