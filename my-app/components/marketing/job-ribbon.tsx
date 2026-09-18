const TITLES = [
  "Software engineer intern",
  "Senior backend",
  "Forward deployed engineer",
  "Product designer",
  "Data scientist",
  "IT support engineer",
  "Staff product marketing",
  "Full-stack developer",
  "Teaching assistant",
  "Network engineer",
];

export function JobRibbon() {
  const loop = [...TITLES, ...TITLES];

  return (
    <div className="border-y border-[#d9cfc0] bg-[#efe6d6]">
      <p className="sr-only">Sample titles from the jobs snapshot</p>
      <div className="overflow-hidden py-3">
        <div className="marketing-marquee-track flex w-max gap-8 px-6 text-sm tracking-wide text-[#57534e] uppercase">
          {loop.map((title, index) => (
            <span key={`${title}-${index}`} className="flex items-center gap-8">
              {title}
              <span aria-hidden className="text-[#c4b6a4]">
                /
              </span>
            </span>
          ))}
        </div>
      </div>
    </div>
  );
}
