import { useEffect, useState, useCallback } from "react";
import { api, formatApiError } from "@/lib/api";
import { toast } from "sonner";
import { MessageSquare, MessageSquareOff, Reply, Trash2, Send } from "lucide-react";
import dayjs from "dayjs";
import { useAuth } from "@/context/AuthContext";

/**
 * Reusable threaded comments.
 * @param baseUrl e.g. `/lessons/{cid}/{stid}/{lid}/comments` or `/recordings/{cid}/comments`
 *                 (POST + GET both use this; DELETE uses `/comments/{id}`)
 * @param canToggle if true, teacher sees the enable/disable toggle
 * @param onToggle async fn(enabled) — called when teacher flips the switch
 * @param canModerate if true, this user can delete any comment (teacher of the course / admin)
 */
export default function CommentsThread({ baseUrl, canToggle = false, onToggle, canModerate = false }) {
  const { user } = useAuth();
  const [state, setState] = useState({ enabled: true, comments: [] });
  const [loading, setLoading] = useState(true);
  const [text, setText] = useState("");
  const [replyingTo, setReplyingTo] = useState(null);
  const [replyText, setReplyText] = useState("");

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const { data } = await api.get(baseUrl);
      setState(data);
    } catch (err) {
      toast.error(formatApiError(err));
    } finally {
      setLoading(false);
    }
  }, [baseUrl]);
  useEffect(() => { load(); }, [load]);

  const post = async (body, parent_id = null) => {
    if (!body.trim()) return;
    try {
      await api.post(baseUrl, { body, parent_id });
      setText(""); setReplyText(""); setReplyingTo(null);
      load();
    } catch (err) { toast.error(formatApiError(err)); }
  };

  const remove = async (id) => {
    if (!window.confirm("Delete this comment and any replies?")) return;
    try {
      await api.delete(`/comments/${id}`);
      toast.success("Comment deleted");
      load();
    } catch (err) { toast.error(formatApiError(err)); }
  };

  const toggleEnabled = async () => {
    if (!onToggle) return;
    try {
      await onToggle(!state.enabled);
      load();
    } catch (err) { toast.error(formatApiError(err)); }
  };

  const roots = state.comments.filter((c) => !c.parent_id);
  const repliesFor = (id) => state.comments.filter((c) => c.parent_id === id);

  return (
    <div className="border border-zinc-200" data-testid="comments-thread">
      <div className="px-4 py-3 border-b border-zinc-200 bg-zinc-50 flex items-center gap-2">
        <MessageSquare className="w-4 h-4 text-blue-700" />
        <h3 className="font-heading font-bold text-sm">Discussion {state.enabled ? `(${state.comments.length})` : ""}</h3>
        {canToggle && (
          <button onClick={toggleEnabled} data-testid="comments-toggle-button" className={`ml-auto inline-flex items-center gap-1 text-xs font-semibold px-2.5 py-1 border ${state.enabled ? "border-blue-200 text-blue-700 bg-white" : "border-zinc-300 text-zinc-500 bg-white"}`}>
            {state.enabled ? <><MessageSquare className="w-3 h-3" /> Enabled</> : <><MessageSquareOff className="w-3 h-3" /> Disabled</>}
          </button>
        )}
      </div>

      {!state.enabled ? (
        <p className="px-4 py-6 text-sm text-zinc-500 text-center" data-testid="comments-disabled">Discussion is disabled by the teacher for this content.</p>
      ) : (
        <>
          <div className="px-4 py-3 border-b border-zinc-100">
            <div className="flex gap-2">
              <textarea
                data-testid="comment-input"
                value={text}
                onChange={(e) => setText(e.target.value)}
                placeholder="Ask a question or share your thoughts…"
                rows={2}
                className="flex-1 border border-zinc-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-700 resize-y"
              />
              <button
                onClick={() => post(text)}
                disabled={!text.trim()}
                data-testid="comment-post-button"
                className="self-end inline-flex items-center gap-1 px-4 py-2 text-sm font-semibold bg-blue-700 text-white hover:bg-blue-900 disabled:opacity-40"
              >
                <Send className="w-3.5 h-3.5" /> Post
              </button>
            </div>
          </div>

          {loading ? (
            <p className="px-4 py-6 text-xs text-zinc-500">Loading comments…</p>
          ) : roots.length === 0 ? (
            <p className="px-4 py-6 text-sm text-zinc-500 text-center" data-testid="comments-empty">Be the first to start the discussion.</p>
          ) : (
            <ul className="divide-y divide-zinc-100">
              {roots.map((c) => (
                <li key={c.id} className="px-4 py-3" data-testid={`comment-${c.id}`}>
                  <CommentRow
                    comment={c}
                    canDelete={c.author_id === user.id || canModerate}
                    onDelete={remove}
                    onReply={() => { setReplyingTo(c.id); setReplyText(""); }}
                  />
                  {replyingTo === c.id && (
                    <div className="mt-2 ml-8 flex gap-2">
                      <textarea
                        data-testid={`reply-input-${c.id}`}
                        autoFocus
                        value={replyText}
                        onChange={(e) => setReplyText(e.target.value)}
                        placeholder="Write a reply…"
                        rows={2}
                        className="flex-1 border border-zinc-300 px-3 py-1.5 text-sm resize-y"
                      />
                      <div className="flex flex-col gap-1">
                        <button onClick={() => post(replyText, c.id)} data-testid={`reply-post-${c.id}`} className="px-3 py-1.5 text-xs font-semibold bg-blue-700 text-white hover:bg-blue-900">Reply</button>
                        <button onClick={() => setReplyingTo(null)} className="px-3 py-1.5 text-xs font-semibold border border-zinc-300 text-zinc-500 hover:bg-zinc-100">Cancel</button>
                      </div>
                    </div>
                  )}
                  {repliesFor(c.id).length > 0 && (
                    <ul className="mt-3 ml-8 border-l border-zinc-200 pl-4 space-y-3">
                      {repliesFor(c.id).map((r) => (
                        <li key={r.id} data-testid={`reply-${r.id}`}>
                          <CommentRow
                            comment={r}
                            canDelete={r.author_id === user.id || canModerate}
                            onDelete={remove}
                          />
                        </li>
                      ))}
                    </ul>
                  )}
                </li>
              ))}
            </ul>
          )}
        </>
      )}
    </div>
  );
}

