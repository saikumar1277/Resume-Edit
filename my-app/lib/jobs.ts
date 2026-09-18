export type JobWorkplace = "remote" | "hybrid" | "onsite";
export type JobType = "full-time" | "part-time" | "contract" | "internship";
export type JobExperience = "intern" | "entry" | "mid" | "senior";
export type JobSort = "posted_desc" | "posted_asc" | "company" | "title";
export type JobPosted = "1d" | "7d" | "30d";

export type Job = {
  id: string;
  title: string;
  company: string;
  location: string;
  workplace: JobWorkplace;
  type: JobType;
  postedAt: string;
  description: string;
  tags: string[];
  url?: string;
  experience: JobExperience;
};

export type JobFilters = {
  title: string;
  location: string;
  company: string;
  workplaces: JobWorkplace[];
  types: JobType[];
  experience: JobExperience[];
  posted: JobPosted | "";
  exclude: string;
  sort: JobSort;
};

export const WORKPLACE_LABELS: Record<JobWorkplace, string> = {
  remote: "Remote",
  hybrid: "Hybrid",
  onsite: "On-site",
};

export const TYPE_LABELS: Record<JobType, string> = {
  "full-time": "Full-time",
  "part-time": "Part-time",
  contract: "Contract",
  internship: "Internship",
};

export const EXPERIENCE_LABELS: Record<JobExperience, string> = {
  intern: "Intern",
  entry: "Entry",
  mid: "Mid",
  senior: "Senior",
};

export const POSTED_LABELS: Record<JobPosted, string> = {
  "1d": "Past day",
  "7d": "Past week",
  "30d": "Past month",
};

export const SORT_LABELS: Record<JobSort, string> = {
  posted_desc: "Newest",
  posted_asc: "Oldest",
  company: "Company",
  title: "Title",
};

export const MOCK_JOBS: Job[] = [
  {
    id: "j1",
    title: "Senior Frontend Engineer",
    company: "Northstar Labs",
    location: "New York, NY",
    workplace: "hybrid",
    type: "full-time",
    postedAt: "2026-09-10",
    experience: "senior",
    description:
      "Build the editor canvas and document tools for a writing product. You will own TipTap integrations, layout performance, and the design system used across the web app.",
    tags: ["React", "TypeScript", "TipTap", "CSS"],
  },
  {
    id: "j2",
    title: "Backend Engineer",
    company: "Harbor Data",
    location: "Austin, TX",
    workplace: "onsite",
    type: "full-time",
    postedAt: "2026-09-08",
    experience: "mid",
    description:
      "Design FastAPI services that convert documents, store structured JSON, and stream PDF downloads. Comfort with Python, file processing, and clean HTTP APIs is required.",
    tags: ["Python", "FastAPI", "PostgreSQL", "PDF"],
  },
  {
    id: "j3",
    title: "Full-Stack Engineer",
    company: "Relay Health",
    location: "Remote, US",
    workplace: "remote",
    type: "full-time",
    postedAt: "2026-09-12",
    experience: "mid",
    description:
      "Ship patient-facing features from Next.js UI through Python APIs. You will work with clinicians to turn messy requirements into small, testable releases.",
    tags: ["Next.js", "Python", "TypeScript", "AWS"],
  },
  {
    id: "j4",
    title: "Machine Learning Engineer",
    company: "Cinder Analytics",
    location: "Seattle, WA",
    workplace: "hybrid",
    type: "contract",
    postedAt: "2026-09-05",
    experience: "mid",
    description:
      "Six-month contract to productionize ranking models for job matching. You will evaluate LLM rewrite quality, add evaluation harnesses, and keep latency under a second.",
    tags: ["Python", "LLMs", "Evaluation", "Ranking"],
  },
  {
    id: "j5",
    title: "Data Analyst",
    company: "Brightline Retail",
    location: "Chicago, IL",
    workplace: "hybrid",
    type: "part-time",
    postedAt: "2026-09-03",
    experience: "mid",
    description:
      "Part-time role analyzing conversion funnels and resume-upload drop-off. You will build dashboards and write short briefs for product and marketing.",
    tags: ["SQL", "Looker", "Excel", "Analytics"],
  },
  {
    id: "j6",
    title: "Software Engineering Intern",
    company: "Atlas Cloud",
    location: "San Francisco, CA",
    workplace: "onsite",
    type: "internship",
    postedAt: "2026-09-01",
    experience: "intern",
    description:
      "Summer internship on the developer platform team. You will add API examples, fix bugs in the upload pipeline, and pair with a mentor on a shippable project.",
    tags: ["JavaScript", "APIs", "Git", "Testing"],
  },
  {
    id: "j7",
    title: "DevOps Engineer",
    company: "Pinecone Systems",
    location: "Denver, CO",
    workplace: "remote",
    type: "contract",
    postedAt: "2026-08-28",
    experience: "mid",
    description:
      "Contract to stand up CI, preview environments, and PDF worker scaling. Experience with Docker, GitHub Actions, and simple observability is a plus.",
    tags: ["Docker", "CI", "AWS", "Observability"],
  },
  {
    id: "j8",
    title: "Product Designer",
    company: "Papertrail",
    location: "Boston, MA",
    workplace: "onsite",
    type: "part-time",
    postedAt: "2026-09-07",
    experience: "mid",
    description:
      "Part-time designer for a resume editor. You will refine the jobs list, toolbar density, and empty states, then hand off tight Figma specs to engineering.",
    tags: ["Figma", "UI", "Prototyping", "Research"],
  },
  {
    id: "j9",
    title: "iOS Engineer",
    company: "Lumen Mobile",
    location: "Toronto, ON",
    workplace: "hybrid",
    type: "internship",
    postedAt: "2026-08-30",
    experience: "intern",
    description:
      "Internship building SwiftUI screens that preview resumes on device. You will work with design on typography and implement offline document caching.",
    tags: ["Swift", "SwiftUI", "iOS", "Offline"],
  },
  {
    id: "j10",
    title: "Technical Writer",
    company: "Open Ledger",
    location: "London, UK",
    workplace: "remote",
    type: "part-time",
    postedAt: "2026-09-11",
    experience: "mid",
    description:
      "Document the conversion pipeline, block JSON, and editor shortcuts. You will interview engineers and publish a public guide for API consumers.",
    tags: ["Writing", "Docs", "APIs", "Markdown"],
  },
  {
    id: "j11",
    title: "Staff Platform Engineer",
    company: "Keel Freight",
    location: "Austin, TX",
    workplace: "onsite",
    type: "contract",
    postedAt: "2026-09-02",
    experience: "senior",
    description:
      "Lead a contract to replace ad-hoc JSON files with a durable store, without changing the editor API. Strong opinions on migrations and rollback are expected.",
    tags: ["Python", "Postgres", "Migrations", "Platform"],
  },
  {
    id: "j12",
    title: "AI Product Intern",
    company: "Northstar Labs",
    location: "Remote, US",
    workplace: "remote",
    type: "internship",
    postedAt: "2026-09-09",
    experience: "intern",
    description:
      "Internship helping prompt, evaluate, and ship resume rewrite suggestions. You will label model edits, write eval cases, and sit with users during tests.",
    tags: ["LLMs", "Product", "Evaluation", "Writing"],
  },
];

