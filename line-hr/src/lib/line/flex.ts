// Flex Message builders. Preview any of these by pasting the JSON into
// https://developers.line.biz/flex-simulator/
import type { messagingApi } from "@line/bot-sdk";
import { formatThaiDateRange } from "../dates";
import { formatLeaveDays, type LeavePeriod } from "../leave-rules";
import { encodeLeaveDecision } from "./postback";

type FlexBox = messagingApi.FlexBox;
type FlexBubble = messagingApi.FlexBubble;
type FlexComponent = messagingApi.FlexComponent;
type FlexMessage = messagingApi.FlexMessage;
type FlexButton = messagingApi.FlexButton;

export const FLEX_COLORS = {
  pending: "#F97316",
  approved: "#16A34A",
  rejected: "#DC2626",
  info: "#0F766E",
  lineGreen: "#06C755",
  label: "#8A8A8A",
  text: "#1F2937",
} as const;

export type LeaveCardInfo = {
  id: string;
  employeeName: string;
  leaveTypeName: string;
  startDate: string;
  endDate: string;
  period: LeavePeriod;
  days: number;
  reason: string | null;
};

function clip(value: string, max: number): string {
  return value.length > max ? `${value.slice(0, max - 1)}…` : value;
}

function header(title: string, subtitle: string | null, color: string): FlexBox {
  const contents: FlexComponent[] = [{ type: "text", text: title, color: "#FFFFFF", weight: "bold", size: "lg", wrap: true }];
  if (subtitle) contents.push({ type: "text", text: subtitle, color: "#FFFFFFD9", size: "xs", wrap: true });
  return { type: "box", layout: "vertical", backgroundColor: color, paddingAll: "16px", spacing: "xs", contents };
}

function detailRow(label: string, value: string): FlexBox {
  return {
    type: "box",
    layout: "baseline",
    spacing: "md",
    contents: [
      { type: "text", text: label, size: "sm", color: FLEX_COLORS.label, flex: 3 },
      { type: "text", text: value.trim() || "-", size: "sm", color: FLEX_COLORS.text, flex: 6, wrap: true },
    ],
  };
}

function uriButton(label: string, uri: string, style: FlexButton["style"] = "link"): FlexButton {
  return { type: "button", style, height: "sm", action: { type: "uri", label, uri } };
}

function bubble(head: FlexBox, rows: FlexComponent[], footer: FlexComponent[]): FlexBubble {
  return {
    type: "bubble",
    size: "kilo",
    header: head,
    body: { type: "box", layout: "vertical", spacing: "sm", paddingAll: "16px", contents: rows },
    ...(footer.length ? { footer: { type: "box", layout: "vertical", spacing: "sm", contents: footer } } : {}),
  };
}

function leaveRows(info: LeaveCardInfo): FlexComponent[] {
  return [
    detailRow("พนักงาน", info.employeeName),
    detailRow("ประเภทการลา", info.leaveTypeName),
    detailRow("วันที่ลา", formatThaiDateRange(info.startDate, info.endDate)),
    detailRow("รวม", formatLeaveDays(info.days, info.period)),
    detailRow("เหตุผล", clip(info.reason ?? "", 300)),
  ];
}

