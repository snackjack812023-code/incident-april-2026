// Postback data travels through LINE and comes back in the webhook. Treat it as untrusted input:
// it only identifies *what* was tapped; permissions are checked against the DB when handling it.

export type LeaveDecision = "approve" | "reject";

export type PostbackCommand = { action: "leave.decide"; leaveId: string; decision: LeaveDecision };

const UUID = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;

export function encodeLeaveDecision(leaveId: string, decision: LeaveDecision): string {
  return new URLSearchParams({ action: "leave.decide", id: leaveId, decision }).toString();
}

export function parsePostbackData(data: string): PostbackCommand | null {
  const params = new URLSearchParams(data);
  if (params.get("action") === "leave.decide") {
    const leaveId = params.get("id") ?? "";
    const decision = params.get("decision");
    if (UUID.test(leaveId) && (decision === "approve" || decision === "reject")) {
      return { action: "leave.decide", leaveId, decision };
    }
  }
  return null;
}
