export function processWebhook(payload: any): any {
  const event_type: any = payload?.event_type;
  const user_id: any = payload?.user_id;
  const data: any = payload?.data;

  return {
    event_type,
    user_id,
    data,
  };
}
