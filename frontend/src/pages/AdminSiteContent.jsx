import { useEffect, useState } from "react";
import { toast } from "sonner";
import { Save } from "lucide-react";
import { api, formatApiError } from "@/lib/api";
import { useAuth } from "@/context/AuthContext";
import { useSiteConfig } from "@/context/SiteConfigContext";

const LANDING_FIELDS = [
  { key: "hero_badge", label: "Hero — Badge", type: "input" },
  { key: "hero_heading", label: "Hero — Heading", type: "textarea" },
  { key: "hero_subheading", label: "Hero — Subheading", type: "textarea" },
  { key: "hero_cta_student", label: "Hero — Student CTA button", type: "input" },
  { key: "hero_cta_teacher", label: "Hero — Teacher CTA button", type: "input" },
  { key: "stat_1_number", label: "Stat 1 — Number/Label (big)", type: "input" },
  { key: "stat_1_label", label: "Stat 1 — Sub-label", type: "input" },
  { key: "stat_2_number", label: "Stat 2 — Number/Label (big)", type: "input" },
  { key: "stat_2_label", label: "Stat 2 — Sub-label", type: "input" },
  { key: "stat_3_number", label: "Stat 3 — Number/Label (big)", type: "input" },
  { key: "stat_3_label", label: "Stat 3 — Sub-label", type: "input" },
  { key: "features_heading", label: "Features — Heading", type: "textarea" },
  { key: "contact_eyebrow", label: "Contact — Eyebrow", type: "input" },
  { key: "contact_heading", label: "Contact — Heading", type: "textarea" },
  { key: "contact_description", label: "Contact — Description", type: "textarea" },
  { key: "contact_email", label: "Contact — Email", type: "input" },
  { key: "contact_phone", label: "Contact — Phone", type: "input" },
  { key: "contact_website", label: "Contact — Website", type: "input" },
  { key: "cta_heading", label: "Bottom CTA — Heading", type: "textarea" },
  { key: "cta_description", label: "Bottom CTA — Description", type: "input" },
  { key: "cta_button", label: "Bottom CTA — Button text", type: "input" },
  { key: "footer_tagline", label: "Footer — Tagline", type: "input" },
  { key: "teachers_menu_label", label: "Teachers Menu Label", type: "input" },
  { key: "next_class_empty_state", label: "Next class — Empty state text", type: "input" },
];

export default function AdminSiteContent() {
  const { user } = useAuth();
  const { brand_name: currentBrand, landing: currentLanding, refresh } = useSiteConfig();
  const [brandName, setBrandName] = useState("");
  const [landing, setLanding] = useState({});
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    setBrandName(currentBrand || "");
    setLanding({ ...currentLanding });
  }, [currentBrand, currentLanding]);

  if (user?.role !== "admin") {
    return <p className="text-sm text-red-600" data-testid="site-content-forbidden">Admins only.</p>;
  }

  const save = async () => {
    setBusy(true);
    try {
      await api.put("/site-config", { brand_name: brandName, landing });
      await refresh();
      toast.success("Site content saved");
    } catch (err) { toast.error(formatApiError(err)); }
    finally { setBusy(false); }
  };

  return (
    <div className="space-y-6" data-testid="admin-site-content">
      <div>
        <h1 className="font-heading text-2xl sm:text-3xl font-black tracking-tight">Site content</h1>
        <p className="text-sm text-zinc-500 mt-1">Edit the brand name and every text block on the public landing page. Changes take effect immediately for all visitors — no redeploy needed.</p>
      </div>

      <section className="border border-zinc-200 p-5 md:p-6 space-y-4">
        <h2 className="font-heading text-lg font-bold">Brand</h2>
        <div>
          <label className="text-xs uppercase tracking-[0.15em] font-semibold text-zinc-500">Brand name (shown in header, footer, page title, emails)</label>
          <input
            data-testid="brand-name-input"
            value={brandName}
            maxLength={200}
            onChange={(e) => setBrandName(e.target.value)}
            className="mt-1.5 w-full border border-zinc-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-700"
          />
        </div>
      </section>

      <section className="border border-zinc-200 p-5 md:p-6 space-y-4">
        <h2 className="font-heading text-lg font-bold">Landing page copy</h2>
        {LANDING_FIELDS.map(({ key, label, type }) => (
          <div key={key}>
            <label className="text-xs uppercase tracking-[0.15em] font-semibold text-zinc-500">{label}</label>
            {type === "textarea" ? (
              <textarea
                data-testid={`landing-input-${key}`}
                value={landing[key] ?? ""}
                maxLength={5000}
                rows={2}
                onChange={(e) => setLanding((l) => ({ ...l, [key]: e.target.value }))}
                className="mt-1.5 w-full border border-zinc-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-700 resize-none"
              />
            ) : (
              <input
                data-testid={`landing-input-${key}`}
                value={landing[key] ?? ""}
                maxLength={5000}
                onChange={(e) => setLanding((l) => ({ ...l, [key]: e.target.value }))}
                className="mt-1.5 w-full border border-zinc-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-700"
              />
            )}
          </div>
        ))}
      </section>

      <div className="sticky bottom-0 -mx-4 md:-mx-8 px-4 md:px-8 py-4 bg-white/90 backdrop-blur border-t border-zinc-200">
        <button
          data-testid="site-content-save"
          onClick={save}
          disabled={busy}
          className="inline-flex items-center gap-2 px-5 py-2.5 bg-blue-700 text-white text-sm font-semibold hover:bg-blue-900 disabled:opacity-50"
        >
          <Save className="w-4 h-4" /> {busy ? "Saving…" : "Save changes"}
        </button>
      </div>
    </div>
  );
}
