import type { webhook } from "@line/bot-sdk";
import type { DB } from "@/db/types";
import { findEmployeeByLineUserId, type CurrentEmployee } from "../services/employees";
import { decideLeave, STATUS_LABELS } from "../services/leaves";
import { liffUrl } from "../urls";
import { employeeMenuMessage, registerPromptMessage } from "./flex";
import type { LineMessage, LineMessenger } from "./messenger";
import { parsePostbackData, type PostbackCommand } from "./postback";

export type WebhookDeps = { db: DB; line: LineMessenger };

const MENU_KEYWORDS = /^(เมนู|menu|ขอลา|ลา|เช็คอิน|เช็คชื่อ|ลงทะเบียน)$/i;

/** Handles each event independently: one failing event never blocks the rest of the batch. */
export async function handleWebhookEvents(deps: WebhookDeps, events: webhook.Event[]): Promise<void> {
  for (const event of events) {
    try {
      await handleEvent(deps, event);
    } catch (err) {
      console.error(`[webhook] ${event.type} event failed`, err);
    }
  }
}

async function handleEvent(deps: WebhookDeps, event: webhook.Event): Promise<void> {
  const userId = event.source?.userId;
  switch (event.type) {
    case "follow": {
      if (!userId) return;
      await deps.line.reply(event.replyToken, [await menuFor(deps, userId)]);
      return;
    }
    case "message": {
      // Only answer explicit menu keywords in 1:1 chats, so the bot never spams group chats.
      if (event.source?.type !== "user" || !userId || !event.replyToken) return;
      if (event.message.type !== "text" || !MENU_KEYWORDS.test(event.message.text.trim())) return;
      await deps.line.reply(event.replyToken, [await menuFor(deps, userId)]);
      return;
    }
    case "postback": {
      const command = parsePostbackData(event.postback.data);
      if (!command || !userId) return;
      const reply = await runCommand(deps, userId, command);
      if (event.replyToken) await deps.line.reply(event.replyToken, [reply]);
      return;
    }
    default:
      return;
  }
}

async function menuFor(deps: WebhookDeps, userId: string): Promise<LineMessage> {
  const employee = await findEmployeeByLineUserId(deps.db, userId);
  if (!employee || !employee.active) return registerPromptMessage({ registerUrl: liffUrl("/register") });
  return employeeMenuMessage({
    name: employee.name,
    leaveUrl: liffUrl("/leave"),
    checkinUrl: liffUrl("/checkin"),
    homeUrl: liffUrl("/"),
  });
}

function text(value: string): LineMessage {
  return { type: "text", text: value };
}

async function runCommand(deps: WebhookDeps, userId: string, command: PostbackCommand): Promise<LineMessage> {
  const actor: CurrentEmployee | null = await findEmployeeByLineUserId(deps.db, userId);
  if (!actor || !actor.active) return text("บัญชี LINE นี้ยังไม่ได้ลงทะเบียนกับระบบ");

  const result = await decideLeave(deps, actor, { leaveId: command.leaveId, decision: command.decision });
  if (result.ok) {
    const verb = command.decision === "approve" ? "✅ อนุมัติ" : "❌ ปฏิเสธ";
    return text(`${verb}คำขอลาของ ${result.leave.employeeName} เรียบร้อยแล้ว`);
  }
  switch (result.code) {
    case "forbidden":
      return text("คุณไม่มีสิทธิ์อนุมัติคำขอลา");
    case "not_found":
      return text("ไม่พบคำขอลานี้ (อาจถูกลบไปแล้ว)");
    case "own_request":
      return text("ไม่สามารถอนุมัติคำขอลาของตัวเองได้");
    case "already_decided": {
      const leave = result.leave;
      const by = leave?.deciderName ? ` โดย ${leave.deciderName}` : "";
      return text(`คำขอนี้ถูกดำเนินการไปแล้ว: ${leave ? STATUS_LABELS[leave.status] : ""}${by}`);
    }
  }
}
