import type { Request, Response, NextFunction } from "express";

interface AuditLogEntry {
  userId: string;
  action: string;
  resource: string;
  timestamp: Date;
  metadata?: Record<string, unknown>;
}

interface BusinessPayload {
  userId: string;
  action: string;
  resource: string;
  data?: Record<string, unknown>;
}

interface BusinessResult {
  ok: true;
  resource: string;
  processedAt: Date;
  data?: Record<string, unknown>;
}

async function saveAuditLog(entry: AuditLogEntry): Promise<void> {
  // Simulated persistence — replace with real DB / log sink.
  await new Promise<void>((resolve) => {
    setTimeout(() => {
      console.log("[audit]", JSON.stringify(entry));
      resolve();
    }, 10);
  });
}

async function runBusinessLogic(payload: BusinessPayload): Promise<BusinessResult> {
  // Simulated business work — replace with real logic.
  await new Promise<void>((resolve) => setTimeout(resolve, 5));
  return {
    ok: true,
    resource: payload.resource,
    processedAt: new Date(),
    data: payload.data,
  };
}

export async function handler(
  req: Request,
  res: Response,
  next: NextFunction,
): Promise<void> {
  try {
    const payload = req.body as BusinessPayload;

    // 1) Fire-and-forget audit log — do NOT await so the request isn't blocked.
    //    Attach a .catch so an audit failure can't become an unhandled rejection.
    saveAuditLog({
      userId: payload.userId,
      action: payload.action,
      resource: payload.resource,
      timestamp: new Date(),
      metadata: { ip: req.ip, userAgent: req.get("user-agent") },
    }).catch((err) => {
      console.error("[audit] failed to persist entry", err);
    });

    // 2) Run the business logic (this one we DO await).
    const result = await runBusinessLogic(payload);

    // 3) Return the result.
    res.status(200).json(result);
  } catch (err) {
    next(err);
  }
}
