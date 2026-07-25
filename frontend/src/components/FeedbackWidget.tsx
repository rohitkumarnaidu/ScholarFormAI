"use client";

import { useState } from "react";
import * as Dialog from "@radix-ui/react-dialog";
import { MessageSquare, Star, X, Loader2 } from "lucide-react";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { toast } from "sonner";
import { submitFeedback } from "@/lib/issue-api";

const categories = [
  { value: "general", label: "General Feedback" },
  { value: "bug", label: "Bug Report" },
  { value: "feature", label: "Feature Request" },
  { value: "ux", label: "UX Feedback" },
  { value: "performance", label: "Performance" },
];

const schema = z.object({
  message: z.string().min(1, "Message is required").max(2000, "Message too long"),
  category: z.string().default("general"),
  rating: z.number().min(1).max(5).default(0),
  reporter_name: z.string().optional(),
  reporter_email: z.string().email("Invalid email").optional().or(z.literal("")),
  anonymous: z.boolean().default(false),
});

type FormData = z.infer<typeof schema>;

export default function FeedbackWidget() {
  const [open, setOpen] = useState(false);
  const [submitting, setSubmitting] = useState(false);

  const {
    register,
    handleSubmit,
    watch,
    setValue,
    reset,
    formState: { errors },
  } = useForm<FormData>({
    resolver: zodResolver(schema) as any,
    defaultValues: { message: "", category: "general", rating: 0, anonymous: false },
  });

  const rating = watch("rating");
  const anonymous = watch("anonymous");

  const onSubmit = async (data: FormData) => {
    setSubmitting(true);
    try {
      await submitFeedback({
        message: data.message,
        category: data.category,
        rating: data.rating || undefined,
        reporter_name: data.anonymous ? undefined : data.reporter_name || undefined,
        reporter_email: data.anonymous ? undefined : data.reporter_email || undefined,
        title: data.category === "bug" ? "Bug: " + data.message.slice(0, 80) : undefined,
      });
      toast.success("Feedback submitted! Thank you.");
      reset();
      setOpen(false);
    } catch {
      toast.error("Failed to submit feedback. Please try again.");
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <Dialog.Root open={open} onOpenChange={setOpen}>
      <Dialog.Trigger asChild>
        <button
          aria-label="Send feedback"
          className="fixed bottom-6 left-6 z-40 flex h-12 w-12 items-center justify-center rounded-full bg-slate-800 text-white shadow-lg transition-all hover:bg-slate-700 hover:shadow-xl"
        >
          <MessageSquare className="h-5 w-5" />
        </button>
      </Dialog.Trigger>

      <Dialog.Portal>
        <Dialog.Overlay className="fixed inset-0 z-50 bg-black/40 data-[state=open]:animate-in data-[state=closed]:animate-out" />
        <Dialog.Content className="fixed left-1/2 top-1/2 z-50 max-h-[85vh] w-full max-w-md -translate-x-1/2 -translate-y-1/2 rounded-xl border border-gray-200 bg-white p-6 shadow-2xl data-[state=open]:animate-in data-[state=closed]:animate-out">
          <Dialog.Close className="absolute right-4 top-4 text-gray-400 hover:text-gray-600">
            <X className="h-4 w-4" />
          </Dialog.Close>

          <Dialog.Title className="text-lg font-semibold text-gray-900">
            Send Feedback
          </Dialog.Title>
          <Dialog.Description className="mt-1 text-sm text-gray-500">
            Help us improve AMF with your feedback.
          </Dialog.Description>

          <form onSubmit={handleSubmit(onSubmit)} className="mt-5 space-y-4">
            <div>
              <label className="block text-sm font-medium text-gray-700">Rating</label>
              <div className="mt-1 flex gap-1">
                {[1, 2, 3, 4, 5].map((star) => (
                  <button
                    key={star}
                    type="button"
                    onClick={() => setValue("rating", star, { shouldValidate: true })}
                    className="p-0.5 transition-colors"
                  >
                    <Star
                      className={`h-6 w-6 ${
                        star <= rating ? "fill-amber-400 text-amber-400" : "text-gray-300"
                      }`}
                    />
                  </button>
                ))}
              </div>
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700">Category</label>
              <select
                {...register("category")}
                className="mt-1 w-full rounded-lg border border-gray-300 px-3 py-2 text-sm"
              >
                {categories.map((c) => (
                  <option key={c.value} value={c.value}>{c.label}</option>
                ))}
              </select>
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700">Message</label>
              <textarea
                {...register("message")}
                rows={4}
                placeholder="Tell us what you think..."
                className="mt-1 w-full rounded-lg border border-gray-300 px-3 py-2 text-sm resize-none"
              />
              {errors.message && (
                <p className="mt-1 text-xs text-red-600">{errors.message.message}</p>
              )}
            </div>

            {!anonymous && (
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-sm font-medium text-gray-700">Name (optional)</label>
                  <input
                    {...register("reporter_name")}
                    placeholder="Your name"
                    className="mt-1 w-full rounded-lg border border-gray-300 px-3 py-2 text-sm"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700">Email (optional)</label>
                  <input
                    {...register("reporter_email")}
                    placeholder="email@example.com"
                    className="mt-1 w-full rounded-lg border border-gray-300 px-3 py-2 text-sm"
                  />
                  {errors.reporter_email && (
                    <p className="mt-1 text-xs text-red-600">{errors.reporter_email.message}</p>
                  )}
                </div>
              </div>
            )}

            <label className="flex items-center gap-2 cursor-pointer">
              <input
                type="checkbox"
                {...register("anonymous")}
                className="rounded border-gray-300 text-blue-600 focus:ring-blue-500"
              />
              <span className="text-sm text-gray-700">Submit anonymously</span>
            </label>

            <button
              type="submit"
              disabled={submitting}
              className="inline-flex w-full items-center justify-center gap-2 rounded-lg bg-blue-600 px-4 py-2.5 text-sm font-medium text-white hover:bg-blue-700 disabled:opacity-50 transition-colors"
            >
              {submitting && <Loader2 className="h-4 w-4 animate-spin" />}
              {submitting ? "Submitting..." : "Submit Feedback"}
            </button>
          </form>
        </Dialog.Content>
      </Dialog.Portal>
    </Dialog.Root>
  );
}
