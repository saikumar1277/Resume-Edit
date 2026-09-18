"use client";

import { type ReactNode, useEffect, useMemo, useState } from "react";
import { usePathname, useRouter, useSearchParams } from "next/navigation";
import {
  ChevronLeftIcon,
  ChevronRightIcon,
  ExternalLinkIcon,
  XIcon,
} from "lucide-react";
import { fetchJobs, type SweepStatus } from "../../lib/api";
import {
  EMPTY_FILTERS,
  EXPERIENCE_LABELS,
  MOCK_JOBS,
  POSTED_LABELS,
  SORT_LABELS,
  TYPE_LABELS,
  WORKPLACE_LABELS,
  filterJobs,
  formatPostedAt,
  isJobExperience,
  isJobPosted,
  isJobSort,
  isJobType,
  isJobWorkplace,
  type Job,
  type JobExperience,
  type JobFilters,
  type JobPosted,
  type JobSort,
  type JobType,
  type JobWorkplace,
} from "../../lib/jobs";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import {
  Collapsible,
  CollapsibleContent,
  CollapsibleTrigger,
} from "@/components/ui/collapsible";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Skeleton } from "@/components/ui/skeleton";
import { ToggleGroup, ToggleGroupItem } from "@/components/ui/toggle-group";
import { cn } from "@/lib/utils";

const PAGE_SIZE = 20;
const DEBOUNCE_MS = 300;

function csv<T extends string>(
  raw: string | null,
  check: (value: string) => value is T,
): T[] {
  if (!raw) return [];
  const out: T[] = [];
  for (const part of raw.split(",")) {
    const item = part.trim();
    if (check(item) && !out.includes(item)) out.push(item);
  }
  return out;
}

function filtersFromParams(params: URLSearchParams): JobFilters {
  const sort = params.get("sort") ?? "";
  const posted = params.get("posted") ?? "";
  return {
    title: params.get("title") || params.get("q") || "",
    location: params.get("location") ?? "",
    company: params.get("company") ?? "",
    workplaces: csv(params.get("workplace"), isJobWorkplace),
    types: csv(params.get("type"), isJobType),
    experience: csv(params.get("experience"), isJobExperience),
    posted: isJobPosted(posted) ? posted : "",
    exclude: params.get("exclude") ?? "",
    sort: isJobSort(sort) ? sort : "posted_desc",
  };
}

function paramsFromFilters(filters: JobFilters): string {
  const params = new URLSearchParams();
  if (filters.title.trim()) params.set("title", filters.title.trim());
  if (filters.location.trim()) params.set("location", filters.location.trim());
  if (filters.company.trim()) params.set("company", filters.company.trim());
  if (filters.workplaces.length) {
    params.set("workplace", filters.workplaces.join(","));
  }
  if (filters.types.length) {
    params.set("type", filters.types.join(","));
  }
  if (filters.experience.length) {
    params.set("experience", filters.experience.join(","));
  }
  if (filters.posted) params.set("posted", filters.posted);
  if (filters.exclude.trim()) params.set("exclude", filters.exclude.trim());
  if (filters.sort !== "posted_desc") params.set("sort", filters.sort);
  return params.toString();
}

function formatWhen(value: string | null | undefined): string {
  if (!value) return "";
  const then = Date.parse(value);
  if (Number.isNaN(then)) return "";
  const minutes = Math.round((Date.now() - then) / 60000);
  if (minutes < 1) return "just now";
  if (minutes < 60) return `${minutes}m ago`;
  const hours = Math.round(minutes / 60);
  if (hours < 48) return `${hours}h ago`;
  return `${Math.round(hours / 24)}d ago`;
}

