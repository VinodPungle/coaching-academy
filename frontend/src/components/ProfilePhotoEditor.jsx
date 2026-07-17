import { useRef, useState } from "react";
import { Upload, Link2, Trash2, User } from "lucide-react";
import { toast } from "sonner";
import { uploadFile, fileUrl, formatApiError } from "@/lib/api";

/** Displays a photo, supports upload (jpg/png ≤ 5MB), URL paste, and remove.
 *  Calls `onChange(newUrl)` with the resolved URL. Pass empty string to indicate no photo. */
export default function ProfilePhotoEditor({ value, onChange, testidPrefix = "profile-photo" }) {
  const fileInput = useRef(null);
  const [uploading, setUploading] = useState(false);
  const [showUrl, setShowUrl] = useState(false);
  const [urlDraft, setUrlDraft] = useState("");

  const handleFile = async (file) => {
    if (!file) return;
    const okExt = /\.(png|jpe?g|webp)$/i.test(file.name);
    if (!okExt) return toast.error("Please choose a .jpg, .png or .webp image");
    if (file.size > 5 * 1024 * 1024) return toast.error("Image must be under 5 MB");
    setUploading(true);
    try {
      const res = await uploadFile(file);
      onChange(res.url); // /api/files/{id}
      toast.success("Photo uploaded");
    } catch (err) { toast.error(formatApiError(err)); }
    finally { setUploading(false); if (fileInput.current) fileInput.current.value = ""; }
  };

  const commitUrl = () => {
    const v = (urlDraft || "").trim();
    if (!v) return;
    if (!/^https?:\/\//i.test(v)) return toast.error("URL must start with http:// or https://");
    onChange(v);
    setShowUrl(false); setUrlDraft("");
    toast.success("Photo URL set");
  };

  const preview = value ? (value.startsWith("/api/files/") ? fileUrl(value) : value) : "";

  return (
    <div className="space-y-3" data-testid={`${testidPrefix}-editor`}>
      <div className="flex items-center gap-4">
        <div className="w-24 h-24 rounded-full bg-zinc-100 border border-zinc-200 overflow-hidden flex items-center justify-center shrink-0">
          {preview ? (
            <img src={preview} alt="Profile" className="w-full h-full object-cover" data-testid={`${testidPrefix}-preview`} />
          ) : (
            <User className="w-10 h-10 text-zinc-400" strokeWidth={1.5} data-testid={`${testidPrefix}-placeholder`} />
          )}
        </div>
        <div className="flex flex-wrap gap-2">
          <button
            type="button"
            data-testid={`${testidPrefix}-upload-button`}
            onClick={() => fileInput.current?.click()}
            disabled={uploading}
            className="inline-flex items-center gap-1.5 border border-zinc-300 px-3 py-2 text-xs font-semibold hover:bg-zinc-100 disabled:opacity-50"
          >
            <Upload className="w-3.5 h-3.5" /> {uploading ? "Uploading…" : "Upload photo"}
          </button>
          <input ref={fileInput} type="file" data-testid={`${testidPrefix}-file-input`} className="hidden" accept="image/png,image/jpeg,image/webp,.png,.jpg,.jpeg,.webp" onChange={(e) => handleFile(e.target.files?.[0])} />
          <button
            type="button"
            data-testid={`${testidPrefix}-url-button`}
            onClick={() => setShowUrl((s) => !s)}
            className="inline-flex items-center gap-1.5 border border-zinc-300 px-3 py-2 text-xs font-semibold hover:bg-zinc-100"
          >
            <Link2 className="w-3.5 h-3.5" /> Paste URL
          </button>
          {value && (
            <button
              type="button"
              data-testid={`${testidPrefix}-remove-button`}
              onClick={() => onChange("")}
              className="inline-flex items-center gap-1.5 border border-red-200 text-red-600 px-3 py-2 text-xs font-semibold hover:bg-red-50"
            >
              <Trash2 className="w-3.5 h-3.5" /> Remove
            </button>
          )}
        </div>
      </div>
      {showUrl && (
        <div className="flex gap-2">
          <input
            data-testid={`${testidPrefix}-url-input`}
            type="url"
            value={urlDraft}
            onChange={(e) => setUrlDraft(e.target.value)}
            placeholder="https://…"
            className="flex-1 border border-zinc-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-700"
          />
          <button
            type="button"
            data-testid={`${testidPrefix}-url-save`}
            onClick={commitUrl}
            className="px-3 py-2 bg-blue-700 text-white text-xs font-semibold hover:bg-blue-900"
          >
            Save
          </button>
        </div>
      )}
      <p className="text-xs text-zinc-400">JPG, PNG or WebP · max 5 MB · or paste an image URL</p>
    </div>
  );
}
