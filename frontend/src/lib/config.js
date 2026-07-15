// Fallback constants — only used if the runtime /api/site-config request fails.
// The real brand + contact info comes from db.site_settings via SiteConfigContext.
export const ACADEMY_NAME = process.env.REACT_APP_ACADEMY_NAME || "Rohini's Academy for Bio Exams";