export default function JobsBoard() {
  const router = useRouter();
  const pathname = usePathname();
  const searchParams = useSearchParams();
  const filters = useMemo(
    () => filtersFromParams(searchParams),
    [searchParams],
  );
  const [draftTitle, setDraftTitle] = useState(filters.title);
  const [draftLocation, setDraftLocation] = useState(filters.location);
  const [draftCompany, setDraftCompany] = useState(filters.company);
  const [draftExclude, setDraftExclude] = useState(filters.exclude);
  const [jobs, setJobs] = useState<Job[]>([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(0);
  const [usingMock, setUsingMock] = useState(false);
  const [loading, setLoading] = useState(true);
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [updatedAt, setUpdatedAt] = useState<string | null>(null);
  const [sweep, setSweep] = useState<SweepStatus | null>(null);
  const [moreOpen, setMoreOpen] = useState(
    Boolean(
      filters.company || filters.exclude || filters.sort !== "posted_desc",
    ),
  );

  useEffect(() => {
    setDraftTitle(filters.title);
    setDraftLocation(filters.location);
    setDraftCompany(filters.company);
    setDraftExclude(filters.exclude);
  }, [filters.title, filters.location, filters.company, filters.exclude]);

  useEffect(() => {
    const handle = window.setTimeout(() => {
      if (
        draftTitle === filters.title &&
        draftLocation === filters.location &&
        draftCompany === filters.company &&
        draftExclude === filters.exclude
      ) {
        return;
      }
      replaceFilters({
        ...filters,
        title: draftTitle,
        location: draftLocation,
        company: draftCompany,
        exclude: draftExclude,
      });
    }, DEBOUNCE_MS);
    return () => window.clearTimeout(handle);
  }, [draftTitle, draftLocation, draftCompany, draftExclude, filters]);

  const filterKey = paramsFromFilters(filters);
  const [prevFilterKey, setPrevFilterKey] = useState(filterKey);
  if (filterKey !== prevFilterKey) {
    setPrevFilterKey(filterKey);
    setPage(0);
  }

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    const offset = page * PAGE_SIZE;
    fetchJobs(filters, { limit: PAGE_SIZE, offset })
      .then((payload) => {
        if (cancelled) return;
        setSweep(payload.sweep);
        setUpdatedAt(payload.updated_at);
        if (payload.source === "snapshot" || payload.jobs.length > 0) {
          setJobs(payload.jobs);
          setTotal(payload.total);
          setUsingMock(false);
          return;
        }
        const sample = filterJobs(MOCK_JOBS, filters);
        setJobs(sample.slice(offset, offset + PAGE_SIZE));
        setTotal(sample.length);
        setUsingMock(true);
      })
      .catch(() => {
        if (cancelled) return;
        const sample = filterJobs(MOCK_JOBS, filters);
        setJobs(sample.slice(offset, offset + PAGE_SIZE));
        setTotal(sample.length);
        setUsingMock(true);
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [filterKey, page]);

  useEffect(() => {
    if (jobs.length === 0) {
      setSelectedId(null);
      return;
    }
    setSelectedId((current) =>
      current && jobs.some((job) => job.id === current) ? current : jobs[0].id,
    );
  }, [jobs]);

  const selected = jobs.find((job) => job.id === selectedId) ?? null;
  const hasPrev = page > 0;
  const hasNext = (page + 1) * PAGE_SIZE < total;
  const rangeStart = total === 0 ? 0 : page * PAGE_SIZE + 1;
  const rangeEnd = Math.min(total, (page + 1) * PAGE_SIZE);
  const pills = activePills(filters);
  const updated = formatWhen(updatedAt);

  function replaceFilters(next: JobFilters) {
    setPage(0);
    const query = paramsFromFilters(next);
    router.replace(query ? `${pathname}?${query}` : pathname, {
      scroll: false,
    });
  }

  return (
    <div className="mx-auto flex w-full max-w-6xl flex-col gap-4 p-5 pb-12">
      <div className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <p className="text-xs tracking-wide text-muted-foreground uppercase">
            Open roles
          </p>
          <h1 className="font-serif text-3xl tracking-tight">Jobs</h1>
          <p className="mt-1 text-sm text-muted-foreground">
            {sweep?.status === "running"
              ? "Refreshing listings in the background."
              : "Search open roles from the latest snapshot."}
          </p>
        </div>
        <Badge variant="secondary" className="h-7 px-3">
          {usingMock
            ? `${total.toLocaleString()} sample roles`
            : `${total.toLocaleString()} roles`}
          {updated && !usingMock ? ` · updated ${updated}` : ""}
        </Badge>
      </div>

      <div className="sticky top-0 z-10 flex flex-wrap items-end gap-3 bg-linear-to-b from-background from-80% to-transparent py-3">
        <div className="flex min-w-56 flex-2 flex-col gap-1.5">
          <Label htmlFor="job-title">Role</Label>
          <Input
            id="job-title"
            type="search"
            value={draftTitle}
            onChange={(event) => setDraftTitle(event.target.value)}
            placeholder="Role or title, e.g. software engineer"
            aria-label="Search job titles"
            className="h-9"
          />
        </div>
        <div className="flex min-w-40 flex-1 flex-col gap-1.5">
          <Label htmlFor="job-location">Location</Label>
          <Input
            id="job-location"
            type="search"
            value={draftLocation}
            onChange={(event) => setDraftLocation(event.target.value)}
            placeholder="City or region"
            aria-label="Filter by location"
            className="h-9"
          />
        </div>

        <FilterGroup label="Experience">
          <ToggleGroup
            multiple
            variant="outline"
            size="sm"
            className="flex-wrap"
            value={filters.experience}
            onValueChange={(value) =>
              replaceFilters({
                ...filters,
                experience: value.filter(isJobExperience),
              })
            }
          >
            {(Object.keys(EXPERIENCE_LABELS) as JobExperience[]).map(
              (value) => (
                <ToggleGroupItem
                  key={value}
                  value={value}
                  className="active:scale-95"
                >
                  {EXPERIENCE_LABELS[value]}
                </ToggleGroupItem>
              ),
            )}
          </ToggleGroup>
        </FilterGroup>
        <FilterGroup label="Workplace">
          <ToggleGroup
            multiple
            variant="outline"
            size="sm"
            className="flex-wrap"
            value={filters.workplaces}
            onValueChange={(value) =>
              replaceFilters({
                ...filters,
                workplaces: value.filter(isJobWorkplace),
              })
            }
          >
            {(Object.keys(WORKPLACE_LABELS) as JobWorkplace[]).map((value) => (
              <ToggleGroupItem
                key={value}
                value={value}
                className="active:scale-95"
              >
                {WORKPLACE_LABELS[value]}
              </ToggleGroupItem>
            ))}
          </ToggleGroup>
        </FilterGroup>
        <FilterGroup label="Type">
          <ToggleGroup
            multiple
            variant="outline"
            size="sm"
            className="flex-wrap"
            value={filters.types}
            onValueChange={(value) =>
              replaceFilters({
                ...filters,
                types: value.filter(isJobType),
              })
            }
          >
            {(Object.keys(TYPE_LABELS) as JobType[]).map((value) => (
              <ToggleGroupItem
                key={value}
                value={value}
                className="active:scale-95"
              >
                {TYPE_LABELS[value]}
              </ToggleGroupItem>
            ))}
          </ToggleGroup>
        </FilterGroup>
        <FilterGroup label="Posted">
          <ToggleGroup
            variant="outline"
            size="sm"
            className="flex-wrap"
            value={filters.posted ? [filters.posted] : []}
            onValueChange={(value) => {
              const next = value[0];
              replaceFilters({
                ...filters,
                posted: isJobPosted(next) ? next : "",
              });
            }}
          >
            {(Object.keys(POSTED_LABELS) as JobPosted[]).map((value) => (
              <ToggleGroupItem
                key={value}
                value={value}
                className="active:scale-95"
              >
                {POSTED_LABELS[value]}
              </ToggleGroupItem>
            ))}
          </ToggleGroup>
        </FilterGroup>

        <div className="flex w-full items-center gap-2">
          <Collapsible open={moreOpen} onOpenChange={setMoreOpen}>
            <CollapsibleTrigger
              render={
                <Button variant={moreOpen ? "default" : "outline"} size="sm" />
              }
            >
              More filters
            </CollapsibleTrigger>
          </Collapsible>
          <Button
            type="button"
            variant="outline"
            size="sm"
            disabled={pills.length === 0 && filters.sort === "posted_desc"}
            onClick={() => {
              setDraftTitle("");
              setDraftLocation("");
              setDraftCompany("");
              setDraftExclude("");
              replaceFilters(EMPTY_FILTERS);
            }}
          >
            Clear
          </Button>
        </div>
      </div>

      <Collapsible open={moreOpen} onOpenChange={setMoreOpen}>
        <CollapsibleContent className="overflow-hidden data-open:animate-in data-open:fade-in-0 data-open:slide-in-from-top-2">
          <div className="grid gap-3 rounded-xl bg-card p-3 ring-1 ring-border sm:grid-cols-3">
            <div className="flex flex-col gap-1.5">
              <Label htmlFor="job-company">Company</Label>
              <Input
                id="job-company"
                type="search"
                value={draftCompany}
                onChange={(event) => setDraftCompany(event.target.value)}
                placeholder="Company name"
                aria-label="Filter by company"
              />
            </div>
            <div className="flex flex-col gap-1.5">
              <Label htmlFor="job-exclude">Exclude</Label>
              <Input
                id="job-exclude"
                type="search"
                value={draftExclude}
                onChange={(event) => setDraftExclude(event.target.value)}
                placeholder="Words to hide"
                aria-label="Exclude keywords"
              />
            </div>
            <div className="flex flex-col gap-1.5">
              <Label htmlFor="job-sort">Sort</Label>
              <Select
                value={filters.sort}
                onValueChange={(value) => {
                  if (isJobSort(value ?? "")) {
                    replaceFilters({ ...filters, sort: value as JobSort });
                  }
                }}
              >
                <SelectTrigger id="job-sort" className="w-full">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  {(Object.keys(SORT_LABELS) as JobSort[]).map((value) => (
                    <SelectItem key={value} value={value}>
                      {SORT_LABELS[value]}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
          </div>
        </CollapsibleContent>
      </Collapsible>

      {pills.length > 0 ? (
        <ul className="flex flex-wrap gap-1.5" aria-label="Active filters">
          {pills.map((pill) => (
            <li key={pill.key}>
              <Badge
                variant="secondary"
                render={
                  <button
                    type="button"
                    onClick={() => replaceFilters(pill.clear(filters))}
                  />
                }
              >
                {pill.label}
                <XIcon />
              </Badge>
            </li>
          ))}
        </ul>
      ) : null}

      {loading && jobs.length === 0 ? (
        <div className="grid gap-4 lg:grid-cols-[minmax(0,1fr)_minmax(280px,0.9fr)]">
          <div className="flex flex-col gap-2">
            {Array.from({ length: 8 }, (_, index) => (
              <Skeleton key={index} className="h-24 w-full rounded-xl" />
            ))}
          </div>
        </div>
      ) : jobs.length === 0 ? (
        <p className="rounded-xl bg-card p-5 text-sm text-muted-foreground ring-1 ring-border">
          No roles match these filters. Clear them to see the full list.
        </p>
      ) : (
        <div className="grid items-start gap-4 lg:grid-cols-[minmax(0,1fr)_minmax(280px,0.9fr)]">
          <div className="flex min-w-0 flex-col gap-2.5">
            <ul className="flex flex-col gap-2" aria-label="Job listings">
              {jobs.map((job, index) => (
                <li
                  key={job.id}
                  className="animate-in fade-in slide-in-from-bottom-2 fill-mode-both"
                  style={{ animationDelay: `${Math.min(index, 12) * 28}ms` }}
                >
                  <JobCard
                    job={job}
                    selected={job.id === selected?.id}
                    onSelect={() => setSelectedId(job.id)}
                  />
                </li>
              ))}
            </ul>
            {total > PAGE_SIZE ? (
              <div className="flex flex-wrap items-center gap-2 pt-1">
                <Button
                  type="button"
                  variant="outline"
                  size="sm"
                  disabled={!hasPrev || loading}
                  onClick={() => setPage((current) => Math.max(0, current - 1))}
                >
                  <ChevronLeftIcon />
                  Previous
                </Button>
                <Button
                  type="button"
                  variant="outline"
                  size="sm"
                  disabled={!hasNext || loading}
                  onClick={() => setPage((current) => current + 1)}
                >
                  Next
                  <ChevronRightIcon />
                </Button>
                <span className="text-sm text-muted-foreground">
                  {rangeStart}–{rangeEnd} of {total.toLocaleString()}
                </span>
              </div>
            ) : null}
          </div>

          {selected ? (
            <Card
              key={selected.id}
              className="sticky top-4 animate-in fade-in zoom-in-95 duration-200"
              aria-live="polite"
            >
              <CardHeader>
                <CardDescription className="font-medium text-foreground">
                  {selected.company}
                </CardDescription>
                <CardTitle className="font-serif text-xl tracking-tight">
                  {selected.title}
                </CardTitle>
                <p className="text-sm text-muted-foreground">
                  {selected.location}
                  {" · "}
                  {WORKPLACE_LABELS[selected.workplace]}
                  {" · "}
                  {TYPE_LABELS[selected.type]}
                  {" · "}
                  {EXPERIENCE_LABELS[selected.experience]}
                  {selected.postedAt
                    ? ` · Posted ${formatPostedAt(selected.postedAt)}`
                    : ""}
                </p>
              </CardHeader>
              <CardContent className="flex flex-col gap-3 pb-4">
                {selected.tags.length > 0 ? (
                  <ul className="flex flex-wrap gap-1.5">
                    {selected.tags.map((tag) => (
                      <li key={tag}>
                        <Badge variant="secondary">{tag}</Badge>
                      </li>
                    ))}
                  </ul>
                ) : null}
                <p className="text-sm leading-relaxed">
                  {selected.description ||
                    "Open the posting for the full description."}
                </p>
                {selected.url ? (
                  <Button
                    size="sm"
                    className="self-start"
                    nativeButton={false}
                    render={
                      <a href={selected.url} target="_blank" rel="noreferrer" />
                    }
                  >
                    Open posting
                    <ExternalLinkIcon />
                  </Button>
                ) : null}
              </CardContent>
            </Card>
          ) : null}
        </div>
      )}
    </div>
  );
}

function FilterGroup({
  label,
  children,
}: {
  label: string;
  children: ReactNode;
}) {
  return (
    <div className="flex flex-col gap-1.5">
      <span className="text-sm font-medium">{label}</span>
      {children}
    </div>
  );
}

function JobCard({
  job,
  selected,
  onSelect,
}: {
  job: Job;
  selected: boolean;
  onSelect: () => void;
}) {
  return (
    <button
      type="button"
      className={cn(
        "w-full rounded-xl bg-card px-4 py-3 text-left text-sm ring-1 ring-border transition-all hover:-translate-y-px hover:shadow-sm active:scale-[0.99]",
        selected && "bg-accent ring-2 ring-foreground",
      )}
      onClick={onSelect}
      aria-pressed={selected}
    >
      <span className="block font-medium">{job.title}</span>
      <span className="mt-0.5 block">{job.company}</span>
      <span className="mt-0.5 block text-xs text-muted-foreground">
        {job.location}
        {" · "}
        {WORKPLACE_LABELS[job.workplace]}
        {" · "}
        {TYPE_LABELS[job.type]}
      </span>
      <span className="mt-2 flex items-center justify-between gap-2">
        <Badge variant="outline">{EXPERIENCE_LABELS[job.experience]}</Badge>
        <span className="text-xs text-muted-foreground">
          {job.postedAt
            ? `Posted ${formatPostedAt(job.postedAt)}`
            : "Date unknown"}
        </span>
      </span>
    </button>
  );
}

function activePills(filters: JobFilters): {
  key: string;
  label: string;
  clear: (current: JobFilters) => JobFilters;
}[] {
  const pills = [];
  if (filters.title.trim()) {
    pills.push({
      key: "title",
      label: `Title: ${filters.title.trim()}`,
      clear: (current: JobFilters) => ({ ...current, title: "" }),
    });
  }
  if (filters.location.trim()) {
    pills.push({
      key: "location",
      label: `Location: ${filters.location.trim()}`,
      clear: (current: JobFilters) => ({ ...current, location: "" }),
    });
  }
  if (filters.company.trim()) {
    pills.push({
      key: "company",
      label: `Company: ${filters.company.trim()}`,
      clear: (current: JobFilters) => ({ ...current, company: "" }),
    });
  }
  for (const value of filters.experience) {
    pills.push({
      key: `exp-${value}`,
      label: EXPERIENCE_LABELS[value],
      clear: (current: JobFilters) => ({
        ...current,
        experience: current.experience.filter((item) => item !== value),
      }),
    });
  }
  for (const value of filters.workplaces) {
    pills.push({
      key: `work-${value}`,
      label: WORKPLACE_LABELS[value],
      clear: (current: JobFilters) => ({
        ...current,
        workplaces: current.workplaces.filter((item) => item !== value),
      }),
    });
  }
  for (const value of filters.types) {
    pills.push({
      key: `type-${value}`,
      label: TYPE_LABELS[value],
      clear: (current: JobFilters) => ({
        ...current,
        types: current.types.filter((item) => item !== value),
      }),
    });
  }
  if (filters.posted) {
    pills.push({
      key: "posted",
      label: POSTED_LABELS[filters.posted],
      clear: (current: JobFilters) => ({ ...current, posted: "" as const }),
    });
  }
  if (filters.exclude.trim()) {
    pills.push({
      key: "exclude",
      label: `Exclude: ${filters.exclude.trim()}`,
      clear: (current: JobFilters) => ({ ...current, exclude: "" }),
    });
  }
  return pills;
}
