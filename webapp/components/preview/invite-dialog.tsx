"use client";

import { useState } from "react";
import { Button } from "@/components/ui/button";

interface InviteDialogProps {
  isOpen: boolean;
  locale: string;
  onClose: () => void;
  onRedeemed: () => Promise<void>;
  showToast: (msg: string, type: "success" | "error" | "info") => void;
}

export function InviteDialog({
  isOpen,
  locale,
  onClose,
  onRedeemed,
  showToast,
}: InviteDialogProps) {
  const [inviteCode, setInviteCode] = useState("");
  const [redeemingInvite, setRedeemingInvite] = useState(false);

  if (!isOpen) return null;

  const handleRedeem = async () => {
    if (!inviteCode.trim()) return;
    setRedeemingInvite(true);
    try {
      const res = await fetch("/api/auth/redeem-invite-code", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ invite_code: inviteCode.trim() }),
      });
      const d = await res.json();
      if (!res.ok) throw new Error(d.error || "兑换失败");
      showToast(locale === "zh" ? "兑换成功！" : "Redeemed successfully!", "success");
      onClose();
      await onRedeemed();
    } catch (err) {
      showToast(err instanceof Error ? err.message : "兑换失败", "error");
    } finally {
      setRedeemingInvite(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
      <div className="absolute inset-0 bg-black/45 backdrop-blur-2xs" onClick={onClose} />
      <div className="relative w-full max-w-md rounded-sm border border-ink/20 bg-white p-5 shadow-2xl space-y-4">
        <h3 className="text-sm font-bold text-ink">
          {locale === "zh" ? "输入邀请码解锁额度" : "Enter Invitation Code"}
        </h3>
        <p className="text-xs text-ink-light">
          {locale === "zh"
            ? "体验免费额度已达上限，请输入专属邀请码兑换更多预览点数。"
            : "Free quota exhausted, please enter invite code to unlock more preview credits."}
        </p>
        <input
          value={inviteCode}
          onChange={(e) => setInviteCode(e.target.value)}
          placeholder={locale === "zh" ? "输入邀请码" : "Invitation Code"}
          className="w-full rounded-sm border border-ink/20 px-3 py-2 text-xs bg-white font-mono"
        />
        <div className="flex items-center justify-end gap-2">
          <Button variant="outline" size="sm" onClick={onClose}>
            {locale === "zh" ? "关闭" : "Close"}
          </Button>
          <Button
            size="sm"
            onClick={handleRedeem}
            disabled={redeemingInvite || !inviteCode.trim()}
          >
            {locale === "zh" ? "立即兑换" : "Redeem"}
          </Button>
        </div>
      </div>
    </div>
  );
}