export const EMPTY_FILTERS: JobFilters = {
  title: "",
  location: "",
  company: "",
  workplaces: [],
  types: [],
  experience: [],
  posted: "",
  exclude: "",
  sort: "posted_desc",
};

export function isJobWorkplace(value: string): value is JobWorkplace {
  return value === "remote" || value === "hybrid" || value === "onsite";
}

export function isJobType(value: string): value is JobType {
  return (
    value === "full-time" ||
    value === "part-time" ||
    value === "contract" ||
    value === "internship"
  );
}

export function isJobExperience(value: string): value is JobExperience {
  return (
    value === "intern" ||
    value === "entry" ||
    value === "mid" ||
    value === "senior"
  );
}

export function isJobPosted(value: string): value is JobPosted {
  return value === "1d" || value === "7d" || value === "30d";
}

export function isJobSort(value: string): value is JobSort {
  return (
    value === "posted_desc" ||
    value === "posted_asc" ||
    value === "company" ||
    value === "title"
  );
}

export function filterJobs(jobs: Job[], filters: JobFilters): Job[] {
  const title = filters.title.trim().toLowerCase();
  const location = filters.location.trim().toLowerCase();
  const company = filters.company.trim().toLowerCase();
  const excluded = filters.exclude
    .toLowerCase()
    .split(/[\s,]+/)
    .filter(Boolean);
  const cutoff = postedCutoff(filters.posted);

  const matched = jobs.filter((job) => {
    if (title && !job.title.toLowerCase().includes(title)) return false;
    if (location && !job.location.toLowerCase().includes(location)) return false;
    if (company && !job.company.toLowerCase().includes(company)) return false;
    if (filters.workplaces.length && !filters.workplaces.includes(job.workplace)) {
      return false;
    }
    if (filters.types.length && !filters.types.includes(job.type)) return false;
    if (filters.experience.length && !filters.experience.includes(job.experience)) {
      return false;
    }
    if (cutoff && (!job.postedAt || job.postedAt < cutoff)) return false;
    const blob = `${job.title} ${job.company}`.toLowerCase();
    if (excluded.some((token) => blob.includes(token))) return false;
    return true;
  });

  const copy = [...matched];
  if (filters.sort === "company") {
    copy.sort((a, b) => a.company.localeCompare(b.company));
  } else if (filters.sort === "title") {
    copy.sort((a, b) => a.title.localeCompare(b.title));
  } else {
    const dir = filters.sort === "posted_asc" ? 1 : -1;
    copy.sort((a, b) => dir * a.postedAt.localeCompare(b.postedAt));
  }
  return copy;
}

function postedCutoff(posted: JobPosted | ""): string {
  if (!posted) return "";
  const days = posted === "1d" ? 1 : posted === "7d" ? 7 : 30;
  const date = new Date();
  date.setUTCDate(date.getUTCDate() - days);
  return date.toISOString().slice(0, 10);
}

export function formatPostedAt(isoDate: string): string {
  if (!isoDate) return "date unknown";
  const date = new Date(`${isoDate}T00:00:00`);
  if (Number.isNaN(date.getTime())) return isoDate;
  return date.toLocaleDateString("en-US", {
    month: "short",
    day: "numeric",
    year: "numeric",
  });
}
