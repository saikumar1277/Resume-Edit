"use client";

import { useParams } from "next/navigation";
import { RequireAuth } from "@/components/require-auth";
import Editor from "./Editor";

export default function EditorPage() {
  const params = useParams<{ id: string }>();
  return (
    <RequireAuth>
      <Editor resumeId={params.id} />
    </RequireAuth>
  );
}
