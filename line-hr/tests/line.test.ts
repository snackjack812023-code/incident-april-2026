import type { messagingApi } from "@line/bot-sdk";
import { describe, expect, it } from "vitest";
import { leaveDecisionMessage, newLeaveRequestMessage, FLEX_COLORS } from "@/lib/line/flex";
import { encodeLeaveDecision, parsePostbackData } from "@/lib/line/postback";
import { signLineBody, verifyLineSignature } from "@/lib/line/signature";

const LEAVE_ID = "3f1c2b9e-1d2a-4c3b-9a8e-7f6d5c4b3a21";

describe("webhook signature", () => {
  const secret = "test-channel-secret";
  const body = JSON.stringify({ destination: "U1", events: [{ type: "follow", text: "สวัสดี" }] });

  it("accepts the correct signature and rejects tampering", () => {
    const signature = signLineBody(body, secret);
    expect(verifyLineSignature(body, signature, secret)).toBe(true);
    expect(verifyLineSignature(body + " ", signature, secret)).toBe(false);
    expect(verifyLineSignature(body, signature, "other-secret")).toBe(false);
    expect(verifyLineSignature(body, "", secret)).toBe(false);
    expect(verifyLineSignature(body, "not-base64!!", secret)).toBe(false);
  });
});

describe("postback data", () => {
  it("round-trips leave decisions", () => {
    const data = encodeLeaveDecision(LEAVE_ID, "approve");
    expect(data.length).toBeLessThanOrEqual(300);
    expect(parsePostbackData(data)).toEqual({ action: "leave.decide", leaveId: LEAVE_ID, decision: "approve" });
  });

  it("rejects malformed data", () => {
    expect(parsePostbackData("action=leave.decide&id=123&decision=approve")).toBeNull();
    expect(parsePostbackData(`action=leave.decide&id=${LEAVE_ID}&decision=delete`)).toBeNull();
    expect(parsePostbackData("hello")).toBeNull();
  });
});

describe("flex messages", () => {
  const info = {
    id: LEAVE_ID,
    employeeName: "สมหญิง ใจดี",
    leaveTypeName: "ลาพักร้อน",
    startDate: "2026-11-20",
    endDate: "2026-11-22",
    period: "full" as const,
    days: 1,
    reason: "",
  };

  it("builds the new-request card with approve / reject postbacks", () => {
    const msg = newLeaveRequestMessage(info, { reviewUrl: "https://example.com/admin/leaves" });
    const bubble = msg.contents as messagingApi.FlexBubble;
    expect(msg.altText).toContain("สมหญิง ใจดี");
    expect(bubble.header?.backgroundColor).toBe(FLEX_COLORS.pending);

    const json = JSON.stringify(msg);
    expect(json).toContain(encodeLeaveDecision(LEAVE_ID, "approve"));
    expect(json).toContain(encodeLeaveDecision(LEAVE_ID, "reject"));
    expect(json).toContain("20–22 พ.ย. 2569");
    // Flex rejects empty text, so an empty reason must render as "-".
    expect(json).not.toContain('"text":""');
  });

  it("omits the link button when there is no app URL", () => {
    const msg = newLeaveRequestMessage(info, { reviewUrl: null });
    expect(JSON.stringify(msg)).not.toContain('"type":"uri"');
  });

  it("colors decisions green / red", () => {
    const approved = leaveDecisionMessage({ ...info, status: "approved", deciderName: "แอดมิน", note: null }, { detailsUrl: null });
    const rejected = leaveDecisionMessage({ ...info, status: "rejected", deciderName: "แอดมิน", note: "ช่วงนั้นคนไม่พอ" }, { detailsUrl: null });
    expect((approved.contents as messagingApi.FlexBubble).header?.backgroundColor).toBe(FLEX_COLORS.approved);
    expect((rejected.contents as messagingApi.FlexBubble).header?.backgroundColor).toBe(FLEX_COLORS.rejected);
    expect(JSON.stringify(rejected)).toContain("ช่วงนั้นคนไม่พอ");
  });
});
