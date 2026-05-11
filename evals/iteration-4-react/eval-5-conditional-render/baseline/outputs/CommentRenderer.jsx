import React from 'react';

export default function CommentRenderer({ comment }) {
  if (!comment) {
    return null;
  }

  const { author, createdAt, html } = comment;

  return (
    <article className="comment">
      <header className="comment__header">
        {author && <span className="comment__author">{author}</span>}
        {createdAt && (
          <time className="comment__timestamp" dateTime={createdAt}>
            {new Date(createdAt).toLocaleString()}
          </time>
        )}
      </header>
      <div
        className="comment__body"
        dangerouslySetInnerHTML={{ __html: html }}
      />
    </article>
  );
}
