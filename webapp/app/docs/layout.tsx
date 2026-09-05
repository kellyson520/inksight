import Link from "next/link";
import { BookOpen } from "lucide-react";
import { DocsMobileNav } from "./mobile-nav";
import { t, withLocalePath } from "@/lib/i18n";
import { localeForRequest } from "@/lib/locale-server";

const sidebarSections = [
  {
    titleKey: "docs.section.gettingStarted",
    items: [
      { labelKey: "docs.item.intro", href: "/docs" },
      { labelKey: "docs.item.architecture", href: "/docs/architecture" },
      { labelKey: "docs.item.hardware", href: "/docs/hardware" },
      { labelKey: "docs.item.bom", href: "/docs/bom" },
      { labelKey: "docs.item.assembly", href: "/docs/assembly" },
    ],
  },
      {
        titleKey: "docs.section.usage",
        items: [
          { labelKey: "docs.item.website", href: "/docs/website" },
          { labelKey: "docs.item.darkMode", href: "/docs/dark-mode" },
          { labelKey: "docs.item.mobileApp", href: "/docs/mobile-app" },
          { labelKey: "docs.item.flash", href: "/docs/flash" },
          { labelKey: "docs.item.buttonControls", href: "/docs/button-controls" },
          { labelKey: "docs.item.apiKey", href: "/docs/api-key" },
          { labelKey: "docs.item.config", href: "/docs/config" },
          { labelKey: "docs.item.voiceMode", href: "/docs/voice-mode" },
        ],
      },
  {
    titleKey: "docs.section.advanced",
    items: [
      { labelKey: "docs.item.deploy", href: "/docs/deploy" },
      { labelKey: "docs.item.branching", href: "/docs/branching" },
      { labelKey: "docs.item.changelog", href: "/docs/changelog" },
      { labelKey: "docs.item.pluginDev", href: "/docs/custom-mode-dev" },
      { labelKey: "docs.item.apiReference", href: "/docs/api-reference" },
      { labelKey: "docs.item.faq", href: "/docs/faq" },
    ],
  },
];

async function Sidebar() {
  const locale = await localeForRequest();
  return (
    <nav className="space-y-6">
      {sidebarSections.map((section) => (
        <div key={section.titleKey}>
          <h4 className="text-xs font-semibold text-ink-light dark:text-zinc-500 uppercase tracking-widest mb-2.5 px-3">
            {t(locale, section.titleKey)}
          </h4>
          <ul className="space-y-0.5">
            {section.items.map((item) => (
              <li key={item.href}>
                <Link
                  href={withLocalePath(locale, item.href)}
                  className="block px-3 py-1.5 text-sm text-ink-muted dark:text-zinc-400 rounded-sm hover:text-ink dark:hover:text-zinc-100 hover:bg-ink/[0.04] dark:hover:bg-zinc-800/60 transition-colors"
                >
                  {t(locale, item.labelKey)}
                </Link>
              </li>
            ))}
          </ul>
        </div>
      ))}
    </nav>
  );
}

export default async function DocsLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  const locale = await localeForRequest();
  return (
    <div className="mx-auto max-w-6xl px-6 py-10">
      {/* Mobile nav trigger */}
      <div className="lg:hidden mb-6">
        <DocsMobileNav />
      </div>

      <div className="flex gap-10">
        {/* Sidebar - desktop only */}
        <aside className="hidden lg:block w-[220px] flex-shrink-0">
          <div className="sticky top-24">
            <div className="flex items-center gap-2 mb-6 px-3">
              <BookOpen size={16} className="text-ink dark:text-zinc-200" />
              <span className="text-sm font-semibold text-ink dark:text-zinc-200">{t(locale, "docs.center")}</span>
            </div>
            <Sidebar />
          </div>
        </aside>

        {/* Content */}
        <div className="min-w-0 flex-1 max-w-3xl">{children}</div>
      </div>
    </div>
  );
}
