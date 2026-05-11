import logger from "./logger";

export interface AuditEntry {
  userId: string;
  action: string;
  resource: string;
  timestamp: number;
  metadata?: Record<string, unknown>;
}

export interface AuditStore {
  write(entry: AuditEntry): Promise<void>;
}

export interface OrderRequest {
  userId: string;
  orderId: string;
  amount: number;
}

export interface OrderResult {
  orderId: string;
  status: "confirmed";
  chargedAmount: number;
}

export interface BillingClient {
  charge(userId: string, amount: number): Promise<{ chargedAmount: number }>;
}

async function saveAudit(store: AuditStore, entry: AuditEntry): Promise<void> {
  await store.write(entry);
}

async function processOrder(
  billing: BillingClient,
  req: OrderRequest,
): Promise<OrderResult> {
  const { chargedAmount } = await billing.charge(req.userId, req.amount);
  return {
    orderId: req.orderId,
    status: "confirmed",
    chargedAmount,
  };
}

export async function handleOrder(
  req: OrderRequest,
  deps: { audit: AuditStore; billing: BillingClient },
): Promise<OrderResult> {
  // Fire-and-forget audit log: must not block the response path.
  // Explicit `void` + `.catch` satisfies js-floating-promise — rejection is
  // routed to the logger instead of becoming an unhandled-rejection event.
  void saveAudit(deps.audit, {
    userId: req.userId,
    action: "order.create",
    resource: req.orderId,
    timestamp: Date.now(),
    metadata: { amount: req.amount },
  }).catch((err: unknown) => {
    logger.error(
      { err: err instanceof Error ? err.message : String(err), orderId: req.orderId },
      "audit log write failed",
    );
  });

  // Business logic runs on the response path and surfaces errors to the caller.
  return await processOrder(deps.billing, req);
}
