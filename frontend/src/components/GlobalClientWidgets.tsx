"use client";

import dynamic from "next/dynamic";

const UpdateBanner = dynamic(() => import("@/components/UpdateBanner"), { ssr: false });
const FeedbackWidget = dynamic(() => import("@/components/FeedbackWidget"), { ssr: false });
const CrashScreen = dynamic(() => import("@/components/CrashScreen"), { ssr: false });

export function GlobalClientWidgets() {
  return (
    <>
      <UpdateBanner />
      <FeedbackWidget />
      <CrashScreen />
    </>
  );
}

export default GlobalClientWidgets;
