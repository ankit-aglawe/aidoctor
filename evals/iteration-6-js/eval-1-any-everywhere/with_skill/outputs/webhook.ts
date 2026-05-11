/**
 * Webhook payload processing.
 *
 * The incoming payload is untrusted (HTTP body, parsed JSON), so we type it as
 * `unknown` and narrow with a user-defined type guard. This forces every
 * access to be checked, avoids `any` at the public boundary, and surfaces
 * malformed payloads as a typed error rather than a silent `undefined`.
 */

export type WebhookEventType =
  | "user.created"
  | "user.updated"
  | "user.deleted"
  | "payment.succeeded"
  | "payment.failed";

export interface WebhookPayload {
  event_type: WebhookEventType;
  user_id: string;
  data: Record<string, unknown>;
}

export class InvalidWebhookPayloadError extends Error {
  name = "InvalidWebhookPayloadError";
  constructor(reason: string) {
    super(`invalid webhook payload: ${reason}`);
  }
}

const KNOWN_EVENT_TYPES: ReadonlySet<WebhookEventType> = new Set([
  "user.created",
  "user.updated",
  "user.deleted",
  "payment.succeeded",
  "payment.failed",
]);

function isWebhookEventType(value: unknown): value is WebhookEventType {
  return typeof value === "string" && KNOWN_EVENT_TYPES.has(value as WebhookEventType);
}

function isPlainObject(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}

/**
 * Parse and validate a webhook payload from an untrusted source.
 *
 * @throws {InvalidWebhookPayloadError} when the payload shape is wrong.
 */
export function processWebhookPayload(payload: unknown): WebhookPayload {
  if (!isPlainObject(payload)) {
    throw new InvalidWebhookPayloadError("payload must be an object");
  }

  const { event_type, user_id, data } = payload;

  if (!isWebhookEventType(event_type)) {
    throw new InvalidWebhookPayloadError(
      `event_type must be one of ${[...KNOWN_EVENT_TYPES].join(", ")}`,
    );
  }

  if (typeof user_id !== "string" || user_id.length === 0) {
    throw new InvalidWebhookPayloadError("user_id must be a non-empty string");
  }

  if (!isPlainObject(data)) {
    throw new InvalidWebhookPayloadError("data must be an object");
  }

  return { event_type, user_id, data };
}
