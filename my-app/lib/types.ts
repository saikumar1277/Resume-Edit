export type Run = {
  text: string;
  font: string;
  size_pt: number;
  color_hex: string;
  bold: boolean;
  italic: boolean;
  underline?: boolean;
};

export type ParagraphAlign = "left" | "center" | "right";

export type ParagraphBlock = {
  id: string;
  type: "paragraph" | "split_row";
  page?: number;
  align?: ParagraphAlign;
  runs: Run[];
};

export type DividerBlock = {
  id: string;
  type: "divider";
  width_pt: number;
  color_hex: string;
};

export type Block = ParagraphBlock | DividerBlock;

export type Resume = {
  id: string;
  note?: string;
  updated_at?: string;
  document: {
    source_file: string;
    page_count: number;
    page_size_pt: { width: number; height: number };
    margins_pt?: { left: number; right: number; top: number; bottom: number };
  };
  blocks: Block[];
};

export type ChatMessage = {
  role: "user" | "assistant";
  content: string;
};

/** One suggestion from the assistant, aimed at a single block by id. */
export type ResumeEdit = {
  op: "replace" | "insert_after";
  block_id: string;
  text: string;
};

export type ChatReply = {
  reply: string;
  edits: ResumeEdit[];
};

export type ResumeSummary = {
  id: string;
  source_file: string;
  note: string;
  updated_at: string;
};
