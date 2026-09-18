"use client";

import { useEffect, useRef, useState } from "react";
import { useRouter } from "next/navigation";
import { FileUpIcon, Trash2Icon } from "lucide-react";
import { toast } from "sonner";
import { deleteResume, searchResumes, uploadPdf } from "@/lib/api";
import type { ResumeSummary } from "@/lib/types";
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
  AlertDialogTrigger,
} from "@/components/ui/alert-dialog";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { ScrollArea } from "@/components/ui/scroll-area";
import {
  Sheet,
  SheetContent,
  SheetDescription,
  SheetHeader,
  SheetTitle,
} from "@/components/ui/sheet";

export function ResumeMenu({
  open,
  onOpenChange,
  fileName,
  currentId,
}: {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  fileName?: string;
  currentId?: string;
}) {
  const router = useRouter();
  const fileRef = useRef<HTMLInputElement>(null);
  const [busy, setBusy] = useState(false);
  const [query, setQuery] = useState("");
  const [results, setResults] = useState<ResumeSummary[]>([]);
  const [searchError, setSearchError] = useState("");

  useEffect(() => {
    if (!open) return;
    let cancelled = false;
    searchResumes(query)
      .then((items) => {
        if (!cancelled) {
          setResults(items);
          setSearchError("");
        }
      })
      .catch((err) => {
        if (!cancelled) {
          setSearchError(err instanceof Error ? err.message : "Search failed.");
        }
      });
    return () => {
      cancelled = true;
    };
  }, [open, query]);

  async function onFileChange(event: React.ChangeEvent<HTMLInputElement>) {
    const file = event.target.files?.[0];
    event.target.value = "";
    if (!file) return;

    setBusy(true);
    try {
      const resume = await uploadPdf(file);
      toast.success("Resume uploaded");
      onOpenChange(false);
      router.push(`/editor/${resume.id}`);
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "Upload failed.");
    } finally {
      setBusy(false);
    }
  }

  function openResume(id: string) {
    onOpenChange(false);
    router.push(`/editor/${id}`);
  }

  async function onDelete(item: ResumeSummary) {
    try {
      await deleteResume(item.id);
      setResults((items) => items.filter((entry) => entry.id !== item.id));
      toast.success("Resume deleted");
      if (item.id === currentId) {
        onOpenChange(false);
        router.push("/resumes");
      }
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "Delete failed.");
    }
  }

  return (
    <Sheet open={open} onOpenChange={onOpenChange}>
      <SheetContent side="left" className="w-80 p-0">
        <SheetHeader className="border-b">
          <SheetTitle>Resume editor</SheetTitle>
          <SheetDescription>
            {fileName || "Upload a PDF or search a saved note."}
          </SheetDescription>
        </SheetHeader>

        <div className="flex min-h-0 flex-1 flex-col gap-3 p-4">
          <input
            ref={fileRef}
            type="file"
            accept="application/pdf"
            className="hidden"
            disabled={busy}
            onChange={onFileChange}
          />
          <Button
            variant="outline"
            disabled={busy}
            onClick={() => fileRef.current?.click()}
          >
            <FileUpIcon />
            {busy ? "Converting…" : "Upload PDF"}
          </Button>

          <Input
            type="search"
            value={query}
            onChange={(event) => setQuery(event.target.value)}
            placeholder="Search by note"
            aria-label="Search saved resumes by note"
          />
          {searchError ? (
            <p className="text-sm text-destructive">{searchError}</p>
          ) : null}

          {results.length === 0 ? (
            <p className="text-sm text-muted-foreground">
              No saved resumes match
            </p>
          ) : (
            <ScrollArea className="h-[min(60vh,28rem)]">
              <ul className="flex flex-col gap-1 pr-3">
                {results.map((item, index) => (
                  <li
                    key={item.id || `${item.source_file}-${index}`}
                    className="animate-in fade-in slide-in-from-left-2 fill-mode-both"
                    style={{
                      animationDelay: `${Math.min(index, 12) * 24}ms`,
                    }}
                  >
                    <div className="flex items-center gap-1 rounded-lg hover:bg-muted">
                      <button
                        type="button"
                        className="min-w-0 flex-1 rounded-lg px-2 py-2 text-left"
                        onClick={() => openResume(item.id)}
                      >
                        <span className="block truncate text-sm font-medium">
                          {item.note || "No note"}
                        </span>
                        <span className="block truncate text-xs text-muted-foreground">
                          {item.source_file || "Untitled"}
                        </span>
                      </button>
                      <AlertDialog>
                        <AlertDialogTrigger
                          render={
                            <Button
                              variant="ghost"
                              size="icon-sm"
                              aria-label={`Delete ${item.note || item.source_file}`}
                            />
                          }
                        >
                          <Trash2Icon />
                        </AlertDialogTrigger>
                        <AlertDialogContent>
                          <AlertDialogHeader>
                            <AlertDialogTitle>Delete resume?</AlertDialogTitle>
                            <AlertDialogDescription>
                              Delete {item.note || item.source_file || "this resume"}?
                              This cannot be undone.
                            </AlertDialogDescription>
                          </AlertDialogHeader>
                          <AlertDialogFooter>
                            <AlertDialogCancel>Cancel</AlertDialogCancel>
                            <AlertDialogAction
                              variant="destructive"
                              onClick={() => void onDelete(item)}
                            >
                              Delete
                            </AlertDialogAction>
                          </AlertDialogFooter>
                        </AlertDialogContent>
                      </AlertDialog>
                    </div>
                  </li>
                ))}
              </ul>
            </ScrollArea>
          )}
        </div>
      </SheetContent>
    </Sheet>
  );
}
