"use client";

import React, { createContext, useContext, useState, useCallback } from "react";
import { AnimatePresence, motion } from "framer-motion";
import { CheckCircle2, AlertCircle, Info, X } from "lucide-react";
import { cn } from "@/lib/utils";

interface Toast {
  id: string;
  message: string;
  type?: "success" | "error" | "info";
  duration?: number;
}

interface ToastContextType {
  toast: (message: string, type?: "success" | "error" | "info") => void;
}

const ToastContext = createContext<ToastContextType>({
  toast: () => {},
});

export function useToast() {
  return useContext(ToastContext);
}

export function ToastProvider({ children }: { children: React.ReactNode }) {
  const [toasts, setToasts] = useState<Toast[]>([]);

  const addToast = useCallback(
    (message: string, type: "success" | "error" | "info" = "info") => {
      const id = Math.random().toString(36).substring(2, 9);
      setToasts((prev) => [...prev, { id, message, type }]);

      setTimeout(() => {
        setToasts((prev) => prev.filter((t) => t.id !== id));
      }, 4000);
    },
    []
  );

  const removeToast = (id: string) => {
    setToasts((prev) => prev.filter((t) => t.id !== id));
  };

  return (
    <ToastContext.Provider value={{ toast: addToast }}>
      {children}
      <div className="fixed bottom-5 right-5 z-50 flex flex-col gap-2 max-w-sm w-full pointer-events-none">
        <AnimatePresence>
          {toasts.map((t) => (
            <motion.div
              key={t.id}
              initial={{ opacity: 0, y: 15, scale: 0.95 }}
              animate={{ opacity: 1, y: 0, scale: 1 }}
              exit={{ opacity: 0, y: 10, scale: 0.95 }}
              transition={{ duration: 0.18, ease: "easeOut" }}
              className={cn(
                "pointer-events-auto flex items-start gap-3 p-3.5 rounded-lg border shadow-xl bg-surface-2 text-text-primary text-xs",
                t.type === "success" && "border-semantic-green/40",
                t.type === "error" && "border-semantic-red/40",
                t.type === "info" && "border-accent/40"
              )}
            >
              {t.type === "success" && (
                <CheckCircle2 className="w-4 h-4 text-semantic-green shrink-0 mt-0.5" />
              )}
              {t.type === "error" && (
                <AlertCircle className="w-4 h-4 text-semantic-red shrink-0 mt-0.5" />
              )}
              {t.type === "info" && (
                <Info className="w-4 h-4 text-accent shrink-0 mt-0.5" />
              )}
              <div className="flex-1 font-medium leading-relaxed">{t.message}</div>
              <button
                onClick={() => removeToast(t.id)}
                className="text-text-tertiary hover:text-text-primary shrink-0 ml-1"
              >
                <X className="w-3.5 h-3.5" />
              </button>
            </motion.div>
          ))}
        </AnimatePresence>
      </div>
    </ToastContext.Provider>
  );
}
