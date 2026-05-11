import DOMPurify from "isomorphic-dompurify";

function CommentRenderer({ html }) {
  if (!html) {
    return <p className="comment comment--empty">No comment to display.</p>;
  }

  // Belt-and-suspenders: even though the backend claims to return sanitized
  // HTML, user-submitted content is a stored-XSS vector. Sanitize again on
  // the client before handing anything to dangerouslySetInnerHTML.
  const safe = DOMPurify.sanitize(html, {
    USE_PROFILES: { html: true },
    FORBID_TAGS: ["script", "style", "iframe", "object", "embed"],
    FORBID_ATTR: ["onerror", "onload", "onclick", "onmouseover"],
  });

  if (!safe.trim()) {
    return <p className="comment comment--empty">No comment to display.</p>;
  }

  return (
    <div
      className="comment"
      // aidoctor: disable=react-dangerous-html reason: sanitized via DOMPurify above (client-side defense in depth; backend also sanitizes)
      dangerouslySetInnerHTML={{ __html: safe }}
    />
  );
}

export default CommentRenderer;
