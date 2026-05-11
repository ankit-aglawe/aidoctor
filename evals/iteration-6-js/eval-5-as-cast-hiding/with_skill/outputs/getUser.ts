import { z } from "zod";

const UserSchema = z.object({
  id: z.string(),
  email: z.string().email(),
  name: z.string(),
});

export type User = z.infer<typeof UserSchema>;

export function getUser(rawJson: string): User {
  let parsed: unknown;
  try {
    parsed = JSON.parse(rawJson);
  } catch (e) {
    throw new Error(
      `getUser: invalid JSON — ${e instanceof Error ? e.message : String(e)}`,
    );
  }

  const result = UserSchema.safeParse(parsed);
  if (!result.success) {
    throw new Error(`getUser: payload did not match User schema — ${result.error.message}`);
  }
  return result.data;
}