function CommentRow({ comment, canDelete, onDelete, onReply }) {
  const isTeacherOrAdmin = comment.author_role !== "student";
  return (
    <div>
      <div className="flex items-center gap-2 text-xs">
        <span className="font-semibold text-sm text-zinc-950">{comment.author_name}</span>
        {isTeacherOrAdmin && (
          <span className="text-[9px] uppercase tracking-[0.15em] font-bold bg-blue-700 text-white px-1.5 py-0.5">
            {comment.author_role === "admin" ? "Admin" : "Teacher"}
          </span>
        )}
        <span className="text-zinc-400">· {dayjs(comment.created_at).fromNow?.() || dayjs(comment.created_at).format("D MMM, h:mm A")}</span>
      </div>
      <p className="mt-1 text-sm text-zinc-700 whitespace-pre-wrap">{comment.body}</p>
      <div className="mt-1 flex gap-3 text-xs">
        {onReply && (
          <button onClick={onReply} data-testid={`reply-button-${comment.id}`} className="text-zinc-500 hover:text-blue-700 inline-flex items-center gap-1">
            <Reply className="w-3 h-3" /> Reply
          </button>
        )}
        {canDelete && (
          <button onClick={() => onDelete(comment.id)} data-testid={`delete-comment-${comment.id}`} className="text-zinc-500 hover:text-red-600 inline-flex items-center gap-1">
            <Trash2 className="w-3 h-3" /> Delete
          </button>
        )}
      </div>
    </div>
  );
}
