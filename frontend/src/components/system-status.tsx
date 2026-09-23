"use client";

import { useEffect, useState } from "react";

import { getHealth } from "@/components/system-status-client";

type Status = "checking" | "online" | "offline";

type SystemStatusProps = {
  labels: Record<Status, string> & { hint: string };
};

export function SystemStatus({ labels }: SystemStatusProps) {
  const [status, setStatus] = useState<Status>("checking");

  useEffect(() => {
    const controller = new AbortController();

    void getHealth(controller.signal)
      .then(() => setStatus("online"))
      .catch(() => {
        if (!controller.signal.aborted) setStatus("offline");
      });

    return () => controller.abort();
  }, []);

  return (
    <div className="statusCard" aria-live="polite">
      <span className={`statusDot statusDot--${status}`} aria-hidden="true" />
      <div>
        <strong>{labels[status]}</strong>
        {status === "offline" ? <p>{labels.hint}</p> : null}
      </div>
    </div>
  );
}
