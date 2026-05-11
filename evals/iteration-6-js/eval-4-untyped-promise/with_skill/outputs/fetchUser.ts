import { z } from "zod";

const UserSchema = z.object({
  id: z.string(),
  email: z.string().email(),
  name: z.string(),
  createdAt: z.string().datetime(),
});

export type User = z.infer<typeof UserSchema>;

export class FetchUserError extends Error {
  name = "FetchUserError";
  constructor(message: string, readonly cause?: unknown) {
    super(message);
  }
}

export async function fetchUser(id: string): Promise<User> {
  if (typeof id !== "string" || id.length === 0) {
    throw new FetchUserError(`invalid user id: ${String(id)}`);
  }

  let response: Response;
  try {
    response = await fetch(`/api/users/${encodeURIComponent(id)}`, {
      headers: { Accept: "application/json" },
    });
  } catch (e) {
    throw new FetchUserError(
      `network error fetching user ${id}: ${e instanceof Error ? e.message : String(e)}`,
      e,
    );
  }

  if (!response.ok) {
    throw new FetchUserError(
      `failed to fetch user ${id}: ${response.status} ${response.statusText}`,
    );
  }

  let payload: unknown;
  try {
    payload = await response.json();
  } catch (e) {
    throw new FetchUserError(
      `invalid JSON for user ${id}: ${e instanceof Error ? e.message : String(e)}`,
      e,
    );
  }

  const parsed = UserSchema.safeParse(payload);
  if (!parsed.success) {
    throw new FetchUserError(
      `response shape mismatch for user ${id}: ${parsed.error.message}`,
      parsed.error,
    );
  }

  return parsed.data;
}
