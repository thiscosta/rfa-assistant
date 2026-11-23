"use client";

import { useEffect, useState } from "react";
import { api, type ClinicProfile } from "@/lib/api";

const EMPTY: ClinicProfile = {
  facility_name: "",
  tax_id: "",
  phone: "",
  fax: "",
  address: "",
  providers: [],
  default_provider_index: null,
};

export default function SettingsPage() {
  const [profile, setProfile] = useState<ClinicProfile | null>(null);
  const [status, setStatus] = useState<string | null>(null);

  useEffect(() => {
    api.clinic().then(setProfile).catch((e) => setStatus(e.message));
  }, []);

  if (!profile) return <p className="text-sm text-slate-500">{status ?? "Loading…"}</p>;

  const set = (patch: Partial<ClinicProfile>) => setProfile({ ...profile, ...patch });
  const setProvider = (i: number, key: "name" | "npi" | "license_number", value: string) =>
    set({ providers: profile.providers.map((p, j) => (j === i ? { ...p, [key]: value } : p)) });

  async function save(e: React.FormEvent) {
    e.preventDefault();
    try {
      const providers = profile!.providers.filter((p) => p.name.trim());
      const idx = profile!.default_provider_index;
      await api.saveClinic({
        ...profile!,
        providers,
        default_provider_index: idx !== null && idx < providers.length ? idx : null,
      });
      setStatus("Saved. Open requests were updated.");
    } catch (err) {
      setStatus((err as Error).message);
    }
  }

  const facility: [keyof ClinicProfile, string][] = [
    ["facility_name", "Facility / practice name"],
    ["tax_id", "Tax ID"],
    ["phone", "Phone"],
    ["fax", "Fax"],
    ["address", "Address"],
  ];

  return (
    <form onSubmit={save} className="mx-auto max-w-3xl space-y-6">
      <div>
        <h1 className="text-xl font-semibold text-slate-900">Clinic settings</h1>
        <p className="mt-1 text-sm text-slate-600">
          Section B of the form is about your clinic, which patient documents rarely contain. Enter it once here and every
          request uses it.
        </p>
      </div>

      <section className="card grid gap-4 p-4 sm:grid-cols-2">
        {facility.map(([key, label]) => (
          <label key={key} className={`text-sm ${key === "address" || key === "facility_name" ? "sm:col-span-2" : ""}`}>
            <span className="mb-1 block font-medium text-slate-700">{label}</span>
            <input className="input" value={profile[key] as string} onChange={(e) => set({ [key]: e.target.value })} />
          </label>
        ))}
      </section>

      <section className="card space-y-3 p-4">
        <div>
          <h2 className="font-medium text-slate-900">Providers</h2>
          <p className="text-xs text-slate-500">
            When a clinical note names one of these providers (by NPI or last name), that provider becomes the requesting
            provider. Otherwise the default is used.
          </p>
        </div>
        {profile.providers.length === 0 && <p className="text-sm text-slate-500">No providers yet.</p>}
        {profile.providers.map((p, i) => (
          <div key={i} className="grid items-end gap-2 sm:grid-cols-[2fr_1fr_1fr_auto_auto]">
            <label className="text-xs">
              <span className="mb-1 block text-slate-600">Name as printed</span>
              <input className="input" placeholder="Dr. First Last, PsyD" value={p.name} onChange={(e) => setProvider(i, "name", e.target.value)} />
            </label>
            <label className="text-xs">
              <span className="mb-1 block text-slate-600">NPI</span>
              <input className="input" value={p.npi} onChange={(e) => setProvider(i, "npi", e.target.value)} />
            </label>
            <label className="text-xs">
              <span className="mb-1 block text-slate-600">License #</span>
              <input className="input" value={p.license_number} onChange={(e) => setProvider(i, "license_number", e.target.value)} />
            </label>
            <label className="flex items-center gap-1.5 pb-2 text-xs text-slate-600">
              <input
                type="radio"
                name="default"
                checked={profile.default_provider_index === i}
                onChange={() => set({ default_provider_index: i })}
              />
              Default
            </label>
            <button
              type="button"
              className="btn-ghost text-xs"
              onClick={() =>
                set({
                  providers: profile.providers.filter((_, j) => j !== i),
                  default_provider_index:
                    profile.default_provider_index === i
                      ? null
                      : profile.default_provider_index !== null && profile.default_provider_index > i
                        ? profile.default_provider_index - 1
                        : profile.default_provider_index,
                })
              }
            >
              Remove
            </button>
          </div>
        ))}
        <button
          type="button"
          className="btn-secondary"
          onClick={() => set({ providers: [...profile.providers, { name: "", npi: "", license_number: "" }] })}
        >
          Add provider
        </button>
      </section>

      <div className="flex items-center gap-3">
        <button className="btn-primary">Save settings</button>
        <button type="button" className="btn-ghost" onClick={() => setProfile(EMPTY)}>
          Clear
        </button>
        {status && <span className="text-sm text-slate-600">{status}</span>}
      </div>
    </form>
  );
}
