"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { z } from "zod";
import { createTrip } from "@/lib/api";
import { cn } from "@/lib/cn";
import type { TripRequest } from "@/types/trip";

const schema = z.object({
  destination: z.string().min(2).max(120),
  start_date: z.string(),
  end_date: z.string(),
  travelers: z.coerce.number().int().min(1).max(12),
  budget_total_inr: z.coerce.number().int().min(1000).max(10_000_000),
  style: z.enum(["budget", "balanced", "luxury"]),
  pace: z.enum(["relaxed", "moderate", "packed"]),
  interests: z.string().max(300),
  dietary: z.string().optional(),
  accessibility: z.enum(["none", "wheelchair", "limited_walking"]),
  notes: z.string().max(500).optional(),
});

type FormErrors = Partial<Record<keyof z.infer<typeof schema>, string>>;

export function TripPlanner(): JSX.Element {
  const router = useRouter();
  const [errors, setErrors] = useState<FormErrors>({});
  const [submitting, setSubmitting] = useState(false);
  const [serverError, setServerError] = useState<string | null>(null);

  async function onSubmit(e: React.FormEvent<HTMLFormElement>): Promise<void> {
    e.preventDefault();
    setServerError(null);
    const fd = new FormData(e.currentTarget);
    const raw = Object.fromEntries(fd.entries());

    const parsed = schema.safeParse(raw);
    if (!parsed.success) {
      const errs: FormErrors = {};
      for (const issue of parsed.error.issues) {
        const k = issue.path[0] as keyof FormErrors;
        errs[k] = issue.message;
      }
      setErrors(errs);
      // Move keyboard focus to the first error so screen-reader users hear it.
      const firstKey = Object.keys(errs)[0];
      if (firstKey) {
        const el = document.getElementById(firstKey);
        el?.focus();
      }
      return;
    }
    setErrors({});

    const v = parsed.data;
    const req: TripRequest = {
      destination: v.destination,
      start_date: v.start_date,
      end_date: v.end_date,
      travelers: v.travelers,
      preferences: {
        style: v.style,
        pace: v.pace,
        interests: v.interests
          .split(",")
          .map((s) => s.trim())
          .filter(Boolean),
        dietary: v.dietary
          ? (v.dietary.split(",").map((s) => s.trim()) as TripRequest["preferences"]["dietary"])
          : [],
        languages: ["en"],
      },
      constraints: {
        budget_total_inr: v.budget_total_inr,
        max_daily_walking_km: 8,
        must_include: [],
        must_avoid: [],
        accessibility: v.accessibility,
      },
      notes: v.notes ?? "",
    };

    setSubmitting(true);
    try {
      const trip = await createTrip(req);
      router.push(`/trip/${trip.id}`);
    } catch (err) {
      setServerError((err as Error).message);
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <form onSubmit={onSubmit} noValidate aria-describedby="form-help">
      <p id="form-help" className="sr-only">
        Required fields marked with an asterisk. Errors will appear under each
        field if validation fails.
      </p>

      <Field id="destination" label="Destination" required error={errors.destination}>
        <input
          id="destination"
          name="destination"
          type="text"
          required
          autoComplete="off"
          aria-invalid={!!errors.destination}
          aria-describedby={errors.destination ? "destination-err" : undefined}
          className={inputCls}
        />
      </Field>

      <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
        <Field id="start_date" label="Start date" required error={errors.start_date}>
          <input
            id="start_date"
            name="start_date"
            type="date"
            required
            aria-invalid={!!errors.start_date}
            className={inputCls}
          />
        </Field>
        <Field id="end_date" label="End date" required error={errors.end_date}>
          <input
            id="end_date"
            name="end_date"
            type="date"
            required
            aria-invalid={!!errors.end_date}
            className={inputCls}
          />
        </Field>
      </div>

      <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
        <Field id="travelers" label="Travellers" required error={errors.travelers}>
          <input
            id="travelers"
            name="travelers"
            type="number"
            min={1}
            max={12}
            defaultValue={2}
            required
            aria-invalid={!!errors.travelers}
            className={inputCls}
          />
        </Field>
        <Field
          id="budget_total_inr"
          label="Total budget (INR)"
          required
          error={errors.budget_total_inr}
        >
          <input
            id="budget_total_inr"
            name="budget_total_inr"
            type="number"
            min={1000}
            step={500}
            required
            aria-invalid={!!errors.budget_total_inr}
            className={inputCls}
          />
        </Field>
      </div>

      <fieldset className="mt-6">
        <legend className="font-medium mb-2">Travel style</legend>
        <div role="radiogroup" aria-label="Travel style" className="flex flex-wrap gap-3">
          {(["budget", "balanced", "luxury"] as const).map((v) => (
            <label
              key={v}
              className="inline-flex items-center gap-2 cursor-pointer rounded border border-slate-300 px-3 py-2 has-[:focus]:ring-2 has-[:focus]:ring-accent"
            >
              <input
                type="radio"
                name="style"
                value={v}
                defaultChecked={v === "balanced"}
                className="accent-accent"
              />
              <span className="capitalize">{v}</span>
            </label>
          ))}
        </div>
      </fieldset>

      <fieldset className="mt-6">
        <legend className="font-medium mb-2">Pace</legend>
        <div role="radiogroup" aria-label="Pace" className="flex flex-wrap gap-3">
          {(["relaxed", "moderate", "packed"] as const).map((v) => (
            <label
              key={v}
              className="inline-flex items-center gap-2 cursor-pointer rounded border border-slate-300 px-3 py-2 has-[:focus]:ring-2 has-[:focus]:ring-accent"
            >
              <input
                type="radio"
                name="pace"
                value={v}
                defaultChecked={v === "moderate"}
                className="accent-accent"
              />
              <span className="capitalize">{v}</span>
            </label>
          ))}
        </div>
      </fieldset>

      <Field id="interests" label="Interests (comma-separated)" error={errors.interests}>
        <input
          id="interests"
          name="interests"
          type="text"
          placeholder="e.g. trekking, food, history"
          className={inputCls}
        />
      </Field>

      <Field id="dietary" label="Dietary needs (comma-separated)">
        <input
          id="dietary"
          name="dietary"
          type="text"
          placeholder="e.g. vegetarian"
          className={inputCls}
        />
      </Field>

      <Field id="accessibility" label="Accessibility">
        <select id="accessibility" name="accessibility" defaultValue="none" className={inputCls}>
          <option value="none">No special needs</option>
          <option value="limited_walking">Limited walking</option>
          <option value="wheelchair">Wheelchair-friendly only</option>
        </select>
      </Field>

      <Field id="notes" label="Notes (optional)" error={errors.notes}>
        <textarea
          id="notes"
          name="notes"
          rows={3}
          maxLength={500}
          placeholder="Anything else we should know?"
          className={inputCls}
        />
      </Field>

      {serverError && (
        <div role="alert" className="mt-4 rounded border border-danger bg-red-50 p-3 text-danger">
          {serverError}
        </div>
      )}

      <button
        type="submit"
        disabled={submitting}
        className={cn(
          "mt-6 inline-flex items-center justify-center rounded bg-accent px-5 py-2.5",
          "font-semibold text-white hover:bg-accentHover",
          "disabled:opacity-60 disabled:cursor-not-allowed",
          "focus-visible:outline-2 focus-visible:outline-offset-2",
        )}
        aria-busy={submitting}
      >
        {submitting ? "Planning…" : "Plan my trip"}
      </button>
    </form>
  );
}

const inputCls =
  "mt-1 block w-full rounded border border-slate-300 px-3 py-2 text-ink placeholder:text-slate-400 focus:border-accent focus:outline-none focus:ring-2 focus:ring-accent";

interface FieldProps {
  id: string;
  label: string;
  required?: boolean;
  error?: string | undefined;
  children: React.ReactNode;
}

function Field({ id, label, required, error, children }: FieldProps): JSX.Element {
  return (
    <div className="mt-4">
      <label htmlFor={id} className="block font-medium">
        {label}
        {required && (
          <span aria-hidden="true" className="text-danger">
            {" *"}
          </span>
        )}
      </label>
      {children}
      {error && (
        <p id={`${id}-err`} role="alert" className="mt-1 text-sm text-danger">
          {error}
        </p>
      )}
    </div>
  );
}