/** Sent to managers/admins: orange card with approve / reject postback buttons. */
export function newLeaveRequestMessage(info: LeaveCardInfo, opts: { reviewUrl: string | null }): FlexMessage {
  const name = clip(info.employeeName, 60);
  const footer: FlexComponent[] = [
    {
      type: "box",
      layout: "horizontal",
      spacing: "sm",
      contents: [
        {
          type: "button",
          style: "secondary",
          height: "sm",
          action: {
            type: "postback",
            label: "ปฏิเสธ",
            data: encodeLeaveDecision(info.id, "reject"),
            displayText: `ปฏิเสธคำขอลาของ ${name}`,
          },
        },
        {
          type: "button",
          style: "primary",
          color: FLEX_COLORS.lineGreen,
          height: "sm",
          action: {
            type: "postback",
            label: "อนุมัติ",
            data: encodeLeaveDecision(info.id, "approve"),
            displayText: `อนุมัติคำขอลาของ ${name}`,
          },
        },
      ],
    },
  ];
  if (opts.reviewUrl) footer.push(uriButton("ดูรายละเอียดในระบบ", opts.reviewUrl));

  return {
    type: "flex",
    altText: clip(
      `คำขอลาใหม่: ${info.employeeName} • ${info.leaveTypeName} • ${formatThaiDateRange(info.startDate, info.endDate)}`,
      400,
    ),
    contents: bubble(header("มีคำขอลาใหม่", "รอการอนุมัติ", FLEX_COLORS.pending), leaveRows(info), footer),
  };
}

/** Sent to the employee when their request is approved (green) or rejected (red). */
export function leaveDecisionMessage(
  info: LeaveCardInfo & { status: "approved" | "rejected"; deciderName: string; note: string | null },
  opts: { detailsUrl: string | null },
): FlexMessage {
  const approved = info.status === "approved";
  const title = approved ? "คำขอลาได้รับการอนุมัติ" : "คำขอลาถูกปฏิเสธ";
  const rows = leaveRows(info).slice(1); // the employee doesn't need their own name
  rows.push(detailRow("ผู้พิจารณา", info.deciderName));
  if (info.note) rows.push(detailRow("หมายเหตุ", clip(info.note, 300)));
  return {
    type: "flex",
    altText: `${title}: ${info.leaveTypeName} ${formatThaiDateRange(info.startDate, info.endDate)}`,
    contents: bubble(
      header(title, null, approved ? FLEX_COLORS.approved : FLEX_COLORS.rejected),
      rows,
      opts.detailsUrl ? [uriButton("ดูวันลาคงเหลือ", opts.detailsUrl)] : [],
    ),
  };
}

/** Reply for people who haven't linked their LINE account yet. */
export function registerPromptMessage(opts: { registerUrl: string | null }): messagingApi.Message {
  const text = "สวัสดีครับ 👋 เริ่มใช้งานระบบลงเวลาและขอลาได้ โดยลงทะเบียนด้วยรหัสเชิญที่ได้รับจากแอดมิน";
  if (!opts.registerUrl) return { type: "text", text };
  return {
    type: "flex",
    altText: "ลงทะเบียนพนักงาน",
    contents: bubble(
      header("ยินดีต้อนรับ", null, FLEX_COLORS.info),
      [{ type: "text", text, size: "sm", color: FLEX_COLORS.text, wrap: true }],
      [uriButton("ลงทะเบียน", opts.registerUrl, "primary")],
    ),
  };
}

/** Main menu for linked employees (reply to "เมนู" or a follow event). */
export function employeeMenuMessage(opts: {
  name: string;
  leaveUrl: string | null;
  checkinUrl: string | null;
  homeUrl: string | null;
}): messagingApi.Message {
  const buttons: FlexComponent[] = [];
  if (opts.checkinUrl) buttons.push(uriButton("เช็คชื่อ เข้า-ออก", opts.checkinUrl, "primary"));
  if (opts.leaveUrl) buttons.push(uriButton("ขอลา", opts.leaveUrl, "secondary"));
  if (opts.homeUrl) buttons.push(uriButton("ประวัติของฉัน", opts.homeUrl));
  const greeting = `สวัสดีคุณ${clip(opts.name, 40)} เลือกเมนูที่ต้องการได้เลย`;
  if (!buttons.length) return { type: "text", text: greeting };
  return {
    type: "flex",
    altText: "เมนูพนักงาน",
    contents: bubble(
      header("เมนูพนักงาน", null, FLEX_COLORS.info),
      [{ type: "text", text: greeting, size: "sm", color: FLEX_COLORS.text, wrap: true }],
      buttons,
    ),
  };
}
