import type { ReactNode } from "react";
import type { Metadata } from "next";

export const metadata: Metadata = {
  title: "Create Video — PDF2Video Studio",
  description: "Upload a PDF or text content and generate a cinematic video with AI.",
};

export default function CreateLayout({ children }: { children: ReactNode }) {
  return <>{children}</>;
}
