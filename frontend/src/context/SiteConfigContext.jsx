// Runtime-editable site copy (brand name + landing page text), fetched
// from GET /api/site-config (backend/routers/site_config.py) rather than
// hardcoded, so an admin can change the landing page copy from
// AdminSiteContent.jsx without a code deploy. Falls back to the constants
// below until the request resolves (or if it fails).
import { createContext, useContext, useEffect, useState, useCallback } from "react";
import { api } from "@/lib/api";

// Fallback constants — used only until the /api/site-config response lands
// (or if it fails outright). Kept intentionally sparse so nothing important
// stays baked into the bundle.
const FALLBACK_BRAND = "Rohini's Academy for Bio Exams";
const FALLBACK_LANDING = {
  hero_badge: "New Batches Open",
  hero_heading: "Crack Exams with the most experienced faculties.",
  hero_subheading: "Live classes, structured courses, mock tests and personal mentorship for CSIR-NET, GATE, IIT-JAM, and other Life Sciences entrance exams.",
  hero_cta_student: "Start learning free",
  hero_cta_teacher: "I'm a teacher",
  stat_1_number: "Self paced",
  stat_1_label: "Live classes",
  stat_2_number: "Personal",
  stat_2_label: "Attention",
  stat_3_number: "Past Questions",
  stat_3_label: "Covered",
  features_heading: "Everything a serious aspirant needs. Nothing they don't.",
  contact_eyebrow: "Get in touch",
  contact_heading: "Have a question? We'd love to hear from you.",
  contact_description: "Reach out about courses, batches, or personalised mentorship. Our team usually replies within one business day.",
  cta_heading: "Your entrance exam success is one decision away.",
  cta_description: "Join the new batch today. First course module is free.",
  cta_button: "Create free account",
  footer_tagline: "Built for entrance exam aspirants",
  teachers_menu_label: "Teachers Profile",
  contact_email: "contact@bioexamprep.com",
  contact_phone: "+91 9403888372",
  contact_website: "bioexamprep.com",
  next_class_empty_state: "No live classes scheduled yet",
};

const SiteConfigCtx = createContext({
  brand_name: FALLBACK_BRAND,
  landing: FALLBACK_LANDING,
  loading: true,
  refresh: async () => {},
});

export function SiteConfigProvider({ children }) {
  const [state, setState] = useState({
    brand_name: FALLBACK_BRAND,
    landing: FALLBACK_LANDING,
    loading: true,
  });

  const refresh = useCallback(async () => {
    try {
      const { data } = await api.get("/site-config");
      const landing = { ...FALLBACK_LANDING, ...(data.landing || {}) };
      setState({ brand_name: data.brand_name || FALLBACK_BRAND, landing, loading: false });
      // Keep tab title in sync
      if (typeof document !== "undefined" && data.brand_name) {
        document.title = `${data.brand_name} — Entrance Exam Coaching`;
      }
    } catch (_err) {
      setState((s) => ({ ...s, loading: false }));
    }
  }, []);

  useEffect(() => { refresh(); }, [refresh]);

  return (
    <SiteConfigCtx.Provider value={{ ...state, refresh }}>
      {children}
    </SiteConfigCtx.Provider>
  );
}

export function useSiteConfig() {
  return useContext(SiteConfigCtx);
}

export const LANDING_KEYS = Object.keys(FALLBACK_LANDING);
