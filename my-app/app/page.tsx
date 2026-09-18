import { Faq } from "@/components/marketing/faq";
import { Hero } from "@/components/marketing/hero";
import { HowItWorks } from "@/components/marketing/how-it-works";
import { JobRibbon } from "@/components/marketing/job-ribbon";
import { ProductSplit } from "@/components/marketing/product-split";
import { Reviews } from "@/components/marketing/reviews";
import { SiteFooter } from "@/components/marketing/site-footer";
import { SiteHeader } from "@/components/marketing/site-header";

export default function Home() {
  return (
    <div className="min-h-full bg-background text-foreground">
      <SiteHeader />
      <main>
        <Hero />
        <JobRibbon />
        <Reviews />
        <HowItWorks />
        <ProductSplit />
        <Faq />
      </main>
      <SiteFooter />
    </div>
  );
}
